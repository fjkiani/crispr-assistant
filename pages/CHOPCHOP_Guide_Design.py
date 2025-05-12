import sys
import os
import streamlit as st
import json
import pandas as pd
import threading
import queue
import time
import tempfile
from pathlib import Path
import importlib.util
from tools.guide_interpreter import compare_guides, locate_guide_in_gene

# Import literature analyzer
from tools.literature_analyzer import get_literature_summary_for_therapeutic_context

# Add the parent directory to the path so we can import from streamlit_app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common functions from the main app
from streamlit_app import (
    ask_llm, 
    run_chopchop, 
    parse_chopchop_results, 
    update_chopchop_results,
    save_chopchop_config,
    stream_subprocess_output,
    get_llm_tooltip
)

# Import helper functions directly
def import_coordinate_handler():
    """Import the Coordinate Handler module from tools/coordinate_handler.py"""
    try:
        spec = importlib.util.spec_from_file_location("coordinate_handler", "tools/coordinate_handler.py")
        coord_handler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coord_handler)
        return coord_handler
    except Exception as e:
        st.warning(f"Coordinate handler not available: {str(e)}")
        return None

def import_educational_context():
    """Import the Educational Context module from tools/educational_context.py"""
    try:
        spec = importlib.util.spec_from_file_location("educational_context", "tools/educational_context.py")
        edu_context = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(edu_context)
        return edu_context
    except Exception as e:
        st.warning(f"Educational content not available: {str(e)}")
        return None

def import_guide_interpreter():
    """Import the Guide Interpreter module from tools/guide_interpreter.py"""
    try:
        spec = importlib.util.spec_from_file_location("guide_interpreter", "tools/guide_interpreter.py")
        guide_interpreter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guide_interpreter)
        return guide_interpreter
    except Exception as e:
        st.warning(f"Guide interpreter not available: {str(e)}")
        return None

# Import guide explanation functions
guide_interpreter = import_guide_interpreter()
explain_guide_score = guide_interpreter.explain_guide_score if guide_interpreter else None

def create_educational_sidebar():
    """
    Create an educational sidebar with CRISPR terminology and concepts
    
    Returns:
        query_text: Any search query entered by the user
    """
    # Import educational context
    edu_context = import_educational_context()
    if not edu_context:
        st.sidebar.warning("Educational content not available.")
        return None
    
    with st.sidebar:
        st.header("CRISPR Education Center")
        
        # Create tabs for different educational content
        ed_tabs = st.tabs(["Terminology", "Concepts", "Ask"])
        
        # Tab 1: Terminology
        with ed_tabs[0]:
            st.subheader("CRISPR Terminology")
            
            # Search box for terms
            term_query = st.text_input("Search for a term:", key="term_search")
            
            if term_query:
                # Get term definition
                term_info = edu_context.get_term_definition(term_query, detailed=True)
                
                if "definition" in term_info:
                    st.markdown(f"### {term_info.get('term', term_query)}")
                    if "full_name" in term_info:
                        st.markdown(f"*{term_info['full_name']}*")
                    
                    st.markdown(f"**Definition:** {term_info['definition']}")
                    
                    if "context" in term_info:
                        st.markdown(f"**Context:** {term_info['context']}")
                    
                    if "related_terms" in term_info:
                        st.markdown("**Related Terms:**")
                        for related in term_info["related_terms"]:
                            st.markdown(f"- {related}")
            else:
                # Show a few common terms
                common_terms = ["CRISPR", "Cas9", "gRNA", "PAM", "Indel"]
                for term in common_terms:
                    with st.expander(term):
                        term_info = edu_context.get_term_definition(term)
                        st.write(term_info["definition"])
        
        # Tab 2: Concepts
        with ed_tabs[1]:
            st.subheader("Advanced Concepts")
            
            # Dropdown for concepts
            concept_options = list(edu_context.ADVANCED_CONCEPTS.keys())
            selected_concept = st.selectbox("Select a concept:", concept_options)
            
            if selected_concept:
                concept_info = edu_context.get_advanced_concept(selected_concept)
                
                st.markdown(f"### {selected_concept}")
                st.markdown(f"**{concept_info['definition']}**")
                
                # Display concept details based on structure
                if "applications" in concept_info:
                    st.markdown("**Applications:**")
                    for app in concept_info["applications"]:
                        st.markdown(f"- {app}")
                
                if "types" in concept_info:
                    st.markdown("**Types:**")
                    for t in concept_info["types"]:
                        if isinstance(t, dict):
                            st.markdown(f"- **{t['name']}**: {t.get('approach', t.get('action', ''))}")
                        else:
                            st.markdown(f"- {t}")
                
                if "considerations" in concept_info:
                    st.markdown("**Considerations:**")
                    for c in concept_info["considerations"]:
                        st.markdown(f"- {c}")
        
        # Tab 3: Ask a question
        with ed_tabs[2]:
            st.subheader("Ask About CRISPR")
            
            query_text = st.text_input("Ask a question:", key="edu_question")
            
            if query_text and st.button("Get Answer", key="edu_answer_btn"):
                with st.spinner("Getting educational information..."):
                    answer = edu_context.get_educational_context(query_text)
                    st.markdown(answer)
                    
                    # Add references if available
                    references = edu_context.get_scientific_references(query_text)
                    if references and isinstance(references, list) and len(references) > 0 and isinstance(references[0], dict) and "title" in references[0]:
                        st.markdown("**References:**")
                        for ref in references[:2]:  # Limit to 2 references
                            st.markdown(f"- {ref['title']} ({ref['authors'].split(',')[0]} et al., {ref['year']})")
            
            return query_text
    
    return None

# Add after imports but before page configuration
def compare_guides(guides, gene_symbol=None):
    """
    Compare multiple guides and provide recommendations.
    
    Args:
        guides (list): List of guide dictionaries
        gene_symbol (str, optional): Target gene symbol for domain context
        
    Returns:
        dict: Comparison results and recommendations
    """
    # Basic comparison logic
    comparison = {
        "recommendations": []
    }
    
    # Sort guides by efficiency score
    sorted_guides = sorted(guides, key=lambda g: float(g.get('efficiency', 0)), reverse=True)
    
    # Check if we have a clear winner
    if len(sorted_guides) > 1:
        top_efficiency = float(sorted_guides[0].get('efficiency', 0))
        second_efficiency = float(sorted_guides[1].get('efficiency', 0))
        
        if top_efficiency > second_efficiency * 1.5:  # If top guide is 50% better
            comparison["recommendations"].append(
                f"Guide {sorted_guides[0].get('seq', '')} has significantly higher efficiency score ({top_efficiency})."
            )
    
    # Check location distribution
    exon_guides = [g for g in guides if g.get('location', '').lower() == 'exon']
    if exon_guides and gene_symbol:
        comparison["recommendations"].append(
            f"For gene knockout in {gene_symbol}, prioritize guides targeting exons."
        )
    
    # Add general recommendation based on guide count
    if len(guides) >= 3:
        comparison["recommendations"].append(
            "Consider testing multiple guides experimentally to find the most effective one."
        )
    
    return comparison

# Set page configuration
st.set_page_config(
    page_title="CHOPCHOP Guide Design - AI Research Assistant",
    page_icon="🧬", 
    layout="wide"
)

