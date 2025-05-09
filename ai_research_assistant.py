import os
import json
import subprocess # Add subprocess
import sys # Add sys for sys.executable
# import subprocess # Will be needed for other functions
from tools.llm_api import get_llm_chat_response # IMPORT THE NEW FUNCTION
import re # Import regex for parsing guide seqs
from tools.result_parser import CRISPRessoResultParser # Import the parser

# Local imports
sys.path.append(os.path.join(os.path.dirname(__file__), "tools"))
try:
    from tools.conda_manager import CondaManager
except ImportError:
    # Create a stub if conda_manager is not available
    class CondaManager:
        def __init__(self):
            self.is_conda_installed = False
            self.crispresso_env = None
        
        def get_installation_guide(self):
            return "Error: conda_manager.py not found. Cannot provide installation instructions."

# --- Agent State (relevant parts) ---
chopchop_config_path = "tools/chopchop/config_local.json"
# conversation_history = [] # Global history, or pass as param

# --- Global State (Simple Example) ---
# In a more complex app, this might be a class or a context manager
last_chopchop_result = None
last_crispresso_output_dir = None

# --- Placeholder for LLM Interaction ---
def ask_llm_and_get_user_response(instruction_for_llm_to_ask: str, conversation_history: list):
    """
    Instructs the LLM to ask the user a question based on the conversation history,
    prints the LLM's formulated question, gets the user's reply, and updates the history.
    """
    # 1. Prepare context for LLM (history + instruction for what to ask)
    # The 'system' role here tells the LLM its task for this turn.
    llm_prompt_payload = conversation_history + [{"role": "system", "content": instruction_for_llm_to_ask}]
    actual_question_to_user = ""

    try:
        # 2. Get LLM to generate the question text
        actual_question_to_user = get_llm_chat_response(llm_prompt_payload, provider="gemini")
        print(f"AI Research Assistant: {actual_question_to_user}")
    except Exception as e:
        # Fallback: if LLM call fails, use the instruction_for_llm_to_ask directly as the question.
        actual_question_to_user = instruction_for_llm_to_ask
        print(f"AI Research Assistant: {actual_question_to_user}")
        print(f"(LLM Error: Could not formulate question dynamically - {e}. Using direct prompt.)")

    # 3. Get user's reply
    user_reply = input("You: ").strip()

    # 4. Update conversation history with what the LLM actually asked and the user's reply
    conversation_history.append({"role": "assistant", "content": actual_question_to_user})
    conversation_history.append({"role": "user", "content": user_reply})

    return user_reply

