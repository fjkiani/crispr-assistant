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

# Add the parent directory to the path so we can import from streamlit_app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common functions from the main app
from streamlit_app import (
    ask_llm, 
    build_crispresso_command,
    verify_crispresso_installation,
    explain_results_with_llm,
    stream_subprocess_output,
    get_llm_tooltip,
    extract_output_dir
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

# Import the Enhanced Result Interpreter
try:
    from tools.result_interpreter import EnhancedResultParser
except ImportError:
    st.error("Failed to import Enhanced Result Interpreter. Make sure result_interpreter.py is in the tools directory.")

# Import the Next Steps module
try:
    from tools.next_steps import (
        suggest_troubleshooting,
        recommend_next_experiment,
        analyze_results_decision_support,
        get_next_steps_recommendation,
        generate_validation_protocol
    )
except ImportError:
    st.error("Failed to import Next Steps module. Make sure next_steps.py is in the tools directory.")

# Set page configuration
st.set_page_config(
    page_title="CRISPResso2 Analysis - AI Research Assistant",
    page_icon="🧬", 
    layout="wide"
)

# Initialize queues for subprocess output
stdout_queue = queue.Queue()
stderr_queue = queue.Queue()

# Page header
st.markdown('<div class="main-header">CRISPResso2 Analysis</div>', unsafe_allow_html=True)

# Create tabs for input, execution, and results
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Input Data", "Run CRISPResso2", "Basic Results", "Advanced Analysis", "Next Steps"])

with tab1:
    st.markdown('<div class="subheader">CRISPResso2 Input Data</div>', unsafe_allow_html=True)
    st.info("Upload your FASTQ files and provide sequences for CRISPResso2 analysis.")
    
    # FASTQ file uploaders
    st.markdown("**FASTQ Files:**")
    
    # We need to handle file upload in Streamlit differently
    # Since we can't use the file uploader directly to get a path
    # Instead, we'll provide an option to either upload or specify a path
    
    fastq_input_method = st.radio(
        "Select FASTQ input method:",
        ["Upload Files", "Specify File Paths"],
        help="Choose whether to upload FASTQ files or specify paths to existing files."
    )
    
    if fastq_input_method == "Upload Files":
        # File uploads
        col1, col2 = st.columns(2)
        with col1:
            fastq_r1_file = st.file_uploader(
                "FASTQ R1 File (Read 1)", 
                type=["fastq", "fq", "gz"],
                help="Upload your Read 1 FASTQ file (required)"
            )
        with col2:
            fastq_r2_file = st.file_uploader(
                "FASTQ R2 File (Read 2)", 
                type=["fastq", "fq", "gz"],
                help="Upload your Read 2 FASTQ file (optional, for paired-end data)"
            )
        
        # Save uploaded files to temp location if they exist
        if fastq_r1_file:
            # Create temp dir if needed
            upload_dir = Path(tempfile.mkdtemp(prefix="crispresso_uploads_"))
            
            # Save R1
            r1_path = upload_dir / fastq_r1_file.name
            with open(r1_path, "wb") as f:
                f.write(fastq_r1_file.getbuffer())
            st.session_state.crispresso["fastq_r1"] = str(r1_path)
            
            # Save R2 if provided
            if fastq_r2_file:
                r2_path = upload_dir / fastq_r2_file.name
                with open(r2_path, "wb") as f:
                    f.write(fastq_r2_file.getbuffer())
                st.session_state.crispresso["fastq_r2"] = str(r2_path)
            else:
                st.session_state.crispresso["fastq_r2"] = ""
    else:
        # File paths
        col1, col2 = st.columns(2)
        with col1:
            fastq_r1_path = st.text_input(
                "FASTQ R1 File Path (Read 1)",
                value=st.session_state.crispresso.get("fastq_r1", ""),
                help="Full path to your Read 1 FASTQ file (required)"
            )
            st.session_state.crispresso["fastq_r1"] = fastq_r1_path
        
        with col2:
            fastq_r2_path = st.text_input(
                "FASTQ R2 File Path (Read 2)",
                value=st.session_state.crispresso.get("fastq_r2", ""),
                help="Full path to your Read 2 FASTQ file (optional, for paired-end data)"
            )
            st.session_state.crispresso["fastq_r2"] = fastq_r2_path
    
    # Sequence inputs
    st.markdown("**Sequence Information:**")
    
    # Check if we have a guide sequence from CHOPCHOP
    if ("chopchop_results" in st.session_state and 
        st.session_state.chopchop_results["guides"] and 
        len(st.session_state.chopchop_results["guides"]) > 0):
        
        st.info("Guide sequences from CHOPCHOP are available. You can select one below.")
        
        # Create a dropdown to select from available guides
        guides = st.session_state.chopchop_results["guides"]
        guide_options = []
        
        for i, guide in enumerate(guides):
            seq = guide.get('seq', '')
            pam = guide.get('pam', '')
            guide_options.append(f"Guide {i+1}: {seq}{pam}")
        
        selected_guide_idx = st.selectbox(
            "Select a guide from CHOPCHOP results:",
            range(len(guide_options)),
            format_func=lambda i: guide_options[i]
        )
        
        # Extract the selected guide sequence
        selected_guide = guides[selected_guide_idx]
        guide_seq = selected_guide.get('seq', '') + selected_guide.get('pam', '')
        
        # Pre-fill the guide sequence field
        st.session_state.crispresso["guide_seq"] = guide_seq
    
    col1, col2 = st.columns(2)
    
    with col1:
        amplicon_seq = st.text_area(
            "Amplicon Sequence", 
            value=st.session_state.crispresso.get("amplicon_seq", ""),
            help="The full amplicon sequence, including the target site."
        )
        st.session_state.crispresso["amplicon_seq"] = amplicon_seq
    
    with col2:
        guide_seq = st.text_input(
            "Guide RNA Sequence (with PAM)", 
            value=st.session_state.crispresso.get("guide_seq", ""),
            help="The guide RNA sequence including the PAM (e.g., 20nt guide + NGG for Cas9)"
        )
        st.session_state.crispresso["guide_seq"] = guide_seq
    
    # Installation method
    st.markdown("**CRISPResso2 Environment:**")
    
    env_mode = st.radio(
        "CRISPResso2 Installation Method:",
        ["PATH", "Conda Environment"],
        index=0 if st.session_state.crispresso.get("env_mode", "path") == "path" else 1,
        help="How CRISPResso2 is installed on your system"
    )
    
    if env_mode == "Conda Environment":
        conda_env = st.text_input(
            "Conda Environment Name", 
            value=st.session_state.crispresso.get("conda_env", ""),
            help="Name of the Conda environment where CRISPResso2 is installed"
        )
        st.session_state.crispresso["conda_env"] = conda_env
    else:
        st.session_state.crispresso["env_mode"] = "path"
        st.session_state.crispresso["conda_env"] = ""
    
    # Save settings
    if st.button("Save Input Settings"):
        if not st.session_state.crispresso["fastq_r1"]:
            st.error("Please provide at least R1 FASTQ file.")
        elif not st.session_state.crispresso["amplicon_seq"]:
            st.error("Please provide the amplicon sequence.")
        elif not st.session_state.crispresso["guide_seq"]:
            st.error("Please provide the guide RNA sequence.")
        elif env_mode == "Conda Environment" and not st.session_state.crispresso["conda_env"]:
            st.error("Please provide the Conda environment name.")
        else:
            st.success("Input settings saved. Switch to the 'Run CRISPResso2' tab to continue.")

with tab2:
    st.markdown('<div class="subheader">Run CRISPResso2</div>', unsafe_allow_html=True)
    
    # Verify if we have the necessary inputs
    if not st.session_state.crispresso.get("fastq_r1") or not st.session_state.crispresso.get("amplicon_seq") or not st.session_state.crispresso.get("guide_seq"):
        st.warning("Please complete the Input Data tab first.")
    else:
        # CRISPResso2 parameters
        st.markdown("**Analysis Parameters:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            experiment_name = st.text_input(
                "Experiment Name", 
                value=st.session_state.crispresso.get("parameters", {}).get("name", "CRISPResso_experiment"),
                help="Name for this experiment (used for output directory naming)"
            )
            
            window_size = st.number_input(
                "Quantification Window Size", 
                min_value=1, 
                value=int(st.session_state.crispresso.get("parameters", {}).get("window", 20)),
                help=get_llm_tooltip("Window Size", "CRISPResso2")
            )
        
        with col2:
            output_dir = st.text_input(
                "Output Directory",
                value=st.session_state.crispresso.get("output_dir", ""),
                help="Directory where CRISPResso2 results will be saved (leave empty for default)"
            )
            
            min_reads = st.number_input(
                "Minimum Reads",
                min_value=1,
                value=int(st.session_state.crispresso.get("parameters", {}).get("min_reads", 100)),
                help=get_llm_tooltip("Minimum Reads", "CRISPResso2")
            )
        
        # Advanced parameters
        with st.expander("Advanced Parameters"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                exclude_indels = st.checkbox(
                    "Exclude Indels",
                    value=st.session_state.crispresso.get("parameters", {}).get("exclude_indels", False),
                    help=get_llm_tooltip("Exclude Indels", "CRISPResso2")
                )
                
                ignore_substitutions = st.checkbox(
                    "Ignore Substitutions",
                    value=st.session_state.crispresso.get("parameters", {}).get("ignore_substitutions", False),
                    help=get_llm_tooltip("Ignore Substitutions", "CRISPResso2")
                )
            
            with col2:
                base_editor = st.checkbox(
                    "Base Editor Mode",
                    value=st.session_state.crispresso.get("parameters", {}).get("base_editor", False),
                    help=get_llm_tooltip("Base Editor Mode", "CRISPResso2")
                )
                
                plot_window_size = st.number_input(
                    "Plot Window Size",
                    min_value=1,
                    value=int(st.session_state.crispresso.get("parameters", {}).get("plot_window", 20)),
                    help=get_llm_tooltip("Plot Window Size", "CRISPResso2")
                )
            
            with col3:
                hdr_seq = st.text_input(
                    "HDR Sequence",
                    value=st.session_state.crispresso.get("parameters", {}).get("hdr", ""),
                    help=get_llm_tooltip("HDR Sequence", "CRISPResso2")
                )
                
                additional_params = st.text_area(
                    "Additional Parameters",
                    value=st.session_state.crispresso.get("parameters", {}).get("additional", ""),
                    help="Additional command-line parameters for CRISPResso2"
                )
        
        # Collect parameters into session state
        parameters = {
            "name": experiment_name,
            "window": window_size,
            "min_reads": min_reads,
            "exclude_indels": exclude_indels,
            "ignore_substitutions": ignore_substitutions,
            "base_editor": base_editor,
            "plot_window": plot_window_size,
            "hdr": hdr_seq,
            "additional": additional_params
        }
        
        st.session_state.crispresso["parameters"] = parameters
        st.session_state.crispresso["output_dir"] = output_dir
        
        # Run button
        if st.button("Run CRISPResso2"):
            # Verify CRISPResso2 installation
            progress_placeholder = st.empty()
            progress_placeholder.info("Verifying CRISPResso2 installation...")
            
            env_mode = "conda" if st.session_state.crispresso.get("env_mode") == "Conda Environment" else "path"
            conda_env = st.session_state.crispresso.get("conda_env", "")
            
            crispresso_available, message = verify_crispresso_installation(env_mode, conda_env)
            
            if not crispresso_available:
                progress_placeholder.error(f"CRISPResso2 installation check failed: {message}")
                st.stop()
            
            # Build the command
            progress_placeholder.info("Preparing CRISPResso2 command...")
            
            cmd_params = {
                "fastq_r1": st.session_state.crispresso["fastq_r1"],
                "fastq_r2": st.session_state.crispresso.get("fastq_r2"),
                "amplicon_seq": st.session_state.crispresso["amplicon_seq"],
                "guide_seq": st.session_state.crispresso["guide_seq"],
                "output_dir": output_dir,
                "experiment_name": experiment_name,
                "window_size": window_size,
                "min_reads": min_reads,
                "exclude_indels": exclude_indels,
                "ignore_substitutions": ignore_substitutions,
                "base_editor": base_editor,
                "plot_window_size": plot_window_size,
                "hdr_seq": hdr_seq,
                "additional_params": additional_params,
                "env_mode": env_mode,
                "conda_env": conda_env
            }
            
            process, cmd_str = build_crispresso_command(cmd_params)
            
            # Show the command
            st.code(cmd_str, language="bash")
            
            # Create output containers
            stdout_container = st.empty()
            stderr_container = st.empty()
            
            # Run CRISPResso2
            progress_placeholder.info("Running CRISPResso2... This may take a while.")
            
            # Start the process
            if process:
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
                            if "Processing" in line or "Loaded" in line or "Computing" in line:
                                progress_placeholder.info(f"Running CRISPResso2: {line.strip()}")
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
                    progress_placeholder.success("CRISPResso2 completed successfully!")
                    
                    # Extract the output directory
                    output_dir = extract_output_dir(stdout_text)
                    if output_dir:
                        st.session_state.crispresso_results = {
                            "path": output_dir,
                            "summary": None,
                            "data": None
                        }
                        
                        # Show a message to switch to the Results tab
                        st.success(f"CRISPResso2 run completed. Results saved to: {output_dir}")
                        st.info("Switch to the 'Results' tab to view the analysis results.")
                    else:
                        progress_placeholder.warning("Could not determine output directory from CRISPResso2 output.")
                else:
                    progress_placeholder.error(f"CRISPResso2 failed with return code {return_code}")
            else:
                progress_placeholder.error("Failed to start CRISPResso2 process.")

with tab3:
    st.markdown('<div class="subheader">CRISPResso2 Results</div>', unsafe_allow_html=True)
    
    # Check if we have results to display
    if "crispresso_results" in st.session_state and st.session_state.crispresso_results.get("path"):
        results_path = st.session_state.crispresso_results["path"]
        
        st.success(f"Displaying results from: {results_path}")
        
        # Display results
        try:
            # Check if the results path exists
            results_dir = Path(results_path)
            if not results_dir.exists():
                st.error(f"Results directory not found: {results_path}")
                st.stop()
            
            # Look for key output files
            quantification_file = next(results_dir.glob("*Quantification_of_editing_frequency.txt"), None)
            alleles_file = next(results_dir.glob("*Alleles_frequency_table.txt"), None)
            summary_file = next(results_dir.glob("CRISPResso_mapping_statistics.txt"), None)
            
            # Summary statistics
            if summary_file:
                st.subheader("Summary Statistics")
                
                # Read summary file
                summary_data = {}
                with open(summary_file, 'r') as f:
                    for line in f:
                        if ":" in line:
                            key, value = line.strip().split(":", 1)
                            summary_data[key.strip()] = value.strip()
                
                # Display summary
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Reads", summary_data.get("Total Reads", "N/A"))
                    st.metric("Reads with Modifications", summary_data.get("Reads with Modifications", "N/A"))
                
                with col2:
                    st.metric("Alignment Rate", summary_data.get("Alignment Rate", "N/A"))
                    st.metric("Modification Rate", summary_data.get("Modification Rate", "N/A"))
                
                # AI analysis of the summary
                if "crispresso_results" in st.session_state and not st.session_state.crispresso_results.get("summary"):
                    # Generate LLM explanation of the results
                    summary_explanation = explain_results_with_llm("summary statistics", str(summary_data))
                    st.session_state.crispresso_results["summary"] = summary_explanation
                
                # Display the explanation
                if st.session_state.crispresso_results.get("summary"):
                    st.info(st.session_state.crispresso_results["summary"])
            
            # Alleles frequency table
            if alleles_file:
                st.subheader("Alleles Frequency")
                
                # Read alleles file
                alleles_df = pd.read_csv(alleles_file, sep='\t')
                
                # Display alleles table
                st.dataframe(alleles_df)
                
                # Download button
                csv = alleles_df.to_csv().encode('utf-8')
                st.download_button(
                    "Download Alleles Data as CSV",
                    csv,
                    "crispresso_alleles.csv",
                    "text/csv",
                    key='download-alleles-csv'
                )
            
            # Display plots
            st.subheader("Visualization")
            
            # Find plot files
            plot_files = list(results_dir.glob("*.pdf")) + list(results_dir.glob("*.png"))
            
            if plot_files:
                # Group plots by type
                plot_types = {
                    "editing": [p for p in plot_files if "editing" in p.name.lower()],
                    "nucleotide": [p for p in plot_files if "nucleotide" in p.name.lower()],
                    "indel": [p for p in plot_files if "indel" in p.name.lower() or "frameshift" in p.name.lower()],
                    "other": []
                }
                
                # Add other plots
                for plot in plot_files:
                    if not any(plot in group for group in plot_types.values()):
                        plot_types["other"].append(plot)
                
                # Display plots by group
                for group_name, plots in plot_types.items():
                    if plots:
                        with st.expander(f"{group_name.title()} Plots ({len(plots)})"):
                            for plot in plots:
                                if plot.suffix.lower() == '.png':
                                    st.image(str(plot), caption=plot.stem)
                                else:
                                    st.markdown(f"[Download {plot.name}]({plot})")
            else:
                st.warning("No plot files found in the results directory.")
            
            # Q&A system for results interpretation
            st.subheader("Ask About Your Results")
            
            user_question = st.text_input(
                "Ask a question about your CRISPR editing results:",
                placeholder="Example: What was the main type of editing observed?"
            )
            
            if user_question and st.button("Ask AI Assistant"):
                # Prepare data for the LLM
                data_context = ""
                
                if summary_data:
                    data_context += "Summary Statistics:\n" + "\n".join([f"{k}: {v}" for k, v in summary_data.items()]) + "\n\n"
                
                if 'alleles_df' in locals() and not alleles_df.empty:
                    data_context += f"Top Alleles:\n{alleles_df.head(5).to_string()}\n\n"
                
                # Get AI response
                prompt = f"""
                User question: {user_question}
                
                Here is data from their CRISPResso2 analysis:
                
                {data_context}
                
                Provide a clear and concise answer to their question based on this data.
                """
                
                answer = ask_llm(prompt)
                st.info(answer)
        
        except Exception as e:
            st.error(f"Error parsing CRISPResso2 results: {str(e)}")
    else:
        st.info("No CRISPResso2 results available. Please run CRISPResso2 first.")

with tab4:
    st.markdown('<div class="subheader">Advanced Analysis</div>', unsafe_allow_html=True)
    
    # Check if we have results to display
    if "crispresso_results" in st.session_state and st.session_state.crispresso_results.get("path"):
        results_path = st.session_state.crispresso_results["path"]
        
        st.success(f"Displaying advanced analysis from: {results_path}")
        
        # Display advanced analysis
        try:
            # Check if the results path exists
            results_dir = Path(results_path)
            if not results_dir.exists():
                st.error(f"Results directory not found: {results_path}")
                st.stop()
            
            # Select experiment type for context-aware analysis
            experiment_type = st.selectbox(
                "Experiment Type",
                ["knockout", "knockin", "base_editing"],
                help="Select your experiment type for context-aware analysis"
            )
            
            # Initialize the enhanced result parser
            parser = EnhancedResultParser(results_path, experiment_type)
            
            # Load the results
            with st.spinner("Loading and analyzing results..."):
                parser.load_results()
            
            # Create tabs for different analysis views
            analysis_tabs = st.tabs([
                "Efficiency Analysis", 
                "Mutation Patterns", 
                "Experiment Success", 
                "LLM Summary"
            ])
            
            # Tab 1: Efficiency Analysis
            with analysis_tabs[0]:
                st.subheader("Editing Efficiency Analysis")
                
                # Generate visualizations
                vis_output_dir = os.path.join(results_path, "enhanced_visualizations")
                visualizations = parser.generate_visualizations(vis_output_dir)
                
                # Display efficiency metrics
                metrics = parser.get_detailed_metrics()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Overall Editing Efficiency", f"{metrics.get('overall_efficiency', 'N/A')}%")
                with col2:
                    st.metric("Indel Frequency", f"{metrics.get('indel_frequency', 'N/A')}%")
                with col3:
                    st.metric("Frameshifts", f"{metrics.get('frameshift_frequency', 'N/A')}%")
                
                # Display visualizations
                if "efficiency_plot" in visualizations:
                    st.image(visualizations["efficiency_plot"], caption="Editing Efficiency")
                
                if "nucleotide_distribution" in visualizations:
                    st.image(visualizations["nucleotide_distribution"], caption="Nucleotide Distribution")
            
            # Tab 2: Mutation Patterns
            with analysis_tabs[1]:
                st.subheader("Mutation Pattern Analysis")
                
                # Display allele patterns
                if hasattr(parser, "alleles_data") and parser.alleles_data is not None:
                    st.subheader("Top Alleles")
                    st.dataframe(parser.alleles_data.head(10))
                
                # Display visualizations
                if "mutation_position" in visualizations:
                    st.image(visualizations["mutation_position"], caption="Mutation Position Distribution")
                
                if "indel_size" in visualizations:
                    st.image(visualizations["indel_size"], caption="Indel Size Distribution")
                
                # Display pattern metrics
                pattern_metrics = parser.get_mutation_pattern_metrics()
                
                st.subheader("Mutation Patterns")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Most Common Mutation", pattern_metrics.get("most_common_mutation", "N/A"))
                    st.metric("Deletion:Insertion Ratio", pattern_metrics.get("del_ins_ratio", "N/A"))
                with col2:
                    st.metric("Mean Indel Size", pattern_metrics.get("mean_indel_size", "N/A"))
                    st.metric("HDR Efficiency", f"{pattern_metrics.get('hdr_efficiency', 'N/A')}%")
            
            # Tab 3: Experiment Success
            with analysis_tabs[2]:
                st.subheader("Experiment Success Evaluation")
                
                # Get success metrics based on experiment type
                success_metrics = parser.evaluate_experiment_success()
                
                # Display success gauge/progress
                success_score = success_metrics.get("success_score", 0)
                
                # Use a progress bar to show success score (0-100)
                st.progress(success_score / 100)
                st.metric("Success Score", f"{success_score:.1f}%")
                
                # Display success factors
                st.subheader("Success Factors")
                
                for factor, details in success_metrics.get("factors", {}).items():
                    score = details.get("score", 0)
                    explanation = details.get("explanation", "")
                    
                    # Create expandable section for each factor
                    with st.expander(f"{factor}: {score}/100"):
                        st.write(explanation)
                
                # Display recommendations
                st.subheader("Recommendations")
                recommendations = success_metrics.get("recommendations", [])
                
                for i, rec in enumerate(recommendations):
                    st.markdown(f"**{i+1}.** {rec}")
                
                # Compare with expected outcomes
                st.subheader("Comparison with Expected Outcomes")
                
                expected_vs_actual = parser.compare_with_expected_outcomes()
                st.dataframe(expected_vs_actual)
            
            # Tab 4: LLM Summary
            with analysis_tabs[3]:
                st.subheader("AI-Generated Summary")
                
                # Get enhanced summary from parser
                if st.button("Generate Enhanced Summary"):
                    with st.spinner("Generating comprehensive analysis..."):
                        summary = parser.generate_enhanced_summary()
                        st.session_state.crispresso_results["enhanced_summary"] = summary
                
                # Display the summary if available
                if "enhanced_summary" in st.session_state.crispresso_results:
                    st.markdown(st.session_state.crispresso_results["enhanced_summary"])
                else:
                    st.info("Click 'Generate Enhanced Summary' to create a comprehensive analysis of your results.")
                
                # Add specialized interpretation based on experiment type
                st.subheader(f"Specialized {experiment_type.replace('_', ' ').title()} Analysis")
                
                if experiment_type == "knockout":
                    ko_analysis = parser.get_knockout_specific_analysis()
                    st.write(ko_analysis)
                elif experiment_type == "knockin":
                    ki_analysis = parser.get_knockin_specific_analysis()
                    st.write(ki_analysis)
                elif experiment_type == "base_editing":
                    be_analysis = parser.get_base_editing_specific_analysis()
                    st.write(be_analysis)
        
        except Exception as e:
            st.error(f"Error in advanced analysis: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("No CRISPResso2 results available. Please run CRISPResso2 first.")

with tab5:
    st.markdown('<div class="subheader">Next Steps & Recommendations</div>', unsafe_allow_html=True)
    
    # Check if we have results to display
    if "crispresso_results" in st.session_state and st.session_state.crispresso_results.get("path"):
        results_path = st.session_state.crispresso_results["path"]
        
        st.success(f"Generating recommendations based on results from: {results_path}")
        
        # Add educational sidebar
        create_educational_sidebar()
        
        # Get experiment info from previous tabs
        experiment_type = st.selectbox(
            "Experiment Type",
            ["knockout", "knockin", "base_editing"],
            index=0,
            help="Select your experiment type for tailored recommendations"
        )
        
        target_gene = st.text_input(
            "Target Gene Symbol",
            value=st.session_state.get("target_gene", ""),
            help="Enter the gene symbol for context-aware recommendations"
        )
        
        # Create tabs for different recommendation aspects
        rec_tabs = st.tabs(["Result Summary", "Next Steps", "Troubleshooting", "Validation Protocol"])
        
        # Prepare results data for recommendations
        results_data = {}
        if "crispresso_analysis" in st.session_state:
            analysis = st.session_state.crispresso_analysis
            
            # Extract key metrics
            if "Quantification_window_modification_frequency" in analysis:
                results_data["editing_efficiency"] = analysis["Quantification_window_modification_frequency"] * 100
            
            if "Quantification_window_insertion_frequency" in analysis:
                results_data["insertion_frequency"] = analysis["Quantification_window_insertion_frequency"] * 100
            
            if "Quantification_window_deletion_frequency" in analysis:
                results_data["deletion_frequency"] = analysis["Quantification_window_deletion_frequency"] * 100
            
            if "Quantification_window_substitution_frequency" in analysis:
                results_data["substitution_frequency"] = analysis["Quantification_window_substitution_frequency"] * 100
            
            # Calculate frameshift percentage if available
            if "Frameshift_analysis" in analysis and "frameshifts_total" in analysis["Frameshift_analysis"]:
                frameshift = analysis["Frameshift_analysis"]["frameshifts_total"]
                non_frameshift = analysis["Frameshift_analysis"].get("non_frameshifts_total", 0)
                if frameshift + non_frameshift > 0:
                    results_data["frameshift_percent"] = frameshift / (frameshift + non_frameshift) * 100
            
            # For HDR experiments
            if experiment_type == "knockin":
                # Estimate HDR efficiency (if data available)
                hdr_efficiency = results_data.get("substitution_frequency", 0)
                results_data["hdr_efficiency"] = hdr_efficiency
            
            # For base editing experiments
            if experiment_type == "base_editing":
                # Check for bystander edits
                results_data["bystander_edits"] = False
                if results_data.get("substitution_frequency", 0) > 5:
                    results_data["bystander_edits"] = True
        
        # Create dummy data if no metrics available
        if not results_data:
            results_data = {
                "editing_efficiency": 25.0,
                "insertion_frequency": 5.0,
                "deletion_frequency": 15.0,
                "substitution_frequency": 5.0,
                "frameshift_percent": 60.0
            }
            
            if experiment_type == "knockin":
                results_data["hdr_efficiency"] = 10.0
            
            if experiment_type == "base_editing":
                results_data["bystander_edits"] = True
        
        # Identify potential issues based on results
        issues = []
        if results_data.get("editing_efficiency", 0) < 20:
            issues.append("low_editing_efficiency")
        elif results_data.get("editing_efficiency", 0) < 5:
            issues.append("no_editing")
        
        if experiment_type == "knockin" and results_data.get("hdr_efficiency", 0) < 10:
            issues.append("low_hdr_efficiency")
        
        if experiment_type == "base_editing" and results_data.get("bystander_edits", False):
            issues.append("base_editing_bystander")
        
        # Tab 1: Result Summary
        with rec_tabs[0]:
            st.subheader("Experiment Results Summary")
            
            # Create metrics row
            col1, col2, col3 = st.columns(3)
            
            with col1:
                editing_eff = results_data.get("editing_efficiency", 0)
                st.metric("Overall Editing Efficiency", f"{editing_eff:.1f}%")
            
            with col2:
                if experiment_type == "knockout":
                    frameshift = results_data.get("frameshift_percent", 0)
                    st.metric("Frameshift Mutations", f"{frameshift:.1f}%")
                elif experiment_type == "knockin":
                    hdr = results_data.get("hdr_efficiency", 0)
                    st.metric("HDR Efficiency", f"{hdr:.1f}%")
                elif experiment_type == "base_editing":
                    subst = results_data.get("substitution_frequency", 0)
                    st.metric("Base Conversion Efficiency", f"{subst:.1f}%")
            
            with col3:
                # Show success rating
                success_threshold = {
                    "knockout": 30,
                    "knockin": 10,
                    "base_editing": 20
                }
                
                main_metric = editing_eff
                if experiment_type == "knockin":
                    main_metric = results_data.get("hdr_efficiency", 0)
                elif experiment_type == "base_editing":
                    main_metric = results_data.get("substitution_frequency", 0)
                
                threshold = success_threshold.get(experiment_type, 30)
                
                if main_metric >= threshold:
                    st.success(f"Experiment Status: **Successful**")
                elif main_metric >= threshold / 2:
                    st.warning(f"Experiment Status: **Partially Successful**")
                else:
                    st.error(f"Experiment Status: **Needs Optimization**")
            
            # Decision support section
            decision_support = analyze_results_decision_support(experiment_type, results_data)
            
            st.subheader("Result Interpretation")
            st.markdown(f"**{decision_support['interpretation']}**")
            
            # Display decision points in expandable sections
            st.subheader("Detailed Analysis")
            for point in decision_support["decision_points"]:
                with st.expander(point["scenario"]):
                    st.markdown(f"**Interpretation:** {point['interpretation']}")
                    st.markdown("**Recommended Next Steps:**")
                    for step in point["next_steps"]:
                        st.markdown(f"- {step}")
        
        # Tab 2: Next Steps
        with rec_tabs[1]:
            st.subheader("Recommended Next Steps")
            
            if st.button("Generate Comprehensive Recommendations"):
                with st.spinner("Generating personalized next steps recommendations..."):
                    # Get gene info
                    gene_info = {"symbol": target_gene} if target_gene else {}
                    
                    # Generate recommendation
                    recommendation = get_next_steps_recommendation(
                        editing_type=experiment_type,
                        result_data=results_data,
                        issue_list=issues
                    )
                    
                    # Save to session state
                    if "next_steps" not in st.session_state:
                        st.session_state.next_steps = {}
                    
                    key = f"{experiment_type}_{target_gene}"
                    st.session_state.next_steps[key] = recommendation
            
            # Display recommendation if available
            key = f"{experiment_type}_{target_gene}"
            if "next_steps" in st.session_state and key in st.session_state.next_steps:
                st.markdown(st.session_state.next_steps[key])
                
                # Add download button
                st.download_button(
                    "Download Recommendations",
                    st.session_state.next_steps[key],
                    f"CRISPR_{experiment_type}_next_steps.txt",
                    "text/plain",
                    key="download-next-steps"
                )
            else:
                # Show basic next experiment recommendation
                next_exp = recommend_next_experiment(experiment_type, results_data)
                
                st.markdown("### Key Next Steps")
                for step in next_exp["prioritized_next_steps"]:
                    st.markdown(f"- {step}")
                
                st.markdown("*Click 'Generate Comprehensive Recommendations' for detailed, AI-generated guidance.*")
        
        # Tab 3: Troubleshooting
        with rec_tabs[2]:
            st.subheader("Troubleshooting Guidance")
            
            # Let user select issues they're experiencing
            available_issues = [
                ("low_editing_efficiency", "Low Editing Efficiency (<20% indels)"),
                ("no_editing", "No Detectable Editing"),
                ("high_off_target", "High Off-Target Effects"),
                ("mixed_population", "Heterogeneous Editing Results"),
                ("low_hdr_efficiency", "Low HDR Efficiency (for knock-in)"),
                ("base_editing_bystander", "Bystander Edits in Base Editing")
            ]
            
            selected_issues = []
            if issues:
                # Pre-select issues based on results
                default_indices = [i for i, (issue_code, _) in enumerate(available_issues) if issue_code in issues]
                selected_issues = st.multiselect(
                    "Select issues you're experiencing:",
                    [label for _, label in available_issues],
                    default=[available_issues[i][1] for i in default_indices if i < len(available_issues)]
                )
            else:
                selected_issues = st.multiselect(
                    "Select issues you're experiencing:",
                    [label for _, label in available_issues]
                )
            
            # Convert selected labels back to issue codes
            issue_codes = []
            for selected in selected_issues:
                for code, label in available_issues:
                    if label == selected:
                        issue_codes.append(code)
                        break
            
            # Get troubleshooting suggestions
            if issue_codes:
                troubleshooting = suggest_troubleshooting(experiment_type, issue_codes)
                
                # Display issues
                for issue in troubleshooting["issues"]:
                    with st.expander(f"{issue['issue']}: {issue['description']}", expanded=True):
                        # Potential causes
                        st.markdown("**Potential Causes:**")
                        for cause in issue["potential_causes"]:
                            st.markdown(f"- {cause['cause']} ({cause['likelihood']} likelihood)")
                        
                        # Solutions
                        st.markdown("**Recommended Solutions:**")
                        for solution in issue["solutions"]:
                            st.markdown(f"- {solution}")
            else:
                # Show some general troubleshooting tips
                st.info("Select issues from the list above to get specific troubleshooting guidance.")
                
                st.markdown("### General Troubleshooting Tips")
                st.markdown("""
                - **Verify components**: Confirm activity of Cas9 and guide RNA
                - **Check delivery**: Ensure transfection/delivery efficiency
                - **Optimize parameters**: Adjust Cas9:guide ratio, timing, cell density
                - **Consider cell type**: Some cell lines are more difficult to edit
                - **Validate detection**: Ensure your assay is sensitive enough
                """)
        
        # Tab 4: Validation Protocol
        with rec_tabs[3]:
            st.subheader("Validation Protocol Generator")
            
            # Show gene input if not already provided
            if not target_gene:
                target_gene = st.text_input(
                    "Enter Target Gene Symbol",
                    help="Enter gene symbol for a tailored validation protocol",
                    key="target_gene_validation"
                )
            
            gene_info = {
                "symbol": target_gene,
                "experiment_type": experiment_type
            }
            
            # Add dropdown for cell type
            cell_types = ["HEK293", "HeLa", "K562", "U2OS", "iPSC", "Primary cells", "Other"]
            cell_type = st.selectbox("Cell Type", cell_types)
            gene_info["cell_type"] = cell_type
            
            if st.button("Generate Validation Protocol"):
                with st.spinner("Generating detailed validation protocol..."):
                    protocol = generate_validation_protocol(
                        editing_type=experiment_type,
                        gene_info=gene_info,
                        current_results=results_data
                    )
                    
                    # Save to session state
                    if "validation_protocol" not in st.session_state:
                        st.session_state.validation_protocol = {}
                    
                    key = f"{experiment_type}_{target_gene}_{cell_type}"
                    st.session_state.validation_protocol[key] = protocol
            
            # Display protocol if available
            key = f"{experiment_type}_{target_gene}_{cell_type}"
            if "validation_protocol" in st.session_state and key in st.session_state.validation_protocol:
                st.markdown(st.session_state.validation_protocol[key])
                
                # Add download button
                st.download_button(
                    "Download Protocol",
                    st.session_state.validation_protocol[key],
                    f"CRISPR_{experiment_type}_validation_protocol.txt",
                    "text/plain",
                    key="download-protocol"
                )
            else:
                st.info("Click 'Generate Validation Protocol' to create a detailed protocol for validating your editing experiment.")
    else:
        st.info("No CRISPResso2 results available. Please run CRISPResso2 first to get recommendations.") 