# Paths
CHOPCHOP_DIR = Path(__file__).parents[1] / "tools" / "chopchop"
CHOPCHOP_SCRIPT_PATH = CHOPCHOP_DIR / "chopchop.py" 
CONFIG_LOCAL_PATH = CHOPCHOP_DIR / "config_local.json"

# Initialize queues for subprocess output
stdout_queue = queue.Queue()
stderr_queue = queue.Queue()

# Add this function after the imports but before the page code
def handle_gene_table_error(error_text, target_gene):
    """Handle gene table errors by providing helpful feedback and alternatives"""
    if "gene_table" in error_text and "No such file or directory" in error_text:
        st.error(f"""
        **Gene Table Not Found Error**
        
        CHOPCHOP couldn't find the gene table needed to translate gene symbol '{target_gene}' to genomic coordinates.
        
        **Solutions:**
        1. Please switch to 'Sequence' input mode and provide the DNA sequence for your target
        2. Or create a gene table file in your genomeFiles directory (see documentation)
        """)
        
        # Fetch example DNA sequence for common genes
        common_genes = {
            "TP53": "ATGGAGGAGCCGCAGTCAGATCCTAGCGTCGAGCCCCCTCTGAGTCAGGAAACATTTTCAGACCTATGGAAACTACTTCCTGAAAACAACGTTCTGTCCCCCTTGCCGTCCCAAGCAATGGATGATTTGATGCTGTCCCCGGACGATATTGAACAATGGTTCACTGAAGACCCAGGTCCAGATGAAGCTCCCAGAATGCCAGAGGCTGCTCCCCCCGTGGCCCCTGCACCAGCAGCTCCTACACCGGCGGCCCCTGCACCAGCCCCCTCCTGGCCCCTGTCATCTTCT",
            "BRCA1": "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTTAGAGTGTCCCATCTGGTAAGTCAGCACAAGAGTGTATTAATTTGGGATTCCTATGATTATCTCCTATGCAAATGAACAGAATTGACCTTACATACTAGGGAAGAAAAGACATGTCTAGTAAGATTAGGCTATTGTAATTGCTGATTTAGTCCTGGTAGCTCCAACCAGTACATGTTCTTCAAGGTTAATTGCTGACACCTGTGTTCTTAATTGCTCTTTTGCTATTAGCTG",
            "CFTR": "ATGCAGAGGTCGCCTCTGGAAAAGGCCAGCGTTGTCTCCAAACTTTTTTTCAGCTGGACCAGACCAATTTTGAGGAAAGGATACAGACAGCGCCTGGAATTGTCAGACATATACCAAATCCCTTCTGTTGATTCTGCTGACAATCTATCTGAAAAATTGGAAAGAGAATGGGATAGAGAGCTGGCTTCAAAGAAAAATCCTAAACTCATTAATGCCCTTCGGCGATGTTTTTTCTGGAGATTTATGTTCTATGGAATCTTTTTATATTTAGGGGAAGTCACCAAAGCAGTACAG"
        }
        
        if target_gene.upper() in common_genes:
            sequence = common_genes[target_gene.upper()]
            st.info(f"""
            **Tip:** Here's a common DNA sequence for {target_gene} that you can use:
            
            ```
            {sequence}
            ```
            
            Copy this sequence and switch to 'Sequence' input mode.
            """)
        return True
    return False

# Add this function after handle_gene_table_error function around line 189
def interpret_guide_properties(guide_data, target_gene, enzyme, provide_therapeutic_context=False):
    """
    Uses LLM to generate an interpretation of the guide RNA properties and scores.
    
    Args:
        guide_data (dict): Data for the selected guide
        target_gene (str): Name of the target gene
        enzyme (str): Selected CRISPR enzyme
        provide_therapeutic_context (bool): Whether to include therapeutic context in the analysis.
        
    Returns:
        str: LLM-generated interpretation text
    """
    # Base prompt
    prompt = f"""As a CRISPR expert, analyze this guide RNA for {target_gene} with {enzyme}:

GUIDE SEQUENCE: {guide_data.get('seq', 'Unknown')}
POSITION: {guide_data.get('start', 'Unknown')}-{guide_data.get('end', 'Unknown')}
EFFICIENCY SCORE: {guide_data.get('efficiency', 'Unknown')} (higher is better)
SPECIFICITY SCORE: {guide_data.get('specificity', 'Unknown')} (higher is better)
SELF-COMPLEMENTARITY: {guide_data.get('self_comp', 'Unknown')} (lower is better)
LOCATION: {guide_data.get('location', 'Unknown')} (e.g., exon, intron)

Please provide:
1. A concise evaluation of this guide's quality, mentioning pros and cons for general research.
2. Explain what makes this a good or suboptimal guide for general genome editing.
3. Recommendations for experimental design with this guide for basic research.
4. Any precautions needed for off-target effects in a research context.
"""

    if provide_therapeutic_context:
        prompt += f"""

Additionally, as a CRISPR THERAPEUTIC DEVELOPMENT expert, provide specific insights for its potential use in a therapeutic application targeting {target_gene}:
A. Therapeutic Efficacy: How does this guide's efficiency score and targeting location (e.g., exon vs. intron, predicted functional impact) relate to achieving a therapeutically relevant level of gene modification for a knockout strategy? What is the importance of high on-target efficiency for cell product potency?
B. Off-Target Risks & Safety: Given the specificity score, what are the potential off-target risks? What level of specificity is generally desired for therapeutic candidates? Crucially, what off-target validation methods (e.g., GUIDE-seq, CIRCLE-seq, digenome-seq) are essential before clinical consideration? Would you recommend exploring high-fidelity Cas enzyme variants or chemically modified sgRNAs with this guide?
C. Durability of Effect: How might the predicted editing outcome (e.g., specific indels if this were a CRISPResso2 result, or the nature of the target site for CHOPCHOP) influence the potential for long-term functional knockout?
D. Delivery Considerations: Are there any aspects of this guide (e.g., length, potential for complex secondary structures if self-complementarity is high) that might influence choice or efficiency of delivery vectors (e.g., AAV, LNP) commonly used for therapeutic applications?
E. Overall Therapeutic Potential: Based on the above, provide a brief assessment of this guide's suitability for further pre-clinical development towards a therapeutic application, highlighting key next steps for de-risking.

Integrate these therapeutic considerations into your overall analysis. Keep your response clear, specific, and structured (e.g., use headings for general and therapeutic sections).
"""
    else:
        prompt += "\nKeep your response clear, specific and under 350 words."

    # Get interpretation from LLM
    try:
        interpretation = ask_llm(prompt)
        return interpretation
    except Exception as e:
        return f"Error generating interpretation: {str(e)}"

# Page header
st.markdown('<div class="main-header">CHOPCHOP Guide Design</div>', unsafe_allow_html=True)

# Create tabs for configuration and execution
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Configuration", 
    "Run CHOPCHOP", 
    "Basic Results", 
    "Enhanced Analysis",
    "Coordinate Utilities"
])