# --- CHOPCHOP Configuration Functions ---
def generate_config_local_json(genome_name, two_bit_dir, bowtie_dir, gene_table_dir):
    """
    Generates the tools/chopchop/config_local.json file.
    """
    config_data = {
        "PATH": {
            "TWOBIT_INDEX_DIR": two_bit_dir,
            "BOWTIE_INDEX_DIR": bowtie_dir,
            "GENE_TABLE_INDEX_DIR": gene_table_dir
        }
        # "INFO": { # Optional: store for agent's own reference
        #     "configured_genome_name": genome_name 
        # }
    }
    try:
        # Ensure the tools/chopchop directory exists
        os.makedirs(os.path.dirname(chopchop_config_path), exist_ok=True)
        with open(chopchop_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        return f"Successfully created CHOPCHOP local configuration at '{chopchop_config_path}' for genome '{genome_name}'."
    except IOError as e:
        return f"Error: Could not write CHOPCHOP local configuration. {e}"
    except Exception as e:
        return f"An unexpected error occurred while generating config_local.json: {e}"

def handle_chopchop_config_interaction(conversation_history):
    """
    Guides the user through CHOPCHOP configuration and generates config_local.json.
    Uses the LLM to ask questions conversationally.
    """
    # System/Agent initiates this part of the conversation
    initial_config_message = "I can help you set up the local configuration file for CHOPCHOP (`config_local.json`). This tells CHOPCHOP where to find necessary genome files on your system. First, I'll need a few details."
    print(f"AI Research Assistant: {initial_config_message}")
    conversation_history.append({"role": "assistant", "content": initial_config_message})
    
    # Ask for genome name
    genome_name_instruction = "Ask the user for the common name or assembly ID for the genome they want to configure (e.g., hg38, mm10, sacCer3). Mention this is for their reference and will be part of the CHOPCHOP setup."
    genome_name = ask_llm_and_get_user_response(genome_name_instruction, conversation_history)
    if not genome_name:
        cancel_msg = "Configuration cancelled. A name for the genome setup is helpful."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return cancel_msg

    # Ask for .2bit dir
    two_bit_dir_instruction = f"For the genome '{genome_name}', ask the user to provide the full path to the directory containing its .2bit sequence file(s) (e.g., /path/to/genomes/{genome_name}/sequence). Explain this is for CHOPCHOP's `TWOBIT_INDEX_DIR`."
    two_bit_dir = ask_llm_and_get_user_response(two_bit_dir_instruction, conversation_history)
    if not two_bit_dir:
        cancel_msg = "Configuration cancelled. Path cannot be empty."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return cancel_msg
    if not os.path.isdir(two_bit_dir): 
        error_msg = f"Configuration error: The path provided for .2bit sequences ('{two_bit_dir}') is not a valid directory. Please try configuring again."
        print(f"AI Research Assistant: {error_msg}")
        conversation_history.append({"role": "assistant", "content": error_msg})
        return error_msg

    # Ask for bowtie_dir
    bowtie_dir_instruction = f"Next, for '{genome_name}', ask for the full path to the directory containing the Bowtie index files (e.g., /path/to/genomes/{genome_name}/bowtie_index). Explain this is for `BOWTIE_INDEX_DIR`."
    bowtie_dir = ask_llm_and_get_user_response(bowtie_dir_instruction, conversation_history)
    if not bowtie_dir:
        cancel_msg = "Configuration cancelled. Path cannot be empty."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return cancel_msg
    if not os.path.isdir(bowtie_dir):
        error_msg = f"Configuration error: The path provided for Bowtie indices ('{bowtie_dir}') is not a valid directory. Please try configuring again."
        print(f"AI Research Assistant: {error_msg}")
        conversation_history.append({"role": "assistant", "content": error_msg})
        return error_msg

    # Ask for gene_table_dir
    gene_table_dir_instruction = f"Lastly, for '{genome_name}', ask for the full path to the directory containing gene annotation files (e.g., /path/to/genomes/{genome_name}/annotations). Explain this is for `GENE_TABLE_INDEX_DIR`."
    gene_table_dir = ask_llm_and_get_user_response(gene_table_dir_instruction, conversation_history)
    if not gene_table_dir:
        cancel_msg = "Configuration cancelled. Path cannot be empty."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return cancel_msg
    if not os.path.isdir(gene_table_dir):
        error_msg = f"Configuration error: The path provided for annotations ('{gene_table_dir}') is not a valid directory. Please try configuring again."
        print(f"AI Research Assistant: {error_msg}")
        conversation_history.append({"role": "assistant", "content": error_msg})
        return error_msg
    
    # Confirmation prompt
    confirmation_instruction = (
        f"Please summarize the following details for the user for genome '{genome_name}':\n"
        f"  - .2bit Sequences Directory: '{two_bit_dir}'\n"
        f"  - Bowtie Indices Directory: '{bowtie_dir}'\n"
        f"  - Annotations Directory: '{gene_table_dir}'\n"
        "Then ask them if this is all correct and if they would like to create/update the 'tools/chopchop/config_local.json' file. They should reply yes or no."
    )
    confirmation = ask_llm_and_get_user_response(confirmation_instruction, conversation_history)

    if confirmation.lower() != 'yes':
        final_msg = "Configuration not confirmed. The 'config_local.json' file was not modified."
        print(f"AI Research Assistant: {final_msg}")
        conversation_history.append({"role": "assistant", "content": final_msg})
        return final_msg

    result_message = generate_config_local_json(genome_name, two_bit_dir, bowtie_dir, gene_table_dir)
    print(f"AI Research Assistant: {result_message}")
    conversation_history.append({"role": "assistant", "content": result_message})
    return result_message

# --- Placeholder for other handlers ---
def handle_chopchop_execution_interaction(conversation_history):
    """
    Handles the process of designing guides with CHOPCHOP using LLM-driven conversation.
    Corresponds to Tasks 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5.
    """
    # --- 1. Check Prerequisites --- 
    if not os.path.exists(chopchop_config_path):
        err_msg = f"Error: CHOPCHOP local configuration ('{chopchop_config_path}') not found. Please run 'configure chopchop' first."
        print(f"AI Research Assistant: {err_msg}")
        conversation_history.append({"role": "assistant", "content": err_msg})
        return err_msg

    initial_prompt = "Alright, let's design some guides with CHOPCHOP. I'll need some information about your experiment."
    print(f"AI Research Assistant: {initial_prompt}")
    conversation_history.append({"role": "assistant", "content": initial_prompt})

    # --- 2. Gather Inputs via LLM --- 
    genome_instruction = "Ask the user which configured genome assembly CHOPCHOP should use for guide design (e.g., hg38)."
    genome = ask_llm_and_get_user_response(genome_instruction, conversation_history)
    if not genome:
        cancel_msg = "Operation cancelled. Genome name is required."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return cancel_msg

    target_instruction = "Ask the user for the target gene name, sequence, or genomic coordinates (e.g., TP53, chr1:1000-2000)."
    target = ask_llm_and_get_user_response(target_instruction, conversation_history)
    if not target:
        cancel_msg = "Operation cancelled. Target is required."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return cancel_msg

    enzyme_instruction = "Ask which CRISPR enzyme they are using (e.g., Cas9, Cpf1, Cas13). If they don't specify, confirm if Cas9 is okay as a default."
    enzyme_response = ask_llm_and_get_user_response(enzyme_instruction, conversation_history)
    enzyme = enzyme_response if enzyme_response else "Cas9"
    # If LLM confirms default, it will be in history. If user just pressed enter, enzyme_response is empty.
    if enzyme == "Cas9" and not enzyme_response: # User likely pressed enter for default
        # Add assistant confirmation of default to history for clarity if LLM didn't already do it.
        # This depends on how well the LLM handles the "confirm if Cas9 is okay" part.
        # For robustness, we can add a direct confirmation if an empty response led to default.
        if not any(msg['role'] == 'assistant' and 'Cas9' in msg['content'] for msg in conversation_history[-2:]):
            assistant_confirms_cas9 = f"Okay, we'll use Cas9 as the enzyme."
            print(f"AI Research Assistant: {assistant_confirms_cas9}")
            conversation_history.append({"role": "assistant", "content": assistant_confirms_cas9})
        # Also update the last user message to reflect their implied choice if it was empty
        if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(default Cas9)"
    
    if enzyme not in ['Cas9', 'Cpf1', 'Cas13']:
        # This check might become redundant if the LLM handles validation based on the prompt.
        # However, it's good for fallback.
        invalid_enzyme_msg = f"Invalid enzyme '{enzyme}'. Please try again, choosing from Cas9, Cpf1, or Cas13."
        print(f"AI Research Assistant: {invalid_enzyme_msg}")
        conversation_history.append({"role": "assistant", "content": invalid_enzyme_msg})
        return invalid_enzyme_msg

    guide_len_instruction = "Ask the user for the desired guide RNA length. Mention that the default is 20 if they don't specify."
    guide_len_str_response = ask_llm_and_get_user_response(guide_len_instruction, conversation_history)
    guide_len_str = guide_len_str_response if guide_len_str_response else "20"
    if guide_len_str == "20" and not guide_len_str_response:
        if not any(msg['role'] == 'assistant' and '20' in msg['content'] for msg in conversation_history[-2:]):
            assistant_confirms_len = f"We'll use a guide length of 20."
            print(f"AI Research Assistant: {assistant_confirms_len}")
            conversation_history.append({"role": "assistant", "content": assistant_confirms_len})
        if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(default 20)"
    try:
        guide_length = int(guide_len_str)
    except ValueError:
        error_msg = "Invalid guide length. Please enter a number."
        print(f"AI Research Assistant: {error_msg}")
        conversation_history.append({"role": "assistant", "content": error_msg})
        return error_msg

    pam_instruction = f"Ask the user for the PAM sequence to be used. Suggest NGG for Cas9 or TTTV for Cpf1 as common defaults, depending on the chosen enzyme ({enzyme}). If they don't specify, use NGG."
    pam_response = ask_llm_and_get_user_response(pam_instruction, conversation_history)
    pam = pam_response if pam_response else "NGG"
    if pam == "NGG" and not pam_response:
        if not any(msg['role'] == 'assistant' and 'NGG' in msg['content'] for msg in conversation_history[-2:]):
            assistant_confirms_pam = f"We'll use NGG as the PAM sequence."
            print(f"AI Research Assistant: {assistant_confirms_pam}")
            conversation_history.append({"role": "assistant", "content": assistant_confirms_pam})
        if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(default NGG)"

    safe_target_name = "".join(c if c.isalnum() else '_' for c in target)[:50]
    default_output_dir = os.path.join("chopchop_output", f"{safe_target_name}_{enzyme}")
    output_dir_instruction = f"Suggest saving the results to '{default_output_dir}'. Ask the user if this location is okay, or if they want to specify a different path."
    output_dir_response = ask_llm_and_get_user_response(output_dir_instruction, conversation_history)
    output_dir = default_output_dir
    if output_dir_response.lower() not in ['yes', 'y', '', 'ok', 'okay', 'sure'] and output_dir_response != default_output_dir:
        output_dir = output_dir_response
    os.makedirs(output_dir, exist_ok=True)

    add_args_instruction = "Ask the user if there are any other specific CHOPCHOP command-line arguments they want to add (e.g., '--max_mismatches 3 --scoringMethod Doench2016'). Tell them to just press Enter if none."
    additional_args = ask_llm_and_get_user_response(add_args_instruction, conversation_history)
    if not additional_args and conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(none)"

    # --- 3. Confirmation --- 
    confirm_details_instruction = (
        f"Please summarize the CHOPCHOP run parameters for the user:\n"
        f"  - Genome: {genome}\n"
        f"  - Target: {target}\n"
        f"  - Enzyme: {enzyme}\n"
        f"  - Guide Length: {guide_length}\n"
        f"  - PAM: {pam}\n"
        f"  - Output Directory: {output_dir}\n"
        f"  - Additional Args: '{additional_args if additional_args else '(None)'}'\n"
        "Then ask if they want to proceed with running CHOPCHOP. They should reply yes or no."
    )
    confirmation = ask_llm_and_get_user_response(confirm_details_instruction, conversation_history)

    if confirmation.lower() != 'yes':
        cancel_run_msg = "CHOPCHOP run cancelled."
        print(f"AI Research Assistant: {cancel_run_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_run_msg})
        return cancel_run_msg

    # --- 4. Execute CHOPCHOP --- 
    run_feedback_msg = "Great! Running CHOPCHOP now. This might take a few moments..."
    print(f"AI Research Assistant: {run_feedback_msg}")
    conversation_history.append({"role": "assistant", "content": run_feedback_msg})

    # Get project root dynamically for cwd
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    cmd = [
        sys.executable, # Use the same python interpreter running this script
        os.path.join(project_root, "tools", "chopchop", "chopchop_integration.py"), # Use absolute path
        "--genome", genome,
        "--target", target,
        "--enzyme", enzyme,
        "--guide_length", str(guide_length),
        "--pam", pam,
        "--output", output_dir
    ]
    if additional_args:
        # Basic splitting, might need more robust parsing for complex args
        cmd.extend(additional_args.split()) 

    try:
        # Use cwd=project_root to ensure relative paths in chopchop_integration.py work
        process_result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=project_root)
        
        # Check return code AFTER running
        if process_result.returncode != 0:
            # Raise the error to be caught by the CalledProcessError handler
             raise subprocess.CalledProcessError(process_result.returncode, cmd, output=process_result.stdout, stderr=process_result.stderr)

        # --- 5. Process Success Output --- 
        stdout_lines = process_result.stdout.splitlines()
        result_json_path = None
        for line in stdout_lines:
            # Look for the exact line printed by chopchop_integration.py
            if line.startswith("Results saved as JSON to"):
                result_json_path = line.split("Results saved as JSON to")[-1].strip()
                break
        
        if result_json_path and os.path.exists(result_json_path):
            # --- Task 1.2.5 Implementation START --- 
            try:
                with open(result_json_path, 'r') as f:
                    top_guides_data = json.load(f)
                
                summary_for_llm = "Top CHOPCHOP Guide Recommendations:\n\n"
                for i, guide in enumerate(top_guides_data[:3]): # Show top 3
                    summary_for_llm += f"Guide {i+1}:\n"
                    summary_for_llm += f"  Sequence: {guide.get('Target sequence', 'N/A')}\n"
                    summary_for_llm += f"  Location: {guide.get('Location', 'N/A')} (Strand: {guide.get('Strand', 'N/A')})\n"
                    summary_for_llm += f"  Efficiency (Doench2016): {guide.get('Efficiency', 'N/A')}\n"
                    summary_for_llm += f"  Specificity Score: {guide.get('Specificity', 'N/A')}\n"
                    summary_for_llm += f"  Off-targets (MM0/MM1/MM2/MM3): {guide.get('MM0', 'N/A')}/{guide.get('MM1', 'N/A')}/{guide.get('MM2', 'N/A')}/{guide.get('MM3', 'N/A')}\n\n"
                
                presentation_instruction_for_llm = (
                    f"The CHOPCHOP analysis for target '{target}' is complete. Here is a summary of the top recommended guides:\n\n"
                    f"{summary_for_llm}\n"
                    "Please present these results clearly to the user. Explain the key metrics (like Efficiency score, Specificity score, and Off-targets MM0/MM1/MM2/MM3) in simple terms for a novice. Briefly advise on how to choose between guides (balancing efficiency and specificity/off-targets). Finally, mention potential next steps like ordering the guide sequence and designing PCR primers for analysis."
                )
                
                llm_presentation = get_llm_chat_response(
                    conversation_history + [{'role': 'system', 'content': presentation_instruction_for_llm}],
                    provider="gemini"
                )
                print(f"AI Research Assistant: {llm_presentation}")
                conversation_history.append({"role": "assistant", "content": llm_presentation})
                last_chopchop_result = { "result": llm_presentation, "success": True } # Store result
                return llm_presentation # Return the LLM's presentation as the final output of this handler

            except json.JSONDecodeError:
                err_msg = f"CHOPCHOP finished, but the result file '{result_json_path}' is not valid JSON."
                print(f"AI Research Assistant: {err_msg}")
                conversation_history.append({"role": "assistant", "content": err_msg})
                last_chopchop_result = { "error": err_msg, "success": False } # Store error state
                return err_msg
            except Exception as e:
                err_msg = f"CHOPCHOP finished, but an error occurred while processing results: {e}"
                print(f"AI Research Assistant: {err_msg}")
                conversation_history.append({"role": "assistant", "content": err_msg})
                last_chopchop_result = { "error": err_msg, "success": False } # Store error state
                return err_msg
            # --- Task 1.2.5 Implementation END --- 
        else:
            err_msg = f"CHOPCHOP command finished (exit code 0), but couldn't find the expected result JSON file message or path ('{result_json_path}'). Output directory: {output_dir}.\nSTDOUT:\n{process_result.stdout}\nSTDERR:\n{process_result.stderr}"
            print(f"AI Research Assistant: {err_msg}")
            conversation_history.append({"role": "assistant", "content": err_msg})
            last_chopchop_result = { "error": err_msg, "success": False } # Store error state
            return err_msg

    except subprocess.CalledProcessError as e:
        err_msg_detail = f"Error running CHOPCHOP (Exit Code {e.returncode}):\nCommand: {' '.join(e.cmd)}\nSTDERR:\n{e.stderr}\nSTDOUT:\n{e.output}"
        print(err_msg_detail) 
        
        llm_instruction_for_error = (
            f"The CHOPCHOP command failed with exit code {e.returncode}. "
            f"Command run was: `{' '.join(e.cmd)}`\n"
            f"Here is the error output (stderr):\n```\n{e.stderr}\n```\n"
            f"Here is the standard output (stdout), if any:\n```\n{e.output}\n```\n"
            "Please analyze this error for a novice user. Explain the likely cause (e.g., incorrect target format, missing genome files in configured paths, invalid parameters like PAM sequence, memory issues). Suggest specific troubleshooting steps they could take, like double-checking the target input, verifying file paths in config_local.json, or checking the specific parameter mentioned in the error."
        )
        llm_error_explanation = get_llm_chat_response(
            conversation_history + [{'role': 'system', 'content': llm_instruction_for_error}],
            provider="gemini"
        )
        final_error_message = f"CHOPCHOP run failed. Here is an explanation:\n{llm_error_explanation}"
        print(f"AI Research Assistant: {final_error_message}")
        conversation_history.append({"role": "assistant", "content": final_error_message})
        last_chopchop_result = { "error": final_error_message, "success": False } # Store error state
        return final_error_message
        
    except FileNotFoundError:
        err_msg = "Error: Could not find the CHOPCHOP script '{os.path.join(project_root, \"tools\", \"chopchop\", \"chopchop_integration.py\")}'. Please check the installation and that the file exists at this location."
        print(f"AI Research Assistant: {err_msg}")
        conversation_history.append({"role": "assistant", "content": err_msg})
        last_chopchop_result = { "error": err_msg, "success": False } # Store error state
        return err_msg
    except Exception as e:
        err_msg = f"An unexpected error occurred while trying to run CHOPCHOP: {e}"
        print(f"Unexpected Error Details: {e}")
        print(f"AI Research Assistant: {err_msg}")
        conversation_history.append({"role": "assistant", "content": err_msg})
        last_chopchop_result = { "error": err_msg, "success": False } # Store error state
        return err_msg

def handle_crispresso_execution_interaction(conversation_history):
    """
    Guides the user through setting up and running a CRISPResso2 analysis.
    Corresponds to Tasks 2.1.1, 2.1.2, 2.1.3.
    """
    # --- Check for CRISPResso2 availability ---
    conda_manager = CondaManager()
    if not conda_manager.is_conda_installed:
        # Conda is not installed
        install_guide = conda_manager.get_installation_guide()
        message = (
            "I need to check your CRISPResso2 installation before we can proceed.\n\n"
            "It appears that Conda is not installed on your system. CRISPResso2 requires Conda "
            "to run properly.\n\n"
            f"Installation Guide:\n{install_guide}\n\n"
            "Once you've installed Conda and CRISPResso2, please come back and we can continue."
        )
        print(f"AI Research Assistant: {message}")
        conversation_history.append({"role": "assistant", "content": message})
        return "conda_not_installed"
    
    if not conda_manager.crispresso_env:
        # CRISPResso2 is not installed
        install_guide = conda_manager.get_installation_guide()
        
        # Ask user if they want to install it
        install_prompt = (
            "I need to check your CRISPResso2 installation before we can proceed.\n\n"
            "It appears that CRISPResso2 is not installed in any of your Conda environments.\n\n"
            f"Installation Guide:\n{install_guide}\n\n"
            "Would you like me to help you install CRISPResso2 now? (yes/no)"
        )
        
        user_response = ask_llm_and_get_user_response(install_prompt, conversation_history)
        
        if user_response.lower() in ["yes", "y", "yeah", "sure", "ok", "okay"]:
            # Create a CRISPResso2 environment
            print("AI Research Assistant: Creating a new Conda environment with CRISPResso2...")
            success = conda_manager.create_crispresso_environment()
            
            if success:
                message = (
                    "Great! I've created a new Conda environment with CRISPResso2 installed. "
                    f"You can activate it using: conda activate {conda_manager.crispresso_env}\n\n"
                    "Now we can proceed with setting up your CRISPResso2 analysis."
                )
                print(f"AI Research Assistant: {message}")
                conversation_history.append({"role": "assistant", "content": message})
            else:
                message = (
                    "I encountered an error while trying to create a CRISPResso2 environment. "
                    "Please try installing CRISPResso2 manually using the instructions provided earlier, "
                    "then come back to continue."
                )
                print(f"AI Research Assistant: {message}")
                conversation_history.append({"role": "assistant", "content": message})
                return "crispresso_install_failed"
        else:
            message = (
                "I understand. Please install CRISPResso2 manually using the instructions provided earlier, "
                "then come back to continue."
            )
            print(f"AI Research Assistant: {message}")
            conversation_history.append({"role": "assistant", "content": message})
            return "user_declined_install"
    
    # --- CRISPResso2 is available, proceed with analysis setup ---
    initial_prompt = (
        f"Great! I've detected CRISPResso2 in the '{conda_manager.crispresso_env}' "
        f"Conda environment. Let's set up your analysis. I'll need details about your "
        f"sequencing reads and experimental setup."
    )
    print(f"AI Research Assistant: {initial_prompt}")
    conversation_history.append({"role": "assistant", "content": initial_prompt})

    # --- Gather Core Inputs (Task 2.1.1) ---
    fastq_r1_instruction = "Please provide the full path to your FASTQ R1 file (forward reads)."
    fastq_r1 = ask_llm_and_get_user_response(fastq_r1_instruction, conversation_history)
    if not fastq_r1:
        cancel_msg = "CRISPResso2 analysis cancelled. FASTQ R1 file path is required."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return "cancelled"

    # Check if R2 file exists
    fastq_r2 = None
    paired_end_instruction = "Are you working with paired-end reads? (yes/no)"
    paired_end_response = ask_llm_and_get_user_response(paired_end_instruction, conversation_history)
    
    if paired_end_response.lower() in ["yes", "y", "yeah", "true", "pair", "paired"]:
        fastq_r2_instruction = "Please provide the full path to your FASTQ R2 file (reverse reads)."
        fastq_r2 = ask_llm_and_get_user_response(fastq_r2_instruction, conversation_history)

    # Amplicon sequence
    amplicon_instruction = (
        "Please provide your amplicon sequence (the reference sequence surrounding your target site). "
        "This should be the full amplicon used in your PCR, including regions outside the expected cut site."
    )
    amplicon_seq = ask_llm_and_get_user_response(amplicon_instruction, conversation_history)
    if not amplicon_seq:
        cancel_msg = "CRISPResso2 analysis cancelled. Amplicon sequence is required."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return "cancelled"

    # Guide RNA sequence
    guide_seq_instruction = "Please provide the guide RNA sequence (sgRNA sequence) used for targeting. "
    guide_seq = None
    
    # Check for previous CHOPCHOP results (Task 2.1.2.6)
    global last_chopchop_result
    if last_chopchop_result and last_chopchop_result.get("success"): 
        # Attempt to parse guides from the stored result string
        try:
            # Simple regex to find sequences after "Sequence:"
            # This relies on the formatting used in the CHOPCHOP result summary
            chopchop_guides = re.findall(r"Sequence:\s*([ATCGU]+)", last_chopchop_result["result"], re.IGNORECASE)
            if chopchop_guides:
                guide_options_text = "I found these guides from your last CHOPCHOP run:\n"
                for i, g_seq in enumerate(chopchop_guides):
                    guide_options_text += f"{i+1}. {g_seq}\n"
                guide_options_text += "Please enter the number of the guide you want to use, or enter the sequence directly if it's not listed."
                guide_seq_instruction = guide_options_text # Overwrite the default instruction
                
                guide_seq_response = ask_llm_and_get_user_response(guide_seq_instruction, conversation_history)
                
                # Check if user entered a number corresponding to a guide
                try:
                    choice_num = int(guide_seq_response)
                    if 1 <= choice_num <= len(chopchop_guides):
                        guide_seq = chopchop_guides[choice_num - 1]
                        guide_chosen_msg = f"Okay, using guide {choice_num}: {guide_seq}"
                        print(f"AI Research Assistant: {guide_chosen_msg}")
                        # Update history - user response was number, assistant confirms sequence
                        conversation_history.append({"role": "assistant", "content": guide_chosen_msg})
                    else:
                         # User entered a number out of range, treat as direct sequence entry
                         guide_seq = guide_seq_response 
                except ValueError:
                    # User entered text, treat as direct sequence entry
                    guide_seq = guide_seq_response
            else:
                 # Found result but couldn't parse guides, ask normally
                 guide_seq_response = ask_llm_and_get_user_response(guide_seq_instruction + "(Could not automatically extract guides from previous run.)", conversation_history)
                 guide_seq = guide_seq_response
        except Exception as parse_error:
            # Error during parsing, ask normally
            print(f"(Debug: Error parsing CHOPCHOP results: {parse_error})")
            guide_seq_response = ask_llm_and_get_user_response(guide_seq_instruction + "(Error parsing previous results.)", conversation_history)
            guide_seq = guide_seq_response
    
    # If guide wasn't set via CHOPCHOP context, ask the standard way
    if guide_seq is None:
        guide_seq_response = ask_llm_and_get_user_response(guide_seq_instruction, conversation_history)
        guide_seq = guide_seq_response 
    
    if not guide_seq:
        cancel_msg = "CRISPResso2 analysis cancelled. Guide RNA sequence is required."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return "cancelled"

    # --- Advanced Parameters Selection (Task 2.1.2) ---
    advanced_params = {}
    
    advanced_params_instruction = "Would you like to specify additional parameters for CRISPResso2? (yes/no)"
    advanced_response = ask_llm_and_get_user_response(advanced_params_instruction, conversation_history)
    
    if advanced_response.lower() in ["yes", "y", "yeah", "true"]:
        # Experiment name
        exp_name_instruction = (
            "What would you like to name your experiment? "
            "This will be used to create the output directory."
        )
        exp_name = ask_llm_and_get_user_response(exp_name_instruction, conversation_history)
        if exp_name:
            advanced_params["name"] = exp_name
        
        # Quantification window
        quant_window_instruction = (
            "Would you like to specify a custom quantification window? "
            "This defines the region around the cut site where mutations will be quantified. "
            "Default is ±1 bp around the Cas9 cut site. (yes/no)"
        )
        quant_window_response = ask_llm_and_get_user_response(quant_window_instruction, conversation_history)
        
        if quant_window_response.lower() in ["yes", "y", "yeah", "true"]:
            quant_window_size_instruction = (
                "How many base pairs on each side of the cut site should be included in the quantification window? "
                "Please enter a number (e.g., 5 for ±5 bp)."
            )
            quant_window_size = ask_llm_and_get_user_response(quant_window_size_instruction, conversation_history)
            try:
                quant_window_size = int(quant_window_size)
                advanced_params["quantification_window_size"] = quant_window_size
            except ValueError:
                print(f"AI Research Assistant: Invalid quantification window size. Using default value.")
    
    # --- Gather Key CRISPResso2 Parameters (Task 2.1.2) --- 
    
    # Conda Environment Handling (Tasks 2.1.2.1, 2.1.2.2, 2.1.2.3)
    conda_env_name = None
    crispresso_executable = "CRISPResso"
    env_instruction = ("Is CRISPResso2 directly callable in your current environment (i.e., in your system PATH), "
                       "or do you need to run it from a specific Conda environment? "
                       "If it's in PATH, just say 'path'. If Conda, say 'conda' and then I'll ask for the environment name.")
    env_type_response = ask_llm_and_get_user_response(env_instruction, conversation_history)

    if 'conda' in env_type_response.lower():
        conda_name_instruction = "What is the name of the Conda environment where CRISPResso2 is installed?"
        conda_env_name = ask_llm_and_get_user_response(conda_name_instruction, conversation_history)
        if not conda_env_name:
            # Fallback or error if no Conda name provided after saying 'conda'
            # For now, we'll try to proceed assuming it might be in PATH if name is empty, but LLM should ideally prevent this
            empty_conda_name_msg = "No Conda environment name was provided. I will try to run CRISPResso2 directly. If this fails, please ensure the environment name is correct or CRISPResso2 is in your PATH."
            print(f"AI Research Assistant: {empty_conda_name_msg}")
            conversation_history.append({"role": "assistant", "content": empty_conda_name_msg})
            conda_env_name = None # Explicitly set to None
        else:
            conda_set_msg = f"Okay, I will attempt to run CRISPResso2 using the Conda environment: '{conda_env_name}'."
            print(f"AI Research Assistant: {conda_set_msg}")
            conversation_history.append({"role": "assistant", "content": conda_set_msg})
    elif 'path' not in env_type_response.lower():
        # If user didn't say 'conda' or 'path', LLM should clarify.
        # For now, assume path if not explicitly conda and log it.
        path_default_msg = "Assuming CRISPResso2 is in the PATH as Conda was not specified."
        print(f"AI Research Assistant: {path_default_msg}")
        conversation_history.append({"role": "assistant", "content": path_default_msg})
    else: # User explicitly said 'path' or LLM guided them to confirm it
        path_confirmed_msg = "Okay, I'll try to run CRISPResso2 directly from your system PATH."
        print(f"AI Research Assistant: {path_confirmed_msg}")
        conversation_history.append({"role": "assistant", "content": path_confirmed_msg})

    # --- Verify CRISPResso Installation --- 
    verify_cmd_parts = []
    if conda_env_name:
        verify_cmd_parts = ["conda", "run", "-n", conda_env_name, crispresso_executable, "--version"]
    else:
        verify_cmd_parts = [crispresso_executable, "--version"]
        
    print("AI Research Assistant: Verifying CRISPResso2 installation...")
    try:
        verify_process = subprocess.run(verify_cmd_parts, capture_output=True, text=True, check=True, timeout=15)
        # Simple check if output contains 'CRISPResso' - could be more specific
        if "crispresso" in verify_process.stdout.lower():
            version_info = verify_process.stdout.strip()
            verify_success_msg = f"Successfully verified CRISPResso2 installation ({version_info}). Proceeding with parameter input."
            print(f"AI Research Assistant: {verify_success_msg}")
            conversation_history.append({"role": "assistant", "content": verify_success_msg})
        else:
            raise ValueError(f"Command ran but output doesn't confirm CRISPResso: {verify_process.stdout}")
            
    except subprocess.CalledProcessError as e:
        verify_fail_msg = (
            f"Error: Failed to verify CRISPResso2 using the command: `{' '.join(verify_cmd_parts)}`\n"
            f"Stderr: {e.stderr}\nStdout: {e.output}\n"
            "Please ensure CRISPResso2 is installed correctly in the specified environment/path and try again."
        )
        print(f"AI Research Assistant: {verify_fail_msg}")
        conversation_history.append({"role": "assistant", "content": verify_fail_msg})
        return "CRISPResso verification failed."
    except FileNotFoundError:
        verify_fnf_msg = (
            f"Error: Command `{'conda' if conda_env_name else crispresso_executable}` not found. "
            f"Cannot verify CRISPResso2. Please check your Conda installation or system PATH."
        )
        print(f"AI Research Assistant: {verify_fnf_msg}")
        conversation_history.append({"role": "assistant", "content": verify_fnf_msg})
        return "CRISPResso verification failed."
    except subprocess.TimeoutExpired:
        verify_timeout_msg = (
            f"Error: Verification command timed out: `{' '.join(verify_cmd_parts)}`\n"
            "This might indicate an issue with the environment or CRISPResso installation."
        )
        print(f"AI Research Assistant: {verify_timeout_msg}")
        conversation_history.append({"role": "assistant", "content": verify_timeout_msg})
        return "CRISPResso verification failed."
    except Exception as e:
        verify_error_msg = f"An unexpected error occurred during CRISPResso2 verification: {e}"
        print(f"AI Research Assistant: {verify_error_msg}")
        conversation_history.append({"role": "assistant", "content": verify_error_msg})
        return "CRISPResso verification failed."

    # --- Initialize a dictionary to store optional CRISPResso parameters --- 
    optional_crispresso_params = {}

    # Experiment Name (if not already set, or to confirm/change)
    # We have experiment_name from earlier, let's use that as default unless user wants to change
    exp_name_instruction = f"The current experiment name is '{experiment_name}'. Would you like to change it? If not, just press Enter or say no."
    change_exp_name_response = ask_llm_and_get_user_response(exp_name_instruction, conversation_history)
    if change_exp_name_response.lower() in ['yes', 'y']:
        new_exp_name_instruction = "What would you like to set as the new experiment name?"
        new_exp_name = ask_llm_and_get_user_response(new_exp_name_instruction, conversation_history)
        if new_exp_name:
            experiment_name = new_exp_name # Update the main experiment_name variable
    optional_crispresso_params['-n'] = experiment_name # Ensure it's in the dict for command building


    # Quantification Window Size
    quant_window_size = advanced_params.get("quantification_window_size", 1)
    optional_crispresso_params['--quantification_window_size'] = quant_window_size

    # Plot Window Size
    plot_window_instruction = ("CRISPResso2 can generate plots showing a window around the guide. "
                               "The default plot window is often based on the quantification window. "
                               "Would you like to specify a custom plot window size (integer value)? If not, say no or press Enter.")
    plot_window_response = ask_llm_and_get_user_response(plot_window_instruction, conversation_history)
    if plot_window_response.lower() not in ['no', 'n', '']:
        try:
            plot_size = int(plot_window_response)
            optional_crispresso_params['--plot_window_size'] = str(plot_size)
            plot_set_msg = f"Okay, plot window size set to {plot_size} bp."
            print(f"AI Research Assistant: {plot_set_msg}")
            conversation_history.append({"role": "assistant", "content": plot_set_msg})
        except ValueError:
            plot_error_msg = "Invalid plot window size. It must be an integer. Using default."
            print(f"AI Research Assistant: {plot_error_msg}")
            conversation_history.append({"role": "assistant", "content": plot_error_msg})
    elif not plot_window_response: # User pressed enter for default
        if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(default plot window)"

    # Min Average Read Quality
    min_qual_instruction = ("You can filter reads based on minimum average quality (Phred score). "
                            "A common default is 0 (no filtering) or around 20-30. "
                            "Would you like to set a minimum average read quality? Enter an integer or say no/press Enter for default (0)." )
    min_qual_response = ask_llm_and_get_user_response(min_qual_instruction, conversation_history)
    if min_qual_response.lower() not in ['no', 'n', '']:
        try:
            qual_score = int(min_qual_response)
            optional_crispresso_params['--min_average_read_quality'] = str(qual_score)
            qual_set_msg = f"Okay, minimum average read quality set to {qual_score}."
            print(f"AI Research Assistant: {qual_set_msg}")
            conversation_history.append({"role": "assistant", "content": qual_set_msg})
        except ValueError:
            qual_error_msg = "Invalid quality score. It must be an integer. No filter will be applied."
            print(f"AI Research Assistant: {qual_error_msg}")
            conversation_history.append({"role": "assistant", "content": qual_error_msg})
    elif not min_qual_response:
        if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(default min quality)"

    # Ignore Substitutions at Ends
    ignore_subs_instruction = ("Sometimes, substitutions at the very ends of reads are due to sequencing errors. "
                               "CRISPResso2 can ignore a specified number of bases at each end for substitution calling. "
                               "Would you like to set this? Enter an integer (e.g., 3 to ignore 3bp from each end) or say no/press Enter to not ignore.")
    ignore_subs_response = ask_llm_and_get_user_response(ignore_subs_instruction, conversation_history)
    if ignore_subs_response.lower() not in ['no', 'n', '']:
        try:
            bp_to_ignore = int(ignore_subs_response)
            optional_crispresso_params['--ignore_substitutions_at_ends'] = str(bp_to_ignore)
            ignore_set_msg = f"Okay, will ignore substitutions at {bp_to_ignore}bp from each read end."
            print(f"AI Research Assistant: {ignore_set_msg}")
            conversation_history.append({"role": "assistant", "content": ignore_set_msg})
        except ValueError:
            ignore_error_msg = "Invalid number of base pairs. It must be an integer. This option will not be set."
            print(f"AI Research Assistant: {ignore_error_msg}")
            conversation_history.append({"role": "assistant", "content": ignore_error_msg})
    elif not ignore_subs_response:
         if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
            conversation_history[-1]['content'] = "(default ignore substitutions)"

    # Ask about Experiment Type (NHEJ, HDR, Base Editing)
    experiment_type = "NHEJ" # Default
    exp_type_instruction = ("What type of CRISPR experiment are you analyzing? "
                          "(e.g., NHEJ for standard knockouts, HDR for homology-directed repair, Base Editing for specific base changes). "
                          "If unsure or just doing standard analysis, NHEJ is the default - just press Enter.")
    exp_type_response = ask_llm_and_get_user_response(exp_type_instruction, conversation_history)

    if 'hdr' in exp_type_response.lower():
        experiment_type = "HDR"
        hdr_msg = "Okay, analyzing as an HDR experiment."
        print(f"AI Research Assistant: {hdr_msg}")
        conversation_history.append({"role": "assistant", "content": hdr_msg})
        # Gather HDR-specific parameters
        hdr_seq_instruction = ("For HDR analysis, please provide the expected amplicon sequence *after* successful HDR.")
        expected_hdr_seq = ask_llm_and_get_user_response(hdr_seq_instruction, conversation_history)
        if expected_hdr_seq:
            optional_crispresso_params['--expected_hdr_amplicon_seq'] = expected_hdr_seq
            # Could add --hdr_bp_distance here too if needed
        else:
            hdr_warn_msg = "Warning: No expected HDR sequence provided. HDR quantification might be limited."
            print(f"AI Research Assistant: {hdr_warn_msg}")
            conversation_history.append({"role": "assistant", "content": hdr_warn_msg})
            
    elif 'base' in exp_type_response.lower() and 'edit' in exp_type_response.lower():
        experiment_type = "BaseEditing"
        be_msg = "Okay, analyzing as a Base Editing experiment."
        print(f"AI Research Assistant: {be_msg}")
        conversation_history.append({"role": "assistant", "content": be_msg})
        optional_crispresso_params['--base_editor_output'] = True # Enable base editing module
        
        # Gather Base Editing-specific parameters
        conv_from_instruction = "Which nucleotide is the base editor supposed to convert FROM? (e.g., C)"
        conv_from = ask_llm_and_get_user_response(conv_from_instruction, conversation_history)
        if conv_from and conv_from.upper() in 'ATCG':
            optional_crispresso_params['--conversion_nuc_from'] = conv_from.upper()
        else:
            be_warn_msg = "Warning: Invalid 'FROM' nucleotide for base editing. Analysis may be affected."
            print(f"AI Research Assistant: {be_warn_msg}")
            conversation_history.append({"role": "assistant", "content": be_warn_msg})

        conv_to_instruction = f"Which nucleotide should {conv_from.upper() if conv_from else 'the original base'} be converted TO? (e.g., T)"
        conv_to = ask_llm_and_get_user_response(conv_to_instruction, conversation_history)
        if conv_to and conv_to.upper() in 'ATCG':
            optional_crispresso_params['--conversion_nuc_to'] = conv_to.upper()
        else:
            be_warn_msg_2 = "Warning: Invalid 'TO' nucleotide for base editing. Analysis may be affected."
            print(f"AI Research Assistant: {be_warn_msg_2}")
            conversation_history.append({"role": "assistant", "content": be_warn_msg_2})
            
    else: # Default to NHEJ
        if not exp_type_response:
            if conversation_history[-1]['role'] == 'user' and not conversation_history[-1]['content']:
                conversation_history[-1]['content'] = "(default NHEJ analysis)"
        nhej_msg = "Okay, proceeding with standard NHEJ analysis."
        print(f"AI Research Assistant: {nhej_msg}")
        # Only append if LLM didn't already confirm
        if not any(msg['role'] == 'assistant' and 'NHEJ' in msg['content'] for msg in conversation_history[-2:]):
             conversation_history.append({"role": "assistant", "content": nhej_msg})

    # --- Construct and Execute CRISPResso Command (Task 2.1.3) --- 
    
    # base_crispresso_cmd = "CRISPResso" # Defined earlier
    if conda_env_name:
        crispresso_cmd_parts = ["conda", "run", "-n", conda_env_name, crispresso_executable]
    else:
        crispresso_cmd_parts = [crispresso_executable]

    # Add core required parameters
    crispresso_cmd_parts.extend([
        "-r1", fastq_r1,
        "-a", amplicon_seq,
        "-g", guide_seq,
        # '-n' and '--quantification_window_size' are now in optional_crispresso_params
    ])
    if fastq_r2:
        crispresso_cmd_parts.extend(["-r2", fastq_r2])

    # Add all collected optional parameters
    for param_key, param_value in optional_crispresso_params.items():
        # Handle boolean flags like --base_editor_output which don't take a value
        if isinstance(param_value, bool) and param_value:
            crispresso_cmd_parts.append(param_key)
        elif param_value is not None: # Add other params with their values
            crispresso_cmd_parts.extend([param_key, str(param_value)])

    # Allow for other common options via LLM in the future
    # Display command preview
    command_str = " ".join(crispresso_cmd_parts)
    command_preview = f"Based on your inputs, I'll run the following CRISPResso2 command:\n\n{command_str}\n\nWould you like to proceed? (yes/no)"
    proceed_response = ask_llm_and_get_user_response(command_preview, conversation_history)
    
    if proceed_response.lower() not in ["yes", "y", "yeah", "true", "proceed"]:
        cancel_msg = "CRISPResso2 analysis cancelled per your request."
        print(f"AI Research Assistant: {cancel_msg}")
        conversation_history.append({"role": "assistant", "content": cancel_msg})
        return "cancelled"
    
    # --- Execute Command ---
    print(f"AI Research Assistant: Running CRISPResso2 analysis. This may take some time...")
    conversation_history.append({"role": "assistant", "content": "Running CRISPResso2 analysis. This may take some time..."})
    
    success, stdout, stderr = conda_manager.run_crispresso_command(crispresso_cmd_parts)
    
    if success:
        # Store the output directory path for potential immediate interpretation
        global last_crispresso_output_dir
        last_crispresso_output_dir = output_dir

        success_msg_instruction = (
            f"CRISPResso2 analysis for '{experiment_name}' completed successfully! "
            f"The results are saved in the directory: {output_dir}.\n\n"
            "Would you like me to summarize the key findings? (yes/no)"
        )
        print(f"AI Research Assistant: {success_msg_instruction}")
        conversation_history.append({"role": "assistant", "content": success_msg_instruction})
        
        # TODO: Implement result parsing and summarization (Task 2.2)
        # This will be implemented in the result_parser.py module
        
        return "success"
    else:
        error_msg = (
            f"Error running CRISPResso2: {stderr}\n\n"
            "Would you like me to help troubleshoot this error? (yes/no)"
        )
        print(f"AI Research Assistant: {error_msg}")
        conversation_history.append({"role": "assistant", "content": error_msg})
        
        # TODO: Implement error handling and troubleshooting assistance (Task 3.1)
        
        return "error"

def handle_crispresso_results_interaction(conversation_history):
    """
    Loads CRISPResso2 results, presents a summary, and answers questions using the parser.
    Corresponds to Tasks 2.2.1, 2.2.3, 2.2.4 (Advanced Q&A).
    """
    global last_crispresso_output_dir
    output_dir_to_parse = last_crispresso_output_dir

    if not output_dir_to_parse or not os.path.isdir(output_dir_to_parse):
        ask_dir_instruction = "Which CRISPResso2 output directory would you like me to interpret? Please provide the full path."
        output_dir_to_parse = ask_llm_and_get_user_response(ask_dir_instruction, conversation_history)
        if not output_dir_to_parse:
            cancel_msg = "Result interpretation cancelled. No directory specified."
            print(f"AI Research Assistant: {cancel_msg}")
            conversation_history.append({"role": "assistant", "content": cancel_msg})
            return cancel_msg
        if not os.path.isdir(output_dir_to_parse):
            error_msg = f"Error: The specified directory '{output_dir_to_parse}' does not exist or is not a directory. Please try again."
            print(f"AI Research Assistant: {error_msg}")
            conversation_history.append({"role": "assistant", "content": error_msg})
            return error_msg
    else:
        confirm_dir_msg = f"Interpreting results from the last run: '{output_dir_to_parse}'"
        print(f"AI Research Assistant: {confirm_dir_msg}")
        conversation_history.append({"role": "assistant", "content": confirm_dir_msg})

    # Task 2.2.1: Instantiate the parser
    parser = CRISPRessoResultParser(output_dir_to_parse)

    if not parser.is_valid():
        error_msg = f"Could not load or parse results from '{output_dir_to_parse}'. Error: {parser.error}"
        print(f"AI Research Assistant: {error_msg}")
        conversation_history.append({"role": "assistant", "content": error_msg})
        # Reset last_crispresso_output_dir if it was invalid
        if output_dir_to_parse == last_crispresso_output_dir:
            last_crispresso_output_dir = None
        return error_msg

    # Task 2.2.3: Generate and present summary using LLM
    results_summary_text = parser.generate_summary()
    
    summary_presentation_instruction = (
        "Here is a summary of the CRISPResso2 analysis results:\n\n"
        f"{results_summary_text}\n\n"
        "Please present this summary clearly to the user. After presenting, ask if they have any specific questions about these results."
    )
    
    # Present the summary (LLM formulates the presentation)
    ask_llm_and_get_user_response(summary_presentation_instruction, conversation_history) 
    # We capture the response but don't necessarily need it immediately, the LLM asked the question.

    # Task 2.2.4: Advanced Q&A loop using the parser
    while True:
        user_question = conversation_history[-1]['content'] 

        if user_question.lower() in ['no', 'nope', 'none', 'no thanks', 'that's all', 'exit', 'quit']:
            end_qna_msg = "Okay, let me know if you have more questions later or want to start a new task!"
            print(f"AI Research Assistant: {end_qna_msg}")
            conversation_history.append({"role": "assistant", "content": end_qna_msg})
            break
            
        # Determine what information the user is asking for
        # This is a simplified approach. A more robust way might involve function calling or more detailed classification.
        question_analysis_prompt = (
            f"Analyze the user's question: '{user_question}'. "
            "Based on keywords, determine which type of information they are asking about regarding the CRISPResso2 results. "
            "Respond with ONE of the following keywords ONLY: 'basic_stats', 'top_alleles', 'frameshift', 'nhej_hdr', 'other'. "
            "Example: If they ask 'What was the NHEJ percentage?', respond 'nhej_hdr'. If they ask 'Show the top 3 alleles', respond 'top_alleles'. If they ask about something not covered (e.g., 'Compare to another experiment'), respond 'other'."
        )
        
        # Use the LLM to classify the question type
        # Note: We don't add this internal classification step to the main conversation_history shown to the user
        llm_classification_response = get_llm_chat_response(conversation_history[:-1] + [{'role': 'system', 'content': question_analysis_prompt}], provider="gemini")
        info_type_requested = llm_classification_response.strip().lower()
        
        # print(f"DEBUG: LLM classified question type as: {info_type_requested}") # Optional debug
        
        # Retrieve data using the appropriate parser method
        data_for_llm = None
        if info_type_requested == 'basic_stats':
            data_for_llm = parser.get_basic_stats()
        elif info_type_requested == 'top_alleles':
            # Check if user asked for a specific number of alleles
            match = re.search(r'\b(\d+)\b', user_question) # Find numbers in question
            n_alleles = int(match.group(1)) if match else 5 # Default to 5 if no number found
            data_for_llm = parser.get_top_alleles(n=n_alleles)
        elif info_type_requested == 'frameshift':
            data_for_llm = parser.get_frameshift_analysis()
        elif info_type_requested == 'nhej_hdr':
            data_for_llm = parser.get_nhej_hdr_analysis()
        # Add more classifications and corresponding parser calls if needed

        # Prepare context for the LLM to generate the final answer
        answer_instruction = ""
        if data_for_llm and 'error' not in data_for_llm:
            answer_instruction = (
                f"The user asked: '{user_question}'.\n\n"
                f"Here is the relevant data extracted from the CRISPResso2 results:\n"
                f"```json\n{json.dumps(data_for_llm, indent=2)}\n```\n\n"
                "Please formulate a clear answer to the user's question based *only* on this provided data. "
                "Present the key information concisely."
            )
        elif data_for_llm and 'error' in data_for_llm:
             answer_instruction = (
                 f"The user asked: '{user_question}'.\n\n"
                 f"I tried to retrieve the relevant data, but encountered an error: {data_for_llm['error']}. "
                 "Please inform the user that this specific information couldn't be retrieved and state the reason."
            )
        else: # info_type_requested was 'other' or data retrieval failed unexpectedly
            answer_instruction = (
                f"The user asked: '{user_question}'.\n\n"
                "I couldn't find specific data in the parsed results files (like Allele frequencies, Frameshift analysis, etc.) that directly answers this question. "
                "Please inform the user that I can primarily answer questions about overall stats, top alleles, frameshift percentages, and NHEJ/HDR ratios based on the standard CRISPResso2 output files. You can also offer to show the overall summary again."
            )

        # Combine with follow-up prompt
        llm_answer_and_next_prompt_instruction = answer_instruction + " After providing the answer, ask the user if they have any further questions about the results."
        
        # Get LLM to generate answer and ask next question, then get user's reply for the next loop
        ask_llm_and_get_user_response(llm_answer_and_next_prompt_instruction, conversation_history)
        
    # Reset last_crispresso_output_dir? Consider if needed.
    # last_crispresso_output_dir = None 
    return "Finished interpreting CRISPResso results."

# --- Main Conversation Loop ---
def main_conversation_loop():
    """
    Manages the main interaction flow with the user.
    """
    # Initialize conversation history for the LLM
    # The first message sets up the LLM's persona or role.
    conversation_history = [
        {"role": "system", "content": "You are an AI Research Assistant specializing in CRISPR gene editing tools CHOPCHOP and CRISPResso2. You are helpful, clear, and guide novice users."}
    ]
    
    initial_greeting = "Hello! I am your AI Research Assistant. I can help you with CHOPCHOP (guide RNA design) and CRISPResso2 (editing analysis). What would you like to do? For example, you can say 'configure chopchop', 'design guides', or 'analyze crispresso data'."
    print(f"AI Research Assistant: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})

    while True:
        user_input = input("You: ")
        conversation_history.append({"role": "user", "content": user_input})

        if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            farewell_message = "Goodbye! Feel free to reach out if you need more help later."
            print(f"AI Research Assistant: {farewell_message}")
            conversation_history.append({"role": "assistant", "content": farewell_message})
            break
        
        response_text = ""
        # Simplified intent recognition - a real LLM would handle this more robustly
        user_intent = user_input.lower() # In a real system, LLM classifies intent

        if "configure chopchop" in user_intent:
            response_text = handle_chopchop_config_interaction(conversation_history)
        elif "design guides" in user_intent or "run chopchop" in user_intent:
            response_text = handle_chopchop_execution_interaction(conversation_history)
        elif "analyze crispresso" in user_intent or "run crispresso" in user_intent:
            response_text = handle_crispresso_execution_interaction(conversation_history)
        elif "interpret crispresso results" in user_intent:
            response_text = handle_crispresso_results_interaction(conversation_history)
        elif "help" in user_intent:
            response_text = ask_llm_and_get_user_response("I can help with: \n1. Configuring CHOPCHOP (say 'configure chopchop') \n2. Designing guides with CHOPCHOP (say 'design guides') \n3. Analyzing CRISPResso2 data (say 'analyze crispresso') \n4. Interpreting CRISPResso2 results (say 'interpret crispresso results'). \nWhat would you like to do?", conversation_history)
        else:
            # Fallback to a general LLM response if no specific action is matched
            # Use Gemini via tools/llm_api.py
            generic_prompt = "The user said: '" + user_input + "'. Respond helpfully as an AI research assistant for CRISPR tools."
            try:
                response_text = get_llm_chat_response(
                    conversation_history + [{'role': 'system', 'content': generic_prompt}],
                    provider="gemini"
                )
            except Exception as e:
                # Fallback if LLM call fails
                print(f"LLM API Error: {e}")
                response_text = "I'm sorry, I'm having trouble connecting to my language model. Could you try again or ask about something else?"

        print(f"AI Research Assistant: {response_text}")
        # Append assistant's final response to history (if not already done in ask_llm_and_get_user_response)
        # This part needs careful handling to avoid duplicate history entries if ask_llm_and_get_user_response
        # already appends the assistant's part of the exchange.
        # For this simple version, assuming ask_llm_and_get_user_response handles its part.
        # If response_text was generated directly (not via ask_llm_and_get_user_response), append it:
        if not any(entry["role"] == "assistant" and entry["content"] == response_text for entry in conversation_history[-2:]): # Basic check
             conversation_history.append({"role": "assistant", "content": response_text})


        # Optional: Trim conversation_history if it gets too long to save tokens for LLM
        # if len(conversation_history) > 20: # Example limit
        #     conversation_history = conversation_history[:1] + conversation_history[-19:]


if __name__ == "__main__":
    main_conversation_loop() 