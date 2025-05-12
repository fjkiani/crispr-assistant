import streamlit as st
from dotenv import load_dotenv
import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import time
import threading
import queue
import re
import shlex
import shutil
import pandas as pd
import importlib.util

# Load environment variables from .env file
load_dotenv()

# Import LLM API dynamically
def import_llm_api():
    """Import the LLM API module from tools/llm_api.py"""
    try:
        # Try to import the module
        spec = importlib.util.spec_from_file_location("llm_api", "tools/llm_api.py")
        llm_api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(llm_api)
        return llm_api
    except Exception as e:
        st.error(f"Error importing LLM API: {str(e)}")
        return None

llm_api = import_llm_api()

# Import educational context and coordinate handler dynamically
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

# Function to call LLM
def ask_llm(prompt, provider="gemini"):
    """Call the LLM API with a prompt and return the response"""
    if llm_api is None:
        return "LLM API not available."
    
    try:
        response = llm_api.query_llm(prompt, provider=provider)
        return response
    except Exception as e:
        st.error(f"Error calling LLM: {str(e)}")
        return f"Error: {str(e)}"

# Define paths
CHOPCHOP_DIR = Path("tools/chopchop")
CONFIG_LOCAL_PATH = CHOPCHOP_DIR / "config_local.json"
CHOPCHOP_SCRIPT_PATH = CHOPCHOP_DIR / "chopchop_integration.py"

# CRISPResso2 function definitions
def verify_crispresso_installation(env_mode, conda_env=None):
    """Verify that CRISPResso2 is installed and available"""
    cmd = []
    
    if env_mode == "conda" and conda_env:
        cmd = ["conda", "run", "-n", conda_env, "CRISPResso", "--version"]
    else:
        cmd = ["CRISPResso", "--version"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr.strip()}"
    except FileNotFoundError:
        if env_mode == "conda":
            return False, f"Error: Conda or the environment '{conda_env}' may not be available."
        else:
            return False, "Error: CRISPResso2 not found in PATH. Make sure it's installed or use Conda environment mode."

def build_crispresso_command(params):
    """Build the CRISPResso2 command based on parameters"""
    cmd = []
    
    # Add conda prefix if using a conda environment
    if params['env_mode'] == 'conda' and params['conda_env']:
        cmd.extend(["conda", "run", "-n", params['conda_env']])
    
    # Basic CRISPResso command
    cmd.append("CRISPResso")
    
    # Required parameters
    cmd.extend(["-r1", params['fastq_r1']])
    
    if params['fastq_r2']:
        cmd.extend(["-r2", params['fastq_r2']])
    
    cmd.extend(["-a", params['amplicon_seq']])
    cmd.extend(["-g", params['guide_seq']])
    
    # Optional parameters
    if params.get('experiment_name'):
        cmd.extend(["-n", params['experiment_name']])
    
    if params.get('quant_window_size'):
        cmd.extend(["--quantification_window_size", str(params['quant_window_size'])])
    
    if params.get('min_read_quality', 0) > 0:
        cmd.extend(["--min_average_read_quality", str(params['min_read_quality'])])
    
    if params.get('output_dir'):
        cmd.extend(["--output_folder", params['output_dir']])
    
    # Add HDR parameters if applicable
    if params.get('expected_hdr_seq'):
        cmd.extend(["--expected_hdr_amplicon_seq", params['expected_hdr_seq']])
    
    # Add Base Editing parameters if applicable
    if params.get('base_editor_output'):
        cmd.extend(["--base_editor_output"])
        
        if params.get('conversion_nuc_from') and params.get('conversion_nuc_to'):
            cmd.extend([
                "--conversion_nuc_from", params['conversion_nuc_from'],
                "--conversion_nuc_to", params['conversion_nuc_to']
            ])
    
    # Other options
    if params.get('ignore_substitutions'):
        cmd.extend(["--ignore_substitutions_at_ends"])
    
    # Add any additional arguments
    if params.get('additional_args'):
        cmd.extend(shlex.split(params['additional_args']))
    
    return cmd

def run_chopchop(target, enzyme, genome_assembly, guide_length, pam, output_dir, additional_args):
    """Run the CHOPCHOP script with the given parameters"""
    
    # Capitalize enzyme name for the script
    script_enzyme = enzyme.capitalize()

    # Build the command
    cmd = [
        sys.executable,
        str(CHOPCHOP_SCRIPT_PATH),
        "--target", target,
        "--enzyme", script_enzyme,
        "--genome", genome_assembly,
        "--guide_length", str(guide_length),
        "--pam", pam,
        "--output", output_dir
    ]
    
    # Add any additional arguments
    if additional_args:
        # Split by space but respect quoted values
        extra_args = shlex.split(additional_args)
        cmd.extend(extra_args)
    
    # Run the command and capture output
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    return process

def extract_output_dir(stdout_text):
    """Extract the CRISPResso2 output directory from stdout"""
    # CRISPResso2 typically outputs a line like:
    # "Results will be available in folder: CRISPResso_on_..."
    pattern = r"Results will be available in folder:?\s+(\S+)"
    match = re.search(pattern, stdout_text)
    
    if match:
        return match.group(1)
    else:
        return None