with tab1:
    st.markdown('<div class="subheader">CHOPCHOP Configuration</div>', unsafe_allow_html=True)
    st.info("Before running CHOPCHOP, you need to configure the local settings including genome files.")
    
    # Organism and assembly selection
    col1, col2 = st.columns(2)
    with col1:
        organism = st.text_input("Organism (e.g., 'Human', 'Mouse')", 
                                value=st.session_state.chopchop_config.get("organism", "Human"))
    with col2:
        assembly = st.text_input("Genome Assembly (e.g., 'hg38', 'mm10')", 
                                value=st.session_state.chopchop_config.get("assembly", "hg38"))
    
    # --- START: Auto-detect genome files ---
    genome_files_dir = Path("genomeFiles")
    default_two_bit = st.session_state.chopchop_config.get("two_bit_file", "")
    default_bowtie_index = st.session_state.chopchop_config.get("bowtie_index", "")
    default_gene_annotation = st.session_state.chopchop_config.get("gene_annotation", "")

    if genome_files_dir.is_dir():
        st.markdown(f"Detected `genomeFiles` directory. Attempting to auto-fill paths...")
        
        # Expected filenames/dirname (adjust if necessary)
        expected_two_bit_name = f"{assembly}.2bit" 
        expected_bowtie_dir_name = "GRCh38_noalt_as" 
        expected_gtf_name = "gencode.v44.annotation.gtf"

        potential_two_bit_path = genome_files_dir / expected_two_bit_name
        if potential_two_bit_path.is_file():
            default_two_bit = str(potential_two_bit_path.resolve())
            st.session_state.chopchop_config["two_bit_file"] = default_two_bit

        potential_bowtie_path = genome_files_dir / expected_bowtie_dir_name
        if potential_bowtie_path.is_dir():
            default_bowtie_index = str(potential_bowtie_path.resolve())
            st.session_state.chopchop_config["bowtie_index"] = default_bowtie_index
        
        potential_gtf_path = genome_files_dir / expected_gtf_name
        if potential_gtf_path.is_file():
            default_gene_annotation = str(potential_gtf_path.resolve())
            st.session_state.chopchop_config["gene_annotation"] = default_gene_annotation
    # --- END: Auto-detect genome files ---

    # File paths
    st.subheader("Genome File Paths")
    st.markdown("**Enter the full paths to your genome files:**")
    
    two_bit_file = st.text_input(".2bit Sequence File Path", 
                                value=default_two_bit,
                                help="Path to the .2bit file containing the genome sequence")
    
    bowtie_index = st.text_input("Bowtie Index Directory", 
                                value=default_bowtie_index,
                                help="Directory containing the Bowtie index files")
    
    gene_annotation = st.text_input("Gene Annotation File (GTF/GFF)", 
                                    value=default_gene_annotation,
                                    help="Path to the gene annotation file (GTF or GFF format)")
    
    # Save button
    if st.button("Save CHOPCHOP Configuration"):
        # Update session state
        st.session_state.chopchop_config = {
            "organism": organism,
            "assembly": assembly,
            "two_bit_file": two_bit_file,
            "bowtie_index": bowtie_index,
            "gene_annotation": gene_annotation
        }
        
        # Create the configuration object
        config_data = {
            "PATH": {
                "PRIMER3": "./primer3_core",
                "BOWTIE": "/Users/fkiani/Desktop/FJK/Developent/CRISPResso2-master/tools/chopchop/bowtie/bowtie",
                "TWOBITTOFA": "./twoBitToFa",
                "TWOBIT_INDEX_DIR": "/Users/fkiani/Desktop/FJK/Developent/CRISPResso2-master/genomeFiles",
                "BOWTIE_INDEX_DIR": "/Users/fkiani/Desktop/FJK/Developent/CRISPResso2-master/genomeFiles",
                "ISOFORMS_INDEX_DIR": "/Users/fkiani/Desktop/FJK/Developent/CRISPResso2-master/genomeFiles",
                "ISOFORMS_MT_DIR": "/Users/fkiani/Desktop/FJK/Developent/CRISPResso2-master/genomeFiles",
                "GENE_TABLE_INDEX_DIR": "/Users/fkiani/Desktop/FJK/Developent/CRISPResso2-master/genomeFiles"
            },
            "THREADS": 1,
            organism: {
                assembly: {
                    "twobitfile": two_bit_file,
                    "bowtie": bowtie_index,
                    "gff": gene_annotation
                }
            }
        }
        
        # Validate inputs
        if not organism or not assembly or not two_bit_file or not bowtie_index or not gene_annotation:
            st.error("Please fill in all the fields.")
        else:
            # Save the configuration
            success, message = save_chopchop_config(config_data)
            if success:
                st.success(message)
            else:
                st.error(message)

with tab2:
    st.subheader("Run CHOPCHOP")
    
    # Check if configuration exists
    if not CONFIG_LOCAL_PATH.exists():
        st.warning("Please configure CHOPCHOP first in the 'Configuration' tab.")
    else:
        # Load available assemblies from config_local.json
        try:
            with open(CONFIG_LOCAL_PATH, 'r') as f:
                config = json.load(f)
            
            # Get organism and assembly from the config
            organisms = [k for k in config.keys() if k not in ["PATH", "THREADS"]]
            if organisms:
                organism = organisms[0]
                assemblies = list(config[organism].keys())
                if assemblies:
                    default_assembly = assemblies[0]
                else:
                    default_assembly = ""
            else:
                st.warning("Invalid configuration. Please reconfigure CHOPCHOP.")
                default_assembly = ""
        except Exception as e:
            st.error(f"Error loading configuration: {str(e)}")
            default_assembly = ""
        
        # CHOPCHOP parameters
        st.markdown("**Target Information:**")
        target_type = st.radio("Target Type", ["Gene Symbol", "Sequence", "Coordinates"], 
                            horizontal=True, 
                            help=get_llm_tooltip("Target Type"))
        
        if target_type == "Gene Symbol":
            target = st.text_input("Gene Symbol", 
                                value=st.session_state.chopchop_run.get("target", ""),
                                help=get_llm_tooltip("Gene Symbol"))
        elif target_type == "Sequence":
            target = st.text_area("DNA Sequence", 
                                value=st.session_state.chopchop_run.get("target", ""),
                                help=get_llm_tooltip("DNA Sequence"))
        else:  # Coordinates
            target = st.text_input("Genomic Coordinates", 
                                value=st.session_state.chopchop_run.get("target", ""),
                                help=get_llm_tooltip("Genomic Coordinates"))
        
        st.markdown("**CRISPR Parameters:**")
        col1, col2 = st.columns(2)
        
        with col1:
            # Define enzyme options
            enzyme_options = ["Cas9", "Cpf1", "Cas13"]
            
            # Handle case-insensitive matching for enzyme selection
            stored_enzyme = st.session_state.chopchop_run.get("enzyme", "cas9").lower()
            enzyme_index = 0  # Default to Cas9
            
            # Find index based on case-insensitive comparison
            for i, option in enumerate(enzyme_options):
                if option.lower() == stored_enzyme:
                    enzyme_index = i
                    break
            
            enzyme = st.selectbox(
                "CRISPR Enzyme", 
                enzyme_options,
                index=enzyme_index,
                help=get_llm_tooltip("CRISPR Enzyme")
            )
            
            guide_length = st.number_input("Guide Length", 
                                        min_value=15, max_value=25, 
                                        value=int(st.session_state.chopchop_run.get("guide_length", 20)),
                                        help=get_llm_tooltip("Guide Length"))
        
        with col2:
            pam = st.text_input("PAM Sequence", 
                            value=st.session_state.chopchop_run.get("pam", "NGG"),
                            help=get_llm_tooltip("PAM Sequence"))
            
            genome_assembly = st.text_input("Genome Assembly", 
                                        value=default_assembly,
                                        help=get_llm_tooltip("Genome Assembly"))
        
        output_dir = st.text_input("Output Directory", 
                                value=st.session_state.chopchop_run.get("output_dir", ""),
                                help="Directory where CHOPCHOP results will be saved (leave empty for temporary directory)")
        
        # Advanced options
        with st.expander("Advanced Options"):
            additional_args = st.text_area("Additional Command-Line Arguments", 
                                        value=st.session_state.chopchop_run.get("additional_args", ""),
                                        help="Additional arguments to pass to the CHOPCHOP script")
        
        # Prepare temporary directory if needed
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix="chopchop_")
        
        # Run button
        if st.button("Run CHOPCHOP"):
            # Update session state
            st.session_state.chopchop_run = {
                "target": target,
                "enzyme": enzyme.lower(),  # Convert to lowercase for command
                "guide_length": guide_length,
                "pam": pam,
                "output_dir": output_dir,
                "additional_args": additional_args
            }
            
            # Create a progress placeholder
            progress_placeholder = st.empty()
            progress_placeholder.info("Starting CHOPCHOP...")
            
            # Create output containers
            stdout_container = st.empty()
            stderr_container = st.empty()
            
            # Run CHOPCHOP
            process = run_chopchop(
                target=target,
                enzyme=enzyme.lower(), # Convert to lowercase for command
                genome_assembly=genome_assembly.strip(), # Remove any extra spaces
                guide_length=guide_length,
                pam=pam,
                output_dir=output_dir,
                additional_args=additional_args
            )
            
            # Start output streaming threads
            t1 = threading.Thread(target=stream_subprocess_output, args=(process, stdout_queue, stderr_queue))
            t1.daemon = True
            t1.start()
            
            # Display output as it comes
            stdout_text = ""
            stderr_text = ""
            
            while True:
                # Check if process is still running
                if process.poll() is not None and stdout_queue.empty() and stderr_queue.empty():
                    break
                
                # Get stdout
                try:
                    while not stdout_queue.empty():
                        line = stdout_queue.get_nowait()
                        stdout_text += line
                        # Update the display
                        stdout_container.text_area("Standard Output", stdout_text, height=200)
                        
                        # Check for progress indicators
                        if "Processing" in line or "Searching" in line:
                            progress_placeholder.info(f"Running CHOPCHOP: {line.strip()}")
                except queue.Empty:
                    pass
                
                # Get stderr
                try:
                    while not stderr_queue.empty():
                        line = stderr_queue.get_nowait()
                        stderr_text += line
                        # Update the display
                        stderr_container.text_area("Error Output", stderr_text, height=100)
                except queue.Empty:
                    pass
                
                # Sleep briefly to avoid CPU hogging
                time.sleep(0.1)
            
            # Process completed
            return_code = process.returncode
            
            if return_code == 0:
                progress_placeholder.success("CHOPCHOP completed successfully!")
                
                # Parse results
                results = parse_chopchop_results(output_dir)
                
                # Update session state with results
                if results and 'guides' in results:
                    update_chopchop_results(output_dir, results['guides'])
                else:
                    update_chopchop_results(output_dir)
                
                # Show a message to switch to the Results tab
                st.success(f"CHOPCHOP run completed. Results saved to: {output_dir}")
                st.info("Switch to the 'Results' tab to view the guide recommendations.")
            else:
                progress_placeholder.error(f"CHOPCHOP failed with return code {return_code}")
                
                # Check for specific errors and provide helpful guidance
                if stderr_text:
                    if target_type == "Gene Symbol" and handle_gene_table_error(stderr_text, target):
                        st.error("Please try again using a DNA sequence instead of a gene symbol.")
                        
                        # Provide a section for entering a DNA sequence directly
                        st.markdown("### Enter DNA sequence directly:")
                        sequence_input = st.text_area(
                            "DNA Sequence for target gene",
                            help="Paste a DNA sequence (e.g., exon or coding sequence) for your target gene"
                        )
                        
                        if sequence_input and st.button("Try with this sequence"):
                            # Store in session state for next run
                            st.session_state.chopchop_run["target"] = sequence_input
                            # Set session state to rerun with the sequence input
                            st.session_state.chopchop_target_type = "Sequence"
                            st.rerun()  # Use st.rerun() which is the recommended replacement for experimental_rerun

with tab3:
    st.subheader("CHOPCHOP Results")
    
    # Check if we have results to display
    if "chopchop_results" in st.session_state and st.session_state.chopchop_results["guides"]:
        guides = st.session_state.chopchop_results["guides"]
        
        # Convert to DataFrame for display
        df = pd.DataFrame(guides)
        
        # Round numeric columns for better display
        numeric_cols = ['efficiency', 'specificity', 'self_comp']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')
                df[col] = df[col].round(2)
        
        # Add LLM-powered results summary
        with st.expander("📊 CHOPCHOP Results Analysis", expanded=True):
            st.markdown("### Guide RNA Analysis")
            
            # Get the target gene and enzyme from session state
            target_gene = st.session_state.chopchop_run.get("target", "Unknown")
            enzyme_used = st.session_state.chopchop_run.get("enzyme", "cas9")
            
            # Basic statistics about the results
            st.markdown(f"**Target:** {target_gene}")
            st.markdown(f"**Total guides found:** {len(guides)}")
            
            # Location statistics
            locations = {}
            for guide in guides:
                loc = guide.get("location", "Unknown")
                locations[loc] = locations.get(loc, 0) + 1
            
            st.markdown("**Guide locations:**")
            for loc, count in locations.items():
                st.markdown(f"- {loc}: {count} guides ({count/len(guides)*100:.1f}%)")
                
            # LLM-powered general advice
            st.markdown("### General Guide Selection Advice")
            advice_prompt = f"""As a CRISPR expert, provide concise advice on selecting guides for {target_gene} based on these statistics:
- Total guides found: {len(guides)}
- Location distribution: {locations}

Focus on explaining:
1. Which location is generally preferred for knockout experiments
2. The importance of efficiency and specificity scores
3. What makes a good guide RNA for {enzyme_used}
4. Tips for selecting the best guide for common experiment types

Keep your response concise and practical, under 250 words.
"""
            with st.spinner("Getting expert advice..."):
                general_advice = ask_llm(advice_prompt)
                st.markdown(general_advice)
        
        # Display the guides in a sortable table
        st.dataframe(df, use_container_width=True)
        
        # Guide selection for detailed analysis
        st.subheader("Select a Guide for Detailed Analysis")
        
        # Guide selector
        guide_options = [f"Guide {i+1}: {guide['seq']}" for i, guide in enumerate(guides)]
        selected_guide_idx = st.selectbox("Select a guide:", range(len(guide_options)), format_func=lambda i: guide_options[i])
        
        # Guide details section
        if selected_guide_idx is not None:
            selected_guide = guides[selected_guide_idx]
            
            # Columns for guide details and LLM analysis
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("### Guide Properties")
                for key, value in selected_guide.items():
                    if key != 'seq':  # Sequence is shown in the title
                        st.markdown(f"**{key}:** {value}")
            
            with col2:
                st.markdown("### Expert Analysis")
                with st.spinner("Analyzing guide properties with AI..."):
                    interpretation = interpret_guide_properties(
                        guide_data=selected_guide,
                        target_gene=target_gene,
                        enzyme=enzyme_used,
                        provide_therapeutic_context=st.session_state.get('show_therapeutic_context', False)
                    )
                    st.markdown(interpretation)
                
                # Literature Search Integration for Basic Results Tab
                if st.session_state.get('show_therapeutic_context', False):
                    st.subheader("Literature Context for Therapeutic Development")
                    # Let's provide context for a couple of key challenges
                    challenge_keywords = {
                        "Efficacy & Functional Impact": "efficacy functional impact",
                        "Off-Target Effects & Safety": "off-target safety validation",
                        "Delivery Methods": "delivery methods T-cell therapy" # Example, can be more dynamic
                    }
                    
                    for display_name, keywords in challenge_keywords.items():
                        button_key = f"lit_search_{selected_guide_idx}_{keywords.replace(' ', '_')}"
                        if st.button(f"Search Literature: {display_name}", key=button_key):
                            with st.spinner(f"Searching literature for {target_gene} - {display_name}..."):
                                research_area_context = "cancer immunotherapy gene editing" # Could be made more dynamic
                                summary = get_literature_summary_for_therapeutic_context(
                                    target_keyword=target_gene,
                                    challenge_keyword=keywords,
                                    research_area=research_area_context
                                )
                                st.session_state[f"lit_summary_{selected_guide_idx}_{keywords.replace(' ', '_')}"] = summary
                        
                        # Display stored summary if available
                        summary_key = f"lit_summary_{selected_guide_idx}_{keywords.replace(' ', '_')}"
                        if summary_key in st.session_state:
                            with st.expander(f"Literature Summary: {target_gene} - {display_name}", expanded=False):
                                st.markdown(st.session_state[summary_key])
            
            # Option to select this guide for experiment design
            if st.button("Use this Guide for Experiment Design"):
                if "selected_guides" not in st.session_state:
                    st.session_state.selected_guides = []
                
                # Add guide to selected guides if not already there
                if selected_guide not in st.session_state.selected_guides:
                    st.session_state.selected_guides.append(selected_guide)
                    st.success(f"Guide added for experiment design. You now have {len(st.session_state.selected_guides)} guide(s) selected.")
                else:
                    st.info("This guide is already selected for experiment design.")
                
                # Update workflow context for AI chat assistant
                if "chat_workflow_context" in st.session_state:
                    st.session_state.chat_workflow_context["selected_guides"] = st.session_state.selected_guides
                    st.session_state.chat_workflow_context["gene_of_interest"] = target_gene
            
            # Display currently selected guides
            if "selected_guides" in st.session_state and st.session_state.selected_guides:
                st.markdown("### Selected Guides for Experiment Design")
                for i, guide in enumerate(st.session_state.selected_guides):
                    st.markdown(f"**{i+1}. {guide['seq']}** (Score: {guide.get('efficiency', 'N/A')})")
                
                # Option to clear selection
                if st.button("Clear Guide Selection"):
                    st.session_state.selected_guides = []
                    if "chat_workflow_context" in st.session_state:
                        st.session_state.chat_workflow_context["selected_guides"] = []
                    st.success("Guide selection cleared.")
    else:
        st.info("No results available. Run CHOPCHOP from the 'Run' tab to generate guides.")