# Initialize session state
def init_session_state():
    """Initialize session state with default values if keys don't exist"""
    # CHOPCHOP Configuration state
    if 'chopchop_config' not in st.session_state:
        st.session_state.chopchop_config = {
            "organism": "",
            "assembly": "",
            "two_bit_file": "",
            "bowtie_index": "",
            "gene_annotation": ""
        }
    
    # CHOPCHOP Run parameters state
    if 'chopchop_run' not in st.session_state:
        st.session_state.chopchop_run = {
            "target": "",
            "enzyme": "cas9",  # Always lowercase for consistency
            "guide_length": 20,
            "pam": "NGG",
            "output_dir": "",
            "additional_args": ""
        }
    
    # CHOPCHOP Results state
    if 'chopchop_results' not in st.session_state:
        st.session_state.chopchop_results = {
            "path": None,
            "guides": None,
            "summary": None
        }
    
    # CRISPResso2 state (will be expanded later)
    if 'crispresso' not in st.session_state:
        st.session_state.crispresso = {
            "fastq_r1": "",
            "fastq_r2": "",
            "amplicon_seq": "",
            "guide_seq": "",
            "output_dir": "",
            "env_mode": "path",  # 'path' or 'conda'
            "conda_env": "",
            "parameters": {}
        }
    
    # CRISPResso2 Results state
    if 'crispresso_results' not in st.session_state:
        st.session_state.crispresso_results = {
            "path": None,
            "summary": None,
            "data": None
        }

# Function to update session state for CHOPCHOP results
def update_chopchop_results(path, guides=None):
    """Update the CHOPCHOP results in the session state"""
    st.session_state.chopchop_results = {
        "path": path,
        "guides": guides,
        "summary": None  # Will be added later with LLM integration
    }
    # For backward compatibility
    st.session_state.chopchop_results_path = path