with tab4:
    st.subheader("Enhanced Guide Analysis")
    
    # Check if we have results to display
    if "chopchop_results" in st.session_state and st.session_state.chopchop_results["guides"]:
        guides = st.session_state.chopchop_results["guides"]
        
        # Input for gene symbol for context-aware analysis
        gene_symbol = st.text_input(
            "Gene Symbol (for contextual analysis)", 
            help="Enter the gene symbol (e.g., TP53) to see how guides relate to functional domains"
        )
        
        # Input for experiment type
        experiment_type = st.selectbox(
            "Experiment Type",
            ["knockout", "knockin", "base_editing"],
            help="Select your experiment type for tailored guide analysis"
        )
        
        # Create tabs for different analysis views
        analysis_tabs = st.tabs([
            "Individual Guide Analysis", 
            "Guide Comparison", 
            "Gene Context", 
            "Expert Summary"
        ])
        
        # Tab 1: Individual Guide Analysis
        with analysis_tabs[0]:
            st.subheader("Detailed Guide Properties")
            
            # Select a guide to analyze
            if guides:
                guide_options = [f"Guide {i+1}: {g.get('seq', '')} ({g.get('efficiency', 'N/A')})" 
                                for i, g in enumerate(guides)]
                
                selected_guide_idx = st.selectbox(
                    "Select a guide to analyze",
                    range(len(guide_options)),
                    format_func=lambda i: guide_options[i]
                )
                
                selected_guide = guides[selected_guide_idx]
                
                # Get detailed explanation
                guide_explanation = explain_guide_score(selected_guide)
                
                # Display the sequence with PAM
                seq = selected_guide.get('seq', '')
                pam = selected_guide.get('pam', '')
                
                st.markdown(f"### {seq}**{pam}**")
                
                # Display scores
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    efficiency = selected_guide.get('efficiency', 'N/A')
                    st.metric("Efficiency Score", efficiency)
                
                with col2:
                    specificity = selected_guide.get('specificity', 'N/A')
                    st.metric("Specificity Score", specificity)
                
                with col3:
                    # Calculate overall quality score (simple average)
                    try:
                        if isinstance(efficiency, str):
                            efficiency = float(efficiency)
                        if isinstance(specificity, str):
                            specificity = float(specificity)
                        overall = (efficiency + specificity) / 2
                        st.metric("Overall Quality", f"{overall:.2f}")
                    except:
                        st.metric("Overall Quality", "N/A")
                
                # Show properties with colored indicators
                st.subheader("Guide Properties")
                
                for prop_name, prop_data in guide_explanation["properties"].items():
                    # Create expandable sections for each property
                    with st.expander(f"{prop_name.replace('_', ' ').title()}: {prop_data['value']}"):
                        # Show optimal/suboptimal indicator
                        if prop_data["optimal"]:
                            st.success("✓ Optimal")
                        else:
                            st.warning("⚠ Suboptimal")
                        
                        # Show explanation
                        st.write(prop_data["explanation"])
                
                # Show potential issues and recommendations
                st.subheader("Recommendations")
                
                # Check for common issues
                issues = []
                
                if not guide_explanation["properties"]["gc_content"]["optimal"]:
                    gc = float(guide_explanation["properties"]["gc_content"]["value"].strip('%')) / 100
                    if gc < 0.4:
                        issues.append("Low GC content may reduce binding efficiency.")
                    else:
                        issues.append("High GC content may increase off-target effects.")
                
                if not guide_explanation["properties"]["poly_t"]["optimal"]:
                    issues.append("Contains poly-T stretch which may reduce guide expression.")
                
                if not guide_explanation["properties"]["terminal_g"]["optimal"]:
                    issues.append("Lacks G before PAM which may reduce efficiency.")
                
                if issues:
                    for issue in issues:
                        st.warning(issue)
                else:
                    st.success("No significant issues detected with this guide.")
        
        # Tab 2: Guide Comparison
        with analysis_tabs[1]:
            st.subheader("Guide Comparison")
            
            # Allow selection of multiple guides to compare
            if guides:
                guide_options = [f"Guide {i+1}: {g.get('seq', '')}" for i, g in enumerate(guides)]
                
                selected_guide_indices = st.multiselect(
                    "Select guides to compare",
                    range(len(guide_options)),
                    format_func=lambda i: guide_options[i],
                    default=[0, 1] if len(guides) > 1 else [0]
                )
                
                if selected_guide_indices:
                    selected_guides = [guides[i] for i in selected_guide_indices]
                    
                    # Get comparison data
                    comparison = compare_guides(selected_guides, gene_symbol if gene_symbol else None)
                    
                    # Create a comparison table
                    comparison_data = []
                    
                    for idx, guide in zip(selected_guide_indices, selected_guides):
                        guide_exp = explain_guide_score(guide)
                        
                        # Check if guide targets a domain (if gene symbol is provided)
                        domain_info = "N/A"
                        if gene_symbol and "location" in guide_exp and "nearby_domains" in guide_exp["location"]:
                            domains = guide_exp["location"]["nearby_domains"]
                            if domains:
                                domain_info = ", ".join([f"{d['name']} ({d['relation']})" for d in domains])
                        
                        # Create row
                        row = {
                            "Guide": f"Guide {idx+1}",
                            "Sequence": guide.get('seq', '') + guide.get('pam', ''),
                            "Efficiency": guide.get('efficiency', 'N/A'),
                            "Specificity": guide.get('specificity', 'N/A'),
                            "GC Content": guide_exp["properties"]["gc_content"]["value"],
                            "Poly-T": "Yes" if not guide_exp["properties"]["poly_t"]["optimal"] else "No",
                            "Terminal G": "Yes" if guide_exp["properties"]["terminal_g"]["optimal"] else "No",
                            "Domain Targeting": domain_info
                        }
                        comparison_data.append(row)
                    
                    # Display as a table
                    st.dataframe(pd.DataFrame(comparison_data))
                    
                    # Visual comparison chart
                    st.subheader("Visual Comparison")
                    
                    # Create a dict for plotting
                    chart_data = {
                        "Guide": [f"Guide {idx+1}" for idx in selected_guide_indices],
                        "Efficiency": [],
                        "Specificity": []
                    }
                    
                    for guide in selected_guides:
                        try:
                            eff = float(guide.get('efficiency', 0))
                        except:
                            eff = 0
                        try:
                            spec = float(guide.get('specificity', 0))
                        except:
                            spec = 0
                            
                        chart_data["Efficiency"].append(eff)
                        chart_data["Specificity"].append(spec)
                    
                    # Create and display chart
                    chart_df = pd.DataFrame(chart_data)
                    st.bar_chart(
                        chart_df.set_index("Guide")
                    )
                    
                    # Display recommendations section
                    if "recommendations" in comparison:
                        st.subheader("Recommendations")
                        for rec in comparison.get("recommendations", []):
                            st.info(rec)
                else:
                    st.warning("Please select at least one guide to analyze.")
        
        # Tab 3: Gene Context
        with analysis_tabs[2]:
            st.subheader("Gene Context Analysis")
            
            if not gene_symbol:
                st.warning("Please enter a gene symbol in the field above to enable gene context analysis.")
            else:
                # Check if we have information about this gene
                try:
                    from tools.guide_interpreter import GENE_DOMAINS
                    
                    if gene_symbol.upper() in GENE_DOMAINS:
                        st.success(f"Found information for {gene_symbol}.")
                        
                        # Display gene domain info
                        domains = GENE_DOMAINS[gene_symbol.upper()]
                        
                        # Create a simple visualization of the gene domains
                        st.subheader(f"{gene_symbol} Domain Structure")
                        
                        # Get gene length (use maximum domain end as approximation)
                        gene_length = max([d["end"] for d in domains])
                        
                        # Create domain visualization
                        domain_html = f"""
                        <style>
                        .gene-container {{
                            width: 100%;
                            height: 50px;
                            background-color: #f0f0f0;
                            position: relative;
                            margin-bottom: 20px;
                        }}
                        
                        .domain {{
                            position: absolute;
                            height: 100%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-weight: bold;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            white-space: nowrap;
                        }}
                        </style>
                        
                        <div class="gene-container">
                        """
                        
                        # Add domains with colors
                        colors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099"]
                        
                        for i, domain in enumerate(domains):
                            start_percent = (domain["start"] / gene_length) * 100
                            width_percent = ((domain["end"] - domain["start"]) / gene_length) * 100
                            color = colors[i % len(colors)]
                            
                            domain_html += f"""
                            <div class="domain" style="left: {start_percent}%; width: {width_percent}%; background-color: {color};" 
                                 title="{domain['name']} ({domain['start']}-{domain['end']}): {domain['function']}">
                                {domain['name']}
                            </div>
                            """
                        
                        domain_html += "</div>"
                        
                        # Add a legend
                        domain_html += "<div style='margin-bottom: 20px;'>"
                        for i, domain in enumerate(domains):
                            color = colors[i % len(colors)]
                            domain_html += f"""
                            <span style="display: inline-block; width: 12px; height: 12px; background-color: {color}; margin-right: 5px;"></span>
                            <span style="margin-right: 15px;">{domain['name']} ({domain['start']}-{domain['end']})</span>
                            """
                        domain_html += "</div>"
                        
                        # Display the visualization
                        st.markdown(domain_html, unsafe_allow_html=True)
                        
                        # For each guide, show where it targets in the gene
                        st.subheader("Guide Targeting Locations")
                        
                        # Get guide locations in gene
                        guide_locations = []
                        
                        if guides:
                            for i, guide in enumerate(guides):
                                seq = guide.get('seq', '')
                                if seq:
                                    location = locate_guide_in_gene(seq, gene_symbol)
                                    if location:
                                        guide_locations.append({
                                            "index": i,
                                            "sequence": seq,
                                            "location": location
                                        })
                        
                        if guide_locations:
                            # Display each guide location
                            for gl in guide_locations:
                                with st.expander(f"Guide {gl['index']+1}: {gl['sequence']}"):
                                    # Show amino acid position
                                    aa_pos = gl["location"]["amino_acid_position"]
                                    st.write(f"**Position:** Amino acid {aa_pos}")
                                    st.write(f"**Strand:** {gl['location']['strand']}")
                                    
                                    # Show nearby domains
                                    if gl["location"]["nearby_domains"]:
                                        st.write("**Nearby Domains:**")
                                        for domain in gl["location"]["nearby_domains"]:
                                            relation = "Overlaps with" if domain["relation"] == "overlaps" else f"{domain['distance']} amino acids away from"
                                            st.write(f"- {relation} {domain['name']}")
                                            st.write(f"  *Function:* {domain['function']}")
                                    else:
                                        st.write("*No functional domains nearby*")
                        else:
                            st.info(f"None of the guides could be precisely mapped to {gene_symbol}.")
                    else:
                        st.warning(f"No detailed information available for {gene_symbol}. Basic analysis still available.")
                except ImportError:
                    st.warning("Domain information module not available. Basic analysis still available.")
        
        # Tab 4: Expert Summary
        with analysis_tabs[3]:
            st.subheader("Expert Analysis")
            
            if st.button("Generate Expert Analysis"):
                with st.spinner("Generating comprehensive guide analysis..."):
                    try:
                        # Generate the expert explanation
                        explanation = generate_llm_explanation(
                            guides[:5],  # Limit to top 5 guides for performance
                            gene_symbol if gene_symbol else None,
                            experiment_type,
                            provide_therapeutic_context=st.session_state.get('show_therapeutic_context', False)
                        )
                        
                        # Store in session state
                        if "guide_analysis" not in st.session_state:
                            st.session_state.guide_analysis = {}
                        
                        key = f"{gene_symbol or 'unknown'}_{experiment_type}"
                        st.session_state.guide_analysis[key] = explanation
                    except Exception as e:
                        st.error(f"Error generating analysis: {str(e)}")
            
            # Display the expert analysis if available
            key = f"{gene_symbol or 'unknown'}_{experiment_type}"
            if "guide_analysis" in st.session_state and key in st.session_state.guide_analysis:
                st.markdown(st.session_state.guide_analysis[key])
            else:
                st.info("Click 'Generate Expert Analysis' to get a comprehensive evaluation of your guides.")
    else:
        st.info("No CHOPCHOP results available. Please run CHOPCHOP first.")

with tab5:
    st.markdown('<div class="subheader">Genomic Coordinate Tools</div>', unsafe_allow_html=True)
    
    # Import coordinate handler
    coord_handler = import_coordinate_handler()
    if not coord_handler:
        st.error("Coordinate handler not available. Please ensure coordinate_handler.py is in the tools directory.")
    else:
        # Add educational sidebar
        create_educational_sidebar()
        
        # Create two columns for different coordinate operations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Gene to Coordinates")
            
            gene_symbol = st.text_input("Gene Symbol", help="Enter a gene symbol (e.g., TP53, BRCA1)")
            assembly = st.selectbox(
                "Genome Assembly",
                ["hg38", "hg19", "mm10", "mm9"],
                index=0,
                help="Select the genome assembly to use"
            )
            
            if gene_symbol and st.button("Find Coordinates", key="find_coords_btn"):
                with st.spinner(f"Looking up coordinates for {gene_symbol}..."):
                    # Create a converter instance
                    converter = coord_handler.GeneCoordinateConverter(assembly=assembly)
                    
                    # Get the region for this gene
                    region = converter.gene_to_region(gene_symbol)
                    
                    if region:
                        st.success(f"Found coordinates for {gene_symbol}")
                        
                        # Display the coordinates
                        st.markdown(f"**Location:** {region.to_ucsc_format()}")
                        st.markdown(f"**Assembly:** {region.assembly}")
                        st.markdown(f"**Strand:** {region.strand}")
                        
                        # Generate browser link
                        browser_url = region.get_ucsc_browser_url()
                        st.markdown(f"**UCSC Browser:** [View in Genome Browser]({browser_url})")
                        
                        # Add to session state for use in CHOPCHOP
                        if "coordinate_context" not in st.session_state:
                            st.session_state.coordinate_context = {}
                        
                        st.session_state.coordinate_context["gene"] = gene_symbol
                        st.session_state.coordinate_context["region"] = {
                            "chromosome": region.chromosome,
                            "start": region.start,
                            "end": region.end,
                            "strand": region.strand,
                            "assembly": region.assembly
                        }
                        
                        # Add button to use these coordinates in CHOPCHOP
                        if st.button("Use These Coordinates in CHOPCHOP"):
                            # Prepare the coordinate string in CHOPCHOP format
                            coord_str = f"{region.chromosome}:{region.start}-{region.end}"
                            # Set in session state
                            st.session_state.chopchop_run["target"] = coord_str
                            st.session_state.chopchop_target_type = "Coordinates"
                            # Redirect to the Run CHOPCHOP tab
                            st.switch_page("pages/CHOPCHOP_Guide_Design.py")
                    else:
                        st.error(f"Could not find coordinates for {gene_symbol}. Try a different gene symbol or assembly.")
        
        with col2:
            st.subheader("Coordinates to Genes")
            
            col2a, col2b, col2c = st.columns([2, 1, 1])
            
            with col2a:
                chromosome = st.text_input("Chromosome", value="chr", help="Chromosome (e.g., chr1, chrX)")
            
            with col2b:
                position = st.number_input("Position", min_value=1, value=1000000, help="1-based position")
            
            with col2c:
                distance = st.number_input("Search Distance", min_value=1000, value=10000, help="Distance in bp")
            
            coord_assembly = st.selectbox(
                "Genome Assembly",
                ["hg38", "hg19", "mm10", "mm9"],
                index=0,
                key="coord_assembly",
                help="Select the genome assembly to use"
            )
            
            if chromosome and position and st.button("Find Genes", key="find_genes_btn"):
                with st.spinner(f"Finding genes near {chromosome}:{position}..."):
                    # Create a genomic coordinate
                    coordinate = coord_handler.GenomicCoordinate(
                        chromosome=chromosome,
                        position=position,
                        assembly=coord_assembly
                    )
                    
                    # Find genes near this coordinate
                    genes = coord_handler.coordinate_to_gene(
                        coordinate=coordinate,
                        distance_threshold=distance
                    )
                    
                    if genes:
                        st.success(f"Found {len(genes)} genes within {distance}bp of {coordinate.to_ucsc_format()}")
                        
                        # Create a table of genes
                        gene_data = []
                        for gene in genes:
                            gene_data.append({
                                "Gene": gene["gene_symbol"],
                                "Distance (bp)": gene["distance"],
                                "Position Type": gene["position_type"].capitalize(),
                                "Strand": gene["region"]["strand"]
                            })
                        
                        # Display as a dataframe
                        st.dataframe(pd.DataFrame(gene_data))
                        
                        # Generate browser link
                        region = coord_handler.GenomicRegion(
                            chromosome=chromosome,
                            start=max(1, position - 5000),
                            end=position + 5000,
                            assembly=coord_assembly
                        )
                        browser_url = region.get_ucsc_browser_url()
                        st.markdown(f"**UCSC Browser:** [View in Genome Browser]({browser_url})")
                        
                        # Add button to use a selected gene in CHOPCHOP
                        if len(gene_data) > 0:
                            gene_options = [g["Gene"] for g in gene_data]
                            selected_gene = st.selectbox("Select a gene to use in CHOPCHOP", gene_options)
                            
                            if st.button("Use Selected Gene in CHOPCHOP"):
                                # Set in session state
                                st.session_state.chopchop_run["target"] = selected_gene
                                st.session_state.chopchop_target_type = "Gene Symbol"
                                # Redirect to the Run CHOPCHOP tab
                                st.switch_page("pages/CHOPCHOP_Guide_Design.py")
                    else:
                        st.info(f"No genes found within {distance}bp of {coordinate.to_ucsc_format()}")
        
        # Sequence context retrieval (below the two columns)
        st.subheader("Sequence Context Retrieval")
        
        seq_col1, seq_col2, seq_col3, seq_col4 = st.columns([2, 1, 1, 1])
        
        with seq_col1:
            seq_chrom = st.text_input("Chromosome", value="chr", key="seq_chrom", help="Chromosome (e.g., chr1, chrX)")
        
        with seq_col2:
            seq_start = st.number_input("Start", min_value=1, value=1000000, key="seq_start", help="Start position")
        
        with seq_col3:
            seq_end = st.number_input("End", min_value=1, value=1000100, key="seq_end", help="End position")
        
        with seq_col4:
            seq_assembly = st.selectbox(
                "Assembly",
                ["hg38", "hg19", "mm10", "mm9"],
                index=0,
                key="seq_assembly",
                help="Genome assembly"
            )
        
        if seq_chrom and seq_start and seq_end and st.button("Get Sequence", key="get_sequence_btn"):
            with st.spinner(f"Retrieving sequence for {seq_chrom}:{seq_start}-{seq_end}..."):
                # Create a genomic region
                region = coord_handler.GenomicRegion(
                    chromosome=seq_chrom,
                    start=seq_start,
                    end=seq_end,
                    assembly=seq_assembly
                )
                
                # Try to get the sequence
                sequence = coord_handler.get_sequence_context(region, use_web_api=True)
                
                if sequence:
                    st.success(f"Retrieved {len(sequence)}bp sequence")
                    
                    # Display the sequence in a text area
                    st.text_area("Sequence", sequence, height=150)
                    
                    # Add option to use this sequence in CHOPCHOP
                    if st.button("Use This Sequence in CHOPCHOP"):
                        # Set in session state
                        st.session_state.chopchop_run["target"] = sequence
                        st.session_state.chopchop_target_type = "Sequence"
                        # Redirect to the Run CHOPCHOP tab
                        st.switch_page("pages/CHOPCHOP_Guide_Design.py")
                else:
                    st.error("Could not retrieve sequence. The region might be too large or not available.")