def save_chopchop_config(config_data):
    """Save the CHOPCHOP configuration to config_local.json"""
    try:
        # Ensure the directory exists
        os.makedirs(CHOPCHOP_DIR, exist_ok=True)
        
        # Write the configuration to file
        with open(CONFIG_LOCAL_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return True, f"Configuration saved to {CONFIG_LOCAL_PATH}"
    except Exception as e:
        return False, f"Error saving configuration: {str(e)}"

def stream_subprocess_output(process, stdout_queue, stderr_queue):
    """Stream subprocess output to queues"""
    for line in iter(process.stdout.readline, ""):
        stdout_queue.put(line)
    process.stdout.close()
    
    for line in iter(process.stderr.readline, ""):
        stderr_queue.put(line)
    process.stderr.close()

def parse_chopchop_results(output_dir):
    """Parse the CHOPCHOP results from the top_guides.json file"""
    try:
        results_file = Path(output_dir) / "top_guides.json"
        if not results_file.exists():
            return None
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        return results
    except Exception as e:
        st.error(f"Error parsing CHOPCHOP results: {str(e)}")
        return None

def get_llm_tooltip(param_name, context="CHOPCHOP"):
    """Get LLM-generated tooltip explanation for a parameter"""
    cache_key = f"tooltip_{context}_{param_name}"
    
    # Check if we have this tooltip cached in session state
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    # Otherwise, generate it with the LLM
    prompt = f"""
    Explain the '{param_name}' parameter for {context} CRISPR tool in 1-2 sentences. 
    Be concise but informative for a scientist who needs clarity on this parameter.
    Focus on what it controls and why it matters.
    """
    
    tooltip = ask_llm(prompt)
    
    # Cache the result
    st.session_state[cache_key] = tooltip
    return tooltip

def explain_results_with_llm(result_type, data):
    """Generate an LLM explanation of results data"""
    prompt = f"""
    Below is {result_type} data from a CRISPResso2 analysis. 
    Provide a concise summary of what this data shows about the CRISPR editing outcomes.
    Focus on the key insights a scientist would find most relevant.
    
    DATA:
    {data}
    """
    
    explanation = ask_llm(prompt)
    return explanation

def chopchop_page():
    # Use styled header
    st.markdown('<div class="main-header">CHOPCHOP Guide Design</div>', unsafe_allow_html=True)
    
    # Create tabs for configuration and execution
    tab1, tab2, tab3 = st.tabs(["Configuration", "Run CHOPCHOP", "Results"])
    
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
            expected_two_bit_name = "hg38.2bit"
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
                organisms = list(config.keys())
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
                enzyme = st.selectbox("CRISPR Enzyme", 
                                    ["cas9", "cpf1", "cas13"], 
                                    index=0 if st.session_state.chopchop_run.get("enzyme", "") == "" else 
                                        ["cas9", "cpf1", "cas13"].index(st.session_state.chopchop_run.get("enzyme", "cas9")),
                                    help=get_llm_tooltip("CRISPR Enzyme"))
                
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
                    "enzyme": enzyme,
                    "guide_length": guide_length,
                    "pam": pam,
                    "output_dir": output_dir,
                    "additional_args": additional_args
                }
                
                # Validate inputs
                if not target or not genome_assembly:
                    st.error("Please fill in at least the target and genome assembly fields.")
                else:
                    # Initialize subprocess output containers
                    stdout_queue = queue.Queue()
                    stderr_queue = queue.Queue()
                    
                    # Create a progress placeholder
                    progress_placeholder = st.empty()
                    progress_placeholder.info("Starting CHOPCHOP...")
                    
                    # Create output containers
                    stdout_container = st.empty()
                    stderr_container = st.empty()
                    
                    # Run CHOPCHOP
                    process = run_chopchop(
                        target=target,
                        enzyme=enzyme,
                        genome_assembly=genome_assembly,
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
    
    with tab3:
        st.subheader("CHOPCHOP Results")
        
        # Check if we have results to display
        if st.session_state.chopchop_results["path"]:
            results_path = st.session_state.chopchop_results["path"]
            
            st.success(f"Displaying results from: {results_path}")
            
            # Extract and display the guides
            guides = st.session_state.chopchop_results["guides"]
            
            if guides:
                # Convert guides to a list of dictionaries for display
                guide_data = []
                for i, guide in enumerate(guides):
                    guide_dict = {
                        "Rank": i + 1,
                        "Sequence": guide.get('seq', ''),
                        "PAM": guide.get('pam', ''),
                        "Efficiency Score": guide.get('efficiency', ''),
                        "Specificity Score": guide.get('specificity', ''),
                        "Chromosome": guide.get('chr', ''),
                        "Start": guide.get('start', ''),
                        "End": guide.get('end', ''),
                        "Strand": guide.get('strand', '')
                    }
                    guide_data.append(guide_dict)
                
                # Display as a table
                st.dataframe(guide_data)
                
                # Add button to export results
                csv = []
                if guide_data:
                    df = pd.DataFrame(guide_data)
                    csv = df.to_csv().encode('utf-8')
                
                st.download_button(
                    "Download Guide Data as CSV",
                    csv,
                    "chopchop_guides.csv",
                    "text/csv",
                    key='download-csv'
                )
            else:
                st.warning("No guides found in the results.")
        else:
            st.info("No CHOPCHOP results available. Please run CHOPCHOP first.")

def crispresso_page():
    # Use styled header
    st.markdown('<div class="main-header">CRISPResso2 Analysis</div>', unsafe_allow_html=True)
    
    # Create tabs for input, execution, and results
    tab1, tab2, tab3 = st.tabs(["Input Data", "Run CRISPResso2", "Results"])
    
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
        
        # Add option to select from CHOPCHOP results if available
        guide_source = "Direct Input"
        if st.session_state.chopchop_results["guides"]:
            guide_source = st.radio(
                "Guide RNA Source:",
                ["Direct Input", "From CHOPCHOP Results"],
                help="Choose whether to enter guide RNA manually or select from CHOPCHOP results."
            )
        
        # If guide is from CHOPCHOP, show a dropdown
        guide_seq = ""
        if guide_source == "From CHOPCHOP Results":
            guides = st.session_state.chopchop_results["guides"]
            guide_options = []
            
            for i, guide in enumerate(guides):
                seq = guide.get('seq', '')
                pam = guide.get('pam', '')
                eff = guide.get('efficiency', '')
                spec = guide.get('specificity', '')
                option_text = f"Guide {i+1}: {seq} (PAM: {pam}, Efficiency: {eff}, Specificity: {spec})"
                guide_options.append((seq, option_text))
            
            selected_guide_index = st.selectbox(
                "Select Guide RNA from CHOPCHOP Results:",
                range(len(guide_options)),
                format_func=lambda i: guide_options[i][1]
            )
            
            guide_seq = guide_options[selected_guide_index][0]
            st.session_state.crispresso["guide_seq"] = guide_seq
        else:
            # Direct input for sequences
            col1, col2 = st.columns(2)
            
            with col1:
                amplicon_seq = st.text_area(
                    "Amplicon Sequence",
                    value=st.session_state.crispresso.get("amplicon_seq", ""),
                    help="Enter the amplicon sequence (DNA sequence surrounding your target site)"
                )
                st.session_state.crispresso["amplicon_seq"] = amplicon_seq
            
            with col2:
                guide_seq = st.text_area(
                    "Guide RNA Sequence",
                    value=st.session_state.crispresso.get("guide_seq", ""),
                    help="Enter the guide RNA sequence (without PAM)"
                )
                st.session_state.crispresso["guide_seq"] = guide_seq
        
        # CRISPResso2 environment
        st.markdown("**CRISPResso2 Environment:**")
        
        env_mode = st.radio(
            "CRISPResso2 Installation:",
            ["System PATH", "Conda Environment"],
            index=0 if st.session_state.crispresso.get("env_mode", "") == "path" else 1,
            help="Specify how CRISPResso2 is installed on your system"
        )
        
        st.session_state.crispresso["env_mode"] = "path" if env_mode == "System PATH" else "conda"
        
        if env_mode == "Conda Environment":
            conda_env = st.text_input(
                "Conda Environment Name",
                value=st.session_state.crispresso.get("conda_env", ""),
                help="Name of the Conda environment where CRISPResso2 is installed"
            )
            st.session_state.crispresso["conda_env"] = conda_env
        
        # CRISPResso2 parameters
        st.markdown("**CRISPResso2 Parameters:**")
        
        # Experiment parameters
        col1, col2 = st.columns(2)
        
        with col1:
            experiment_name = st.text_input(
                "Experiment Name",
                value=st.session_state.crispresso.get("experiment_name", ""),
                help="Name for this CRISPResso2 analysis (used for output directory)"
            )
            st.session_state.crispresso["experiment_name"] = experiment_name
            
            quant_window_size = st.number_input(
                "Quantification Window Size",
                min_value=1, 
                value=int(st.session_state.crispresso.get("quant_window_size", 20)),
                help="Size of the quantification window around the cleavage site"
            )
            st.session_state.crispresso["quant_window_size"] = quant_window_size
        
        with col2:
            min_read_quality = st.number_input(
                "Minimum Read Quality",
                min_value=0, 
                max_value=42,
                value=int(st.session_state.crispresso.get("min_read_quality", 0)),
                help="Minimum average read quality (phred33) to keep a read"
            )
            st.session_state.crispresso["min_read_quality"] = min_read_quality
            
            output_dir = st.text_input(
                "Output Directory",
                value=st.session_state.crispresso.get("output_dir", ""),
                help="Directory where CRISPResso2 results will be saved (leave empty for automatic)"
            )
            st.session_state.crispresso["output_dir"] = output_dir
        
        # Experiment type and advanced options
        experiment_type = st.radio(
            "Experiment Type:",
            ["NHEJ (Standard editing)", "HDR (Homology directed repair)", "Base Editing"],
            help=get_llm_tooltip("Experiment Type", context="CRISPResso2")
        )
        
        if experiment_type == "HDR (Homology directed repair)":
            expected_hdr_seq = st.text_area(
                "Expected HDR Amplicon Sequence",
                value=st.session_state.crispresso.get("expected_hdr_seq", ""),
                help=get_llm_tooltip("Expected HDR Amplicon Sequence", context="CRISPResso2")
            )
            st.session_state.crispresso["expected_hdr_seq"] = expected_hdr_seq
        
        elif experiment_type == "Base Editing":
            col1, col2 = st.columns(2)
            
            with col1:
                base_editor_output = st.selectbox(
                    "Base Editor Output",
                    ["BE-Mix (C to T + A to G)", "BE (C to T)", "ABE (A to G)"],
                    help=get_llm_tooltip("Base Editor Output", context="CRISPResso2")
                )
                
                conversion_nuc_from = st.selectbox(
                    "Conversion From",
                    ["C", "A"],
                    help=get_llm_tooltip("Conversion Nucleotide From", context="CRISPResso2")
                )
            
            with col2:
                conversion_nuc_to = st.selectbox(
                    "Conversion To",
                    ["T", "G"],
                    help=get_llm_tooltip("Conversion Nucleotide To", context="CRISPResso2")
                )
            
            st.session_state.crispresso["base_editor_output"] = base_editor_output
            st.session_state.crispresso["conversion_nuc_from"] = conversion_nuc_from
            st.session_state.crispresso["conversion_nuc_to"] = conversion_nuc_to
        
        # Advanced options
        with st.expander("Advanced Options"):
            ignore_substitutions = st.checkbox(
                "Ignore Substitutions at Ends",
                value=st.session_state.crispresso.get("ignore_substitutions", False),
                help="Ignore substitutions in the read ends when computing similarity"
            )
            st.session_state.crispresso["ignore_substitutions"] = ignore_substitutions
            
            additional_args = st.text_area(
                "Additional Command-Line Arguments",
                value=st.session_state.crispresso.get("additional_args", ""),
                help="Additional arguments to pass to the CRISPResso2 command"
            )
            st.session_state.crispresso["additional_args"] = additional_args
        
        # Input validation and next steps
        st.markdown("---")
        
        if st.button("Validate Inputs and Proceed to Execution"):
            # Validate inputs
            if not st.session_state.crispresso["fastq_r1"]:
                st.error("Please provide a FASTQ R1 file.")
            elif not st.session_state.crispresso["amplicon_seq"]:
                st.error("Please provide an amplicon sequence.")
            elif not st.session_state.crispresso["guide_seq"]:
                st.error("Please provide a guide RNA sequence.")
            elif st.session_state.crispresso["env_mode"] == "conda" and not st.session_state.crispresso["conda_env"]:
                st.error("Please provide a Conda environment name.")
            else:
                st.success("Input validation successful. Switch to 'Run CRISPResso2' tab to execute the analysis.")
                # Auto-switch to the Run tab
                st.session_state.active_tab = "Run CRISPResso2"
                st.rerun()
    
    with tab2:
        st.subheader("Run CRISPResso2")
        
        # Check if inputs are available
        if not st.session_state.crispresso["fastq_r1"] or not st.session_state.crispresso["amplicon_seq"] or not st.session_state.crispresso["guide_seq"]:
            st.warning("Please complete the input data in the 'Input Data' tab before running CRISPResso2.")
        else:
            # Show a summary of inputs
            st.markdown("**Summary of Inputs:**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**FASTQ Files:**")
                st.markdown(f"R1: {Path(st.session_state.crispresso['fastq_r1']).name}")
                if st.session_state.crispresso["fastq_r2"]:
                    st.markdown(f"R2: {Path(st.session_state.crispresso['fastq_r2']).name}")
                
                st.markdown(f"**Environment:** {'Conda: ' + st.session_state.crispresso['conda_env'] if st.session_state.crispresso['env_mode'] == 'conda' else 'System PATH'}")
            
            with col2:
                st.markdown(f"**Amplicon Length:** {len(st.session_state.crispresso['amplicon_seq'])} bp")
                st.markdown(f"**Guide Length:** {len(st.session_state.crispresso['guide_seq'])} bp")
                
                if st.session_state.crispresso.get("experiment_name"):
                    st.markdown(f"**Experiment Name:** {st.session_state.crispresso['experiment_name']}")
            
            # Verify CRISPResso installation
            st.markdown("---")
            st.markdown("**CRISPResso2 Installation Check:**")
            
            if st.button("Verify CRISPResso2 Installation"):
                success, message = verify_crispresso_installation(
                    st.session_state.crispresso["env_mode"],
                    st.session_state.crispresso.get("conda_env", "")
                )
                
                if success:
                    st.success(f"CRISPResso2 is installed and available: {message}")
                else:
                    st.error(message)
            
            # Build and display the command
            st.markdown("---")
            st.markdown("**CRISPResso2 Command Preview:**")
            
            cmd = build_crispresso_command(st.session_state.crispresso)
            cmd_str = " ".join(cmd)
            st.code(cmd_str, language="bash")
            
            # Run button
            st.markdown("---")
            run_col1, run_col2 = st.columns([3, 1])
            
            with run_col1:
                st.markdown("**Run CRISPResso2 Analysis:**")
                st.warning("This may take several minutes depending on your input files and parameters.")
            
            with run_col2:
                run_button = st.button("Run CRISPResso2", type="primary")
            
            if run_button:
                # Initialize output containers
                progress_placeholder = st.empty()
                progress_placeholder.info("Starting CRISPResso2...")
                
                stdout_container = st.empty()
                stderr_container = st.empty()
                
                # Initialize subprocess output queues
                stdout_queue = queue.Queue()
                stderr_queue = queue.Queue()
                
                # Run CRISPResso2
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # Start output streaming threads
                t1 = threading.Thread(target=stream_subprocess_output, args=(process, stdout_queue, stderr_queue))
                t1.daemon = True
                t1.start()
                
                # Display output as it comes
                stdout_text = ""
                stderr_text = ""
                
                # Progress bar
                progress_bar = st.progress(0)
                progress_percent = 0
                
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
                            stdout_container.text_area("Standard Output", stdout_text, height=300)
                            
                            # Check for progress indicators
                            if "Processing" in line:
                                progress_placeholder.info(f"Running CRISPResso2: {line.strip()}")
                                # Increment progress bar
                                progress_percent = min(90, progress_percent + 5)  # Max out at 90% until complete
                                progress_bar.progress(progress_percent / 100)
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
                    progress_bar.progress(1.0)  # 100%
                    
                    # Extract output directory from stdout
                    output_dir = extract_output_dir(stdout_text)
                    
                    if output_dir:
                        # Update session state with results path
                        st.session_state.crispresso_results["path"] = output_dir
                        
                        # Show a message to switch to the Results tab
                        st.success(f"CRISPResso2 run completed. Results saved to: {output_dir}")
                        st.info("Switch to the 'Results' tab to view and interpret the results.")
                    else:
                        st.warning("Couldn't determine output directory from CRISPResso2 output.")
                else:
                    progress_placeholder.error(f"CRISPResso2 failed with return code {return_code}")
                    progress_bar.progress(0.0)  # Reset progress bar
    
    with tab3:
        st.subheader("CRISPResso2 Results")
        
        # Check if we have results to display
        if not st.session_state.crispresso_results["path"]:
            st.info("No CRISPResso2 results available. Please run CRISPResso2 first.")
        else:
            results_path = st.session_state.crispresso_results["path"]
            
            # Verify the results directory exists
            if not os.path.isdir(results_path):
                st.error(f"Results directory not found: {results_path}")
            else:
                st.success(f"Displaying results from: {results_path}")
                
                # Find key result files
                alleles_file = os.path.join(results_path, "Alleles_frequency_table.txt")
                quantification_file = os.path.join(results_path, "Quantification_of_editing_frequency.txt")
                frameshift_file = os.path.join(results_path, "Frameshift_analysis.txt")
                
                # Find report HTML file
                report_files = [f for f in os.listdir(results_path) if f.endswith('_report.html')]
                if report_files:
                    report_file = os.path.join(results_path, report_files[0])
                    
                    # Create a link to open the report in a new tab
                    report_rel_path = os.path.relpath(report_file, os.getcwd())
                    st.markdown(f'<a href="{report_rel_path}" target="_blank">View Full CRISPResso2 HTML Report</a>', unsafe_allow_html=True)
                
                # Display tabs for different result views
                result_tabs = st.tabs(["Summary", "Alleles", "Quantification", "Frameshift Analysis", "Images"])
                
                with result_tabs[0]:  # Summary
                    st.subheader("Analysis Summary")
                    
                    # Find and display key metrics
                    info_file = os.path.join(results_path, "CRISPResso_info.json")
                    if os.path.isfile(info_file):
                        with open(info_file, 'r') as f:
                            info = json.load(f)
                            
                            # Extract and display key metrics
                            st.markdown("### Key Metrics")
                            
                            # Create columns for metrics
                            metric_col1, metric_col2 = st.columns(2)
                            
                            with metric_col1:
                                st.metric("Total Reads", info.get("total_reads", "N/A"))
                                st.metric("Reads with Modifications", info.get("n_reads_modified", "N/A"))
                                if "n_reads_modified" in info and "total_reads" in info and info["total_reads"] > 0:
                                    modification_percentage = (info["n_reads_modified"] / info["total_reads"]) * 100
                                    st.metric("Modification Rate", f"{modification_percentage:.2f}%")
                            
                            with metric_col2:
                                st.metric("Reads Aligned", info.get("n_reads_aligned", "N/A"))
                                if "n_reads_aligned" in info and "total_reads" in info and info["total_reads"] > 0:
                                    alignment_rate = (info["n_reads_aligned"] / info["total_reads"]) * 100
                                    st.metric("Alignment Rate", f"{alignment_rate:.2f}%")
                        
                        # Generate LLM summary of the results
                        if "crispresso_summary" not in st.session_state or st.button("Regenerate Summary"):
                            with st.spinner("Generating analysis summary with AI..."):
                                # Prepare data for the LLM
                                summary_data = {
                                    "total_reads": info.get("total_reads", "N/A"),
                                    "reads_aligned": info.get("n_reads_aligned", "N/A"),
                                    "reads_modified": info.get("n_reads_modified", "N/A"),
                                    "modification_percentage": f"{modification_percentage:.2f}%" if "n_reads_modified" in info and "total_reads" in info and info["total_reads"] > 0 else "N/A"
                                }
                                
                                # Get LLM explanation
                                prompt = f"""
                                You are analyzing CRISPResso2 results from a CRISPR gene editing experiment.
                                Based on the following metrics, provide a concise summary (3-5 sentences):
                                
                                Total reads: {summary_data['total_reads']}
                                Aligned reads: {summary_data['reads_aligned']}
                                Modified reads: {summary_data['reads_modified']}
                                Modification rate: {summary_data['modification_percentage']}
                                
                                Focus on explaining what these results indicate about the editing efficiency 
                                and what a researcher should understand from this data.
                                """
                                
                                summary = ask_llm(prompt)
                                st.session_state.crispresso_summary = summary
                        
                        # Display the summary
                        st.markdown("### AI Analysis")
                        st.markdown(st.session_state.crispresso_summary)
                    
                    else:
                        st.warning("CRISPResso_info.json not found. Cannot display summary metrics.")
                
                with result_tabs[1]:  # Alleles
                    st.subheader("Alleles Frequency")
                    
                    if os.path.isfile(alleles_file):
                        # Read alleles frequency table
                        try:
                            alleles_df = pd.read_csv(alleles_file, sep='\t')
                            st.dataframe(alleles_df)
                            
                            # Add download button
                            csv = alleles_df.to_csv().encode('utf-8')
                            st.download_button(
                                "Download Alleles Data as CSV",
                                csv,
                                "crispresso_alleles.csv",
                                "text/csv",
                                key='download-alleles-csv'
                            )
                            
                            # Add LLM explanation
                            if st.button("Explain Alleles Data", key="explain_alleles"):
                                with st.spinner("Analyzing alleles data..."):
                                    # Get top 5 alleles for brevity
                                    top_alleles = alleles_df.head(5).to_dict(orient='records')
                                    explanation = explain_results_with_llm("alleles frequency", str(top_alleles))
                                    st.info(explanation)
                            
                        except Exception as e:
                            st.error(f"Error reading alleles file: {str(e)}")
                    else:
                        st.warning("Alleles frequency table not found.")
                
                with result_tabs[2]:  # Quantification
                    st.subheader("Quantification of Editing Frequency")
                    
                    if os.path.isfile(quantification_file):
                        # Read quantification table
                        try:
                            quant_df = pd.read_csv(quantification_file, sep='\t')
                            st.dataframe(quant_df)
                            
                            # Add download button
                            csv = quant_df.to_csv().encode('utf-8')
                            st.download_button(
                                "Download Quantification Data as CSV",
                                csv,
                                "crispresso_quantification.csv",
                                "text/csv",
                                key='download-quant-csv'
                            )
                        except Exception as e:
                            st.error(f"Error reading quantification file: {str(e)}")
                    else:
                        st.warning("Quantification file not found.")
                
                with result_tabs[3]:  # Frameshift
                    st.subheader("Frameshift Analysis")
                    
                    if os.path.isfile(frameshift_file):
                        # Read frameshift table
                        try:
                            frameshift_df = pd.read_csv(frameshift_file, sep='\t')
                            st.dataframe(frameshift_df)
                            
                            # Add download button
                            csv = frameshift_df.to_csv().encode('utf-8')
                            st.download_button(
                                "Download Frameshift Analysis as CSV",
                                csv,
                                "crispresso_frameshift.csv",
                                "text/csv",
                                key='download-frameshift-csv'
                            )
                        except Exception as e:
                            st.error(f"Error reading frameshift file: {str(e)}")
                    else:
                        st.warning("Frameshift analysis file not found.")
                
                with result_tabs[4]:  # Images
                    st.subheader("Result Plots")
                    
                    # Find plot images
                    plot_files = [f for f in os.listdir(results_path) if f.endswith('.png') or f.endswith('.pdf')]
                    
                    if plot_files:
                        for plot_file in plot_files:
                            if plot_file.endswith('.png'):
                                # Display PNG images
                                st.image(os.path.join(results_path, plot_file), caption=plot_file)
                            else:
                                # For PDFs, just show a download link
                                pdf_path = os.path.join(results_path, plot_file)
                                with open(pdf_path, "rb") as f:
                                    pdf_bytes = f.read()
                                
                                st.download_button(
                                    f"Download {plot_file}",
                                    pdf_bytes,
                                    plot_file,
                                    "application/pdf"
                                )
                    else:
                        st.warning("No plot images found.")
                
                # Add a Q&A section (advanced feature to be implemented)
                st.markdown("---")
                st.subheader("Ask Questions About Your Results")
                
                user_question = st.text_input(
                    "Ask a question about your CRISPResso2 results:",
                    placeholder="E.g., What is the overall editing efficiency? What is the most common mutation?"
                )
                
                if user_question:
                    if "qa_history" not in st.session_state:
                        st.session_state.qa_history = []
                    
                    # Check if it's a new question
                    is_new_question = len(st.session_state.qa_history) == 0 or st.session_state.qa_history[-1][0] != user_question
                    
                    if is_new_question:
                        with st.spinner("Analyzing your question..."):
                            # Prepare context for the LLM from our results data
                            context = ""
                            
                            # Add summary metrics
                            if os.path.isfile(info_file):
                                with open(info_file, 'r') as f:
                                    info = json.load(f)
                                    context += f"CRISPResso2 Summary Metrics:\n"
                                    context += f"Total reads: {info.get('total_reads', 'N/A')}\n"
                                    context += f"Aligned reads: {info.get('n_reads_aligned', 'N/A')}\n"
                                    context += f"Modified reads: {info.get('n_reads_modified', 'N/A')}\n"
                                    
                                    if "n_reads_modified" in info and "total_reads" in info and info["total_reads"] > 0:
                                        modification_percentage = (info["n_reads_modified"] / info["total_reads"]) * 100
                                        context += f"Modification rate: {modification_percentage:.2f}%\n"
                            
                            # Add alleles data (top 3 for brevity)
                            if os.path.isfile(alleles_file):
                                try:
                                    alleles_df = pd.read_csv(alleles_file, sep='\t')
                                    context += "\nTop 3 alleles:\n"
                                    context += str(alleles_df.head(3).to_dict(orient='records'))
                                except:
                                    pass
                            
                            # Create prompt for LLM
                            prompt = f"""
                            You are a helpful AI research assistant analyzing CRISPResso2 results.
                            Based on the following data from a CRISPR gene editing experiment, answer the user's question.
                            
                            CONTEXT:
                            {context}
                            
                            USER QUESTION:
                            {user_question}
                            
                            Answer concisely (2-4 sentences) focusing only on what can be determined from the data.
                            If the data doesn't contain information to answer the question, clearly state that.
                            """
                            
                            answer = ask_llm(prompt)
                            st.session_state.qa_history.append((user_question, answer))
                    
                    # Display the answer
                    st.markdown("### Answer:")
                    st.markdown(st.session_state.qa_history[-1][1])
                    
                    # Show history if there are multiple Q&As
                    if len(st.session_state.qa_history) > 1:
                        with st.expander("Previous Questions & Answers"):
                            for i, (q, a) in enumerate(st.session_state.qa_history[:-1]):
                                st.markdown(f"**Q{i+1}: {q}**")
                                st.markdown(f"A{i+1}: {a}")
                                st.markdown("---")

def create_educational_sidebar():
    """
    Create an educational sidebar with CRISPR terminology and concepts
    and an AI Chat Assistant that guides users through the workflow
    
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
        ed_tabs = st.tabs(["Terminology", "Concepts", "Ask", "AI Chat Assistant"])
        
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
        
        # Tab 4: AI Chat Assistant
        with ed_tabs[3]:
            st.subheader("AI Chat Assistant")
            st.caption("Ask me anything about CRISPR or how to use this app!")

            # Initialize chat history and context in session state if they don't exist
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Initialize workflow context tracking
            if "chat_workflow_context" not in st.session_state:
                st.session_state.chat_workflow_context = {
                    "current_page": "home",  # home, chopchop, crispresso
                    "chopchop_state": "not_started",  # not_started, configuring, running, results_available
                    "crispresso_state": "not_started",  # not_started, configuring, running, results_available
                    "selected_guides": [],  # List of selected guides from CHOPCHOP
                    "gene_of_interest": "",  # Current gene being analyzed
                    "experiment_type": "",  # knockout, knock-in, base_editing
                }
            
            # Track the current page to provide context-aware assistance
            current_url = st.experimental_get_query_params()
            if "page" in current_url:
                page_name = current_url["page"][0]
                if page_name == "CHOPCHOP_Guide_Design":
                    st.session_state.chat_workflow_context["current_page"] = "chopchop"
                elif page_name == "CRISPResso2_Analysis":
                    st.session_state.chat_workflow_context["current_page"] = "crispresso"
            else:
                st.session_state.chat_workflow_context["current_page"] = "home"
                
            # If on the CHOPCHOP page, check if results are available
            if st.session_state.chat_workflow_context["current_page"] == "chopchop":
                if "chopchop_results" in st.session_state and st.session_state.chopchop_results.get("guides"):
                    st.session_state.chat_workflow_context["chopchop_state"] = "results_available"
                    # If gene target is available, update context
                    if "chopchop_run" in st.session_state and st.session_state.chopchop_run.get("target"):
                        st.session_state.chat_workflow_context["gene_of_interest"] = st.session_state.chopchop_run.get("target")
            
            # Update context based on workflow state
            context_info = ""
            if st.session_state.chat_workflow_context["current_page"] == "chopchop":
                if st.session_state.chat_workflow_context["chopchop_state"] == "results_available":
                    context_info = f"""📋 Current Context: 
                    - Viewing CHOPCHOP guide design results
                    - Target gene: {st.session_state.chat_workflow_context["gene_of_interest"]}
                    - Guides available: {len(st.session_state.chopchop_results.get("guides", []))} guides found
                    """
                    # Show a help button for explaining CHOPCHOP results
                    if st.button("❓ Explain CHOPCHOP Results", key="explain_chopchop_btn"):
                        # Add a user question to the chat history
                        explain_query = "Can you explain what the CHOPCHOP results mean and how to interpret the guide scores?"
                        st.session_state.chat_history.append({"role": "user", "content": explain_query})
                        # The assistant will respond in the chat display below
            
            elif st.session_state.chat_workflow_context["current_page"] == "crispresso":
                context_info = "📋 Current Context: CRISPResso2 Analysis workflow"
                
            if context_info:
                st.info(context_info)

            # Display chat messages from history
            for i, message in enumerate(st.session_state.chat_history):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Accept user input
            if prompt := st.chat_input("What can I help you with?"):
                # Add user message to chat history
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                # Display user message in chat message container
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Generate AI response
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    # Prepare context for LLM based on current workflow state
                    system_prompt = """You are a helpful AI assistant for a CRISPR genomics application. 
                    Your main goal is to guide users through the complete workflow:
                    1. CHOPCHOP for guide RNA design
                    2. Experiment design for their selected guides
                    3. CRISPResso2 for analyzing experimental results
                    
                    Provide specific, actionable guidance rather than general information, and help users understand the 
                    scientific meaning of results. Your expertise covers CRISPR biology, experimental design, and data analysis."""
                    
                    # Add workflow context to the system prompt
                    if st.session_state.chat_workflow_context["current_page"] == "chopchop":
                        if st.session_state.chat_workflow_context["chopchop_state"] == "results_available":
                            system_prompt += f"""
                            
                            CURRENT CONTEXT:
                            - User is viewing CHOPCHOP guide design results
                            - Target gene: {st.session_state.chat_workflow_context["gene_of_interest"]}
                            - Number of guides found: {len(st.session_state.chopchop_results.get("guides", []))}
                            
                            GUIDE SCORING INFORMATION:
                            - Efficiency score: Predicted cutting efficiency (higher is better)
                            - Specificity score: Inverse likelihood of off-target effects (higher is better) 
                            - Self-complementarity: Potential for guide RNA to fold back on itself (lower is better)
                            - Position: Location within the target gene (exons are typically preferred for knockouts)
                            
                            Be prepared to explain the guide selection process and help interpret the scores and columns.
                            For the Experiment Design section, explain the differences between knockout, knock-in, and base editing experiments.
                            """
                    
                    # Format chat history for the LLM
                    chat_history_text = "\n\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.chat_history])
                    
                    final_prompt = f"""
{system_prompt}

CONVERSATION HISTORY:
{chat_history_text}

User's latest question: {prompt}
Assistant:
"""                 
                    # Use the ask_llm function to get a response
                    try:
                        ai_response = ask_llm(final_prompt) # Use the ask_llm function we defined earlier
                        
                        # Display the response
                        message_placeholder.markdown(ai_response)
                        full_response = ai_response
                    except Exception as e:
                        full_response = f"Sorry, I encountered an error: {str(e)}"
                        message_placeholder.error(full_response)
                    
                # Add AI response to chat history
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})
    
    return None # query_text from "Ask" tab is no longer the sole return

def main():
    """Main entry point for the Streamlit app"""
    
    # Initialize session state
    init_session_state()
    
    # Set up page config (must be called only once, at the start)
    st.set_page_config(
        page_title="AI Research Assistant for CRISPR",
        page_icon="🧬",
        layout="wide"
    )
    
    # Add custom CSS for styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.8rem;
        color: #0D47A1;
        margin-bottom: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create educational sidebar if available
    create_educational_sidebar()
    
    # Display home page
    display_home_page()

def display_home_page():
    """Display the home page content"""
    
    st.markdown('<div class="main-header">AI Research Assistant for CRISPR Genome Editing</div>', unsafe_allow_html=True)
    
    # Introduction with custom styling
    st.markdown("""
    <div style='padding: 20px; border-radius: 10px; background-color: #f0f8ff; margin-bottom: 30px;'>
    Welcome to the AI Research Assistant for CRISPR Genome Editing. This tool helps you design guides 
    with CHOPCHOP and analyze editing outcomes with CRISPResso2, with AI assistance at every step.
    </div>
    """, unsafe_allow_html=True)
    
    # Main features in columns with enhanced styling
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='padding: 20px; border-radius: 10px; border: 1px solid #e1e4e8;'>
        <h2 style='color: #1E88E5;'>🧬 CHOPCHOP Guide Design</h2>
        <ul style='list-style-type: none; padding-left: 0;'>
        <li>✓ AI-guided configuration of CHOPCHOP</li>
        <li>✓ Intelligent guide RNA selection</li>
        <li>✓ Enhanced visualization and interpretation</li>
        <li>✓ Experimental design recommendations</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        st.page_link('pages/CHOPCHOP_Guide_Design.py', label="Go to CHOPCHOP Guide Design", icon="🧬")
    
    with col2:
        st.markdown("""
        <div style='padding: 20px; border-radius: 10px; border: 1px solid #e1e4e8;'>
        <h2 style='color: #1E88E5;'>📊 CRISPResso2 Analysis</h2>
        <ul style='list-style-type: none; padding-left: 0;'>
        <li>✓ Simplified CRISPResso2 execution</li>
        <li>✓ Advanced results visualization</li>
        <li>✓ AI-powered interpretation of editing outcomes</li>
        <li>✓ Experimental success evaluation</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        st.page_link('pages/CRISPResso2_Analysis.py', label="Go to CRISPResso2 Analysis", icon="📊")
    
    # Educational section with enhanced styling
    st.markdown("""
    <div style='margin-top: 40px;'>
    <h2 style='color: #1E88E5;'>📚 Educational Resources</h2>
    <p>This assistant includes comprehensive educational resources to help you understand CRISPR technology:</p>
    <ul>
    <li>CRISPR terminology and concept explanations</li>
    <li>Interactive visualization interpretations</li>
    <li>Scientific references and literature</li>
    <li>AI-powered Q&A for CRISPR-related questions</li>
    </ul>
    <p>Explore the educational sidebar to learn more about CRISPR genome editing.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Additional information
    with st.expander("About this project"):
        st.markdown("""
        This AI Research Assistant is designed to make CRISPR genome editing more accessible by providing:
        
        1. **Intelligent guidance** through the complex process of guide RNA design and analysis
        2. **Context-aware interpretation** of results based on experimental goals
        3. **Educational resources** to help researchers understand CRISPR technology
        
        The assistant integrates with popular CRISPR tools (CHOPCHOP and CRISPResso2) and enhances them with 
        AI capabilities to improve usability and insight generation.
        """)

if __name__ == "__main__":
    main() 