# Function to locate a guide within a gene context
def locate_guide_in_gene(guide_seq, gene_symbol):
    """
    Locate where a guide targets within a gene and its functional domains.
    
    Args:
        guide_seq (str): Guide RNA sequence
        gene_symbol (str): Gene symbol
        
    Returns:
        dict: Location information including nearby domains
    """
    # This is a simplified implementation
    # In a production system, this would query a database or genomic coordinates
    
    # Mock result for demonstration
    location = {
        "amino_acid_position": 150,  # Example position
        "strand": "forward",
        "nearby_domains": []
    }
    
    # Check if we have domain information for this gene
    try:
        from tools.guide_interpreter import GENE_DOMAINS
        
        if gene_symbol.upper() in GENE_DOMAINS:
            domains = GENE_DOMAINS[gene_symbol.upper()]
            
            # Check which domains are near this position
            for domain in domains:
                if location["amino_acid_position"] >= domain["start"] and location["amino_acid_position"] <= domain["end"]:
                    location["nearby_domains"].append({
                        "name": domain["name"],
                        "relation": "overlaps",
                        "function": domain["function"]
                    })
                elif abs(location["amino_acid_position"] - domain["start"]) <= 20 or abs(location["amino_acid_position"] - domain["end"]) <= 20:
                    location["nearby_domains"].append({
                        "name": domain["name"],
                        "relation": "nearby",
                        "distance": min(abs(location["amino_acid_position"] - domain["start"]), abs(location["amino_acid_position"] - domain["end"])),
                        "function": domain["function"]
                    })
    except (ImportError, KeyError):
        pass  # Domain information not available
    
    return location

# Function to get LLM explanation
def generate_llm_explanation(guides, gene_symbol, experiment_type, provide_therapeutic_context=False):
    """
    Generate a comprehensive LLM explanation for guides.
    
    Args:
        guides (list): List of guide dictionaries
        gene_symbol (str): Target gene
        experiment_type (str): Type of experiment (knockout, knockin, base_editing)
        provide_therapeutic_context (bool): Whether to include therapeutic context in the analysis.
        
    Returns:
        str: LLM-generated explanation
    """
    # Base prompt for general research advice
    prompt = f"""As a CRISPR expert, provide a comprehensive analysis of these top guides for {gene_symbol if gene_symbol else 'the specified target'} for a {experiment_type} experiment from a general research perspective:

GUIDES OVERVIEW:
"""
    
    for i, guide in enumerate(guides):
        prompt += f"""
GUIDE {i+1}:
- Sequence: {guide.get('seq', 'Unknown')} (PAM: {guide.get('pam', 'Unknown')})
- Efficiency Score: {guide.get('efficiency', 'N/A')}
- Specificity Score: {guide.get('specificity', 'N/A')}
- Location: {guide.get('location', 'N/A')}
"""
    
    prompt += "\n### General Research Analysis:\n"
    if experiment_type == "knockout":
        prompt += """
For this KNOCKOUT experiment (general research focus):
1. Based on the provided scores (efficiency, specificity, location), which of these guides would you recommend and why? 
2. How should target location (e.g., exon vs. intron) generally influence guide choice for achieving a functional knockout in a research setting?
3. What typical on-target efficiency might one aim for in standard mammalian cell line experiments for research purposes?
4. What are crucial control experiments to include for validating a knockout in a research context?
"""
    elif experiment_type == "knockin":
        prompt += """
For this KNOCK-IN experiment (general research focus):
1. Which guide appears most suitable for precise integration, considering its scores and location? What are the key trade-offs?
2. For research purposes, what factors influence homology arm design (length, symmetry)?
3. What are common challenges and considerations for HDR-mediated knock-in experiments in cell lines?
4. General advice on donor template design for research applications.
"""
    else:  # base_editing
        prompt += """
For this BASE EDITING experiment (general research focus):
1. Which guide best positions the target nucleotide within a typical editing window? What are the implications of its scores?
2. What general factors guide the selection of a base editor (e.g., ABE, CBE) for a research target?
3. What on-target editing efficiency is typically considered good for base editing in research settings?
4. How can off-target base editing be assessed or minimized in a research context?
"""

    if provide_therapeutic_context:
        prompt += f"""

### Therapeutic Development Contextual Analysis:
Now, adopting the role of a CRISPR THERAPEUTIC DEVELOPMENT expert, please provide additional specific insights for the potential therapeutic application of these guides for {gene_symbol if gene_symbol else 'the specified target'}, focusing on a {experiment_type} strategy:

A. Comparative Therapeutic Efficacy: 
   - Considering these top guides, which one(s) show the most promise for therapeutic efficacy and why? Discuss the balance between on-target efficiency and predicted functional impact (e.g., exon targeting for knockout).
   - How critical is maximizing on-target editing for producing a potent and effective cell-based therapy (e.g., for CAR-T, HSC editing)?

B. Off-Target Risks & Safety Strategy for Therapeutics:
   - Evaluate the specificity scores of these guides in the context of therapeutic safety. Which guides pose higher/lower off-target risks?
   - What is the acceptable threshold for specificity when developing a CRISPR-based therapeutic? 
   - Outline a strategy for comprehensive off-target analysis (e.g., mentioning in silico prediction, cell-based unbiased methods like GUIDE-seq/CIRCLE-seq/digenome-seq, and the importance of testing in relevant primary cells).
   - When would you strongly recommend considering high-fidelity Cas enzymes or chemically modified sgRNAs for these guides if they were therapeutic candidates?

C. Durability and Long-Term Functional Impact:
   - For a {experiment_type} approach targeting {gene_symbol if gene_symbol else 'this target'}, how might the choice among these guides influence the likelihood of achieving a durable, long-term therapeutic effect? (e.g., cleaner edits, avoidance of hypomorphic alleles).

D. Delivery & Manufacturability Considerations:
   - Are there any properties of these guides (e.g., sequence complexity, self-complementarity if data were available) that might impact their suitability for common therapeutic delivery vectors (AAV, LNP) or large-scale sgRNA synthesis for clinical use?

E. Overall Therapeutic Recommendation & De-risking:
   - Provide an overall assessment: which guide(s), if any, would you prioritize for further pre-clinical therapeutic development and why?
   - What are the key 2-3 de-risking experiments or validation steps you would recommend next for the most promising candidate(s) before advancing towards clinical trials?
"""

    prompt += "\nProvide your analysis in a clear, structured format with distinct sections (General Research Analysis, Therapeutic Development Contextual Analysis) and use markdown headings and bullet points for readability.\n"
    
    # Get explanation from LLM
    try:
        explanation = ask_llm(prompt)
        return explanation
    except Exception as e:
        return f"Error generating explanation: {str(e)}" 