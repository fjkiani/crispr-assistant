import os
import subprocess
import argparse
import json # For potentially handling structured prompts/history in the future
import sys  # Add sys for using the current Python executable

# --- Constants ---
# Assuming the script is in project_root/tools/llm_api.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use the current Python executable instead of assuming a venv location
VENV_PYTHON = sys.executable
LLM_API_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "tools", "llm_api.py")

# --- Simplified function for modules that directly import query_llm ---
def query_llm(prompt, provider="gemini", image_path=None):
    """
    Simple wrapper function that accepts a string prompt and returns a string response.
    This is the function imported by other modules and called by streamlit_app.py.
    
    Args:
        prompt (str): The text prompt to send to the LLM.
        provider (str): The LLM provider to use (e.g., "gemini", "openai", "anthropic").
        image_path (str, optional): Path to an image for multimodal LLMs.
        
    Returns:
        str: The LLM's text response.
    """
    # Convert the single prompt into a conversation history format
    conversation_history = [
        {"role": "system", "content": "You are a helpful AI assistant for CRISPR genome editing."},
        {"role": "user", "content": prompt}
    ]
    
    # Call the more advanced chat function with the simple conversation
    return get_llm_chat_response(
        conversation_history=conversation_history,
        provider=provider,
        image_path=image_path
    )

# --- Helper function for formatting conversation history for a single prompt string ---
def format_history_for_cli_prompt(conversation_history):
    """
    Formats a list of conversation messages into a single string prompt.
    Each message in conversation_history should be a dict: {"role": "user/assistant/system", "content": "..."}
    """
    prompt_str = ""
    for message in conversation_history:
        # Simple concatenation; specific models might prefer different formatting.
        # For Gemini, the prompt passed to the CLI might be handled by the CLI part itself if it uses the chat API.
        # If the CLI uses a simple text completion, this format is a starting point.
        prompt_str += f"{message['role'].capitalize()}: {message['content']}\n\n"
    return prompt_str.strip()

# --- Python function for Agent to call ---
def get_llm_chat_response(conversation_history, provider="gemini", model_name=None, image_path=None, temperature=0.7, max_tokens=1024):
    """
    Gets a chat response from the specified LLM provider by calling the CLI interface of this script.

    Args:
        conversation_history (list): List of message dictionaries (e.g., [{"role": "system", "content": "..."}, ...]).
        provider (str): The LLM provider to use (e.g., "gemini", "openai", "anthropic").
        model_name (str, optional): Specific model name if applicable.
        image_path (str, optional): Path to an image for multimodal LLMs.
        temperature (float): Temperature for sampling.
        max_tokens (int): Max tokens for the response.

    Returns:
        str: The LLM's text response, or an error message.
    """
    # Format the conversation history into a single prompt string for the CLI
    # The system message and alternating user/assistant turns should be handled here.
    cli_prompt = format_history_for_cli_prompt(conversation_history)

    cmd = [
        VENV_PYTHON, # Use python from the virtual environment
        LLM_API_SCRIPT_PATH, # Call this script itself
        "--prompt", cli_prompt,
        "--provider", provider,
        # TODO: Add logic to handle temperature and max_tokens if the CLI supports them
    ]

    if model_name:
        cmd.extend(["--model", model_name])
    if image_path:
        cmd.extend(["--image", image_path])

    try:
        # print(f"DEBUG: LLM API calling command: {' '.join(cmd)}") # For debugging
        process_result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=PROJECT_ROOT)
        # print(f"DEBUG: LLM API stdout: {process_result.stdout}") # For debugging
        # print(f"DEBUG: LLM API stderr: {process_result.stderr}") # For debugging
        return process_result.stdout.strip() # Assuming the CLI prints the LLM response to stdout
    except subprocess.CalledProcessError as e:
        error_message = f"Error calling LLM API (provider: {provider}): {e}\nStderr: {e.stderr}"
        print(error_message) # Log the error
        return f"Error: Could not get a response from the LLM. Details: {e.stderr}" # Return a user-friendly error
    except FileNotFoundError:
        error_message = f"Error: Could not find VENV_PYTHON ('{VENV_PYTHON}') or LLM_API_SCRIPT_PATH ('{LLM_API_SCRIPT_PATH}'). Please check paths."
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"An unexpected error occurred in get_llm_chat_response: {e}"
        print(error_message)
        return "Error: An unexpected error occurred while contacting the LLM."

# --- CLI Argument Parsing and Main Logic --- 
def main_cli():
    # --- Load .env file if it exists --- START
    try:
        from dotenv import load_dotenv
        dotenv_path = os.path.join(PROJECT_ROOT, '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
            # print("DEBUG: Loaded .env file.") # Optional debug message
        else:
            # print("DEBUG: .env file not found, relying on environment variables.") # Optional debug message
            pass
    except ImportError:
        # dotenv not installed, proceed without it, relying on environment vars
        # print("DEBUG: python-dotenv not installed. Relying on environment variables.") # Optional debug message
        pass
    # --- Load .env file if it exists --- END

    parser = argparse.ArgumentParser(description="Interact with various LLM providers. Outputs LLM response to stdout.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the LLM.")
    parser.add_argument("--provider", type=str, required=True, choices=["gemini", "openai", "anthropic", "deepseek", "azure_openai", "local_llm"], help="The LLM provider.")
    parser.add_argument("--model", type=str, help="Optional: Specific model name for the provider.")
    parser.add_argument("--image", type=str, help="Optional: Path to an image for multimodal LLMs.")
    # Add other relevant CLI arguments here (e.g., temperature, max_tokens) if needed

    args = parser.parse_args()

    if args.provider == "gemini":
        try:
            import google.generativeai as genai # Make sure this is installed in your venv
            
            # Now, os.environ.get should find the key loaded from .env
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key or api_key == "your_gemini_api_key_here":
                return """⚠️ GEMINI_API_KEY not properly configured!

To use the AI features, you need to:
1. Get your free API key from https://aistudio.google.com/app/apikey
2. Create a .env file in the project root with:
   GEMINI_API_KEY=your_actual_key_here
3. Restart the application

Without an API key, AI-powered assistance features will not work."""

            genai.configure(api_key=api_key)
            
            # Update model name to use the latest Gemini model
            model_name_to_use = args.model if args.model else 'gemini-1.5-pro' 
            # You might want to use a newer/specific model like 'gemini-1.5-pro-latest' or 'gemini-1.5-pro'
            # Check Google AI Studio for available model names.
            model = genai.GenerativeModel(model_name_to_use)
            
            # The args.prompt contains the full conversation history formatted as a single string.
            # For Gemini, especially with chat models, you might want to send the structured history.
            # However, for a simple text-in, text-out via CLI, sending the formatted string is a start.
            # For more advanced chat, you'd parse args.prompt back into a history list if possible,
            # or adjust get_llm_chat_response to pass structured history to the CLI if CLI supports it.
            
            # For multimodal prompts with images (if your chosen model supports it):
            if args.image and model_name_to_use in ['gemini-pro-vision', 'gemini-1.5-pro-latest', 'gemini-1.5-pro']: # Add other vision-capable models
                try:
                    from PIL import Image # Ensure Pillow is installed: pip install Pillow
                    img = Image.open(args.image)
                    response = model.generate_content([args.prompt, img])
                except ImportError:
                    return "Error: Pillow library not found. Please install it (pip install Pillow) to send images."
                except FileNotFoundError:
                    return f"Error: Image file not found at {args.image}"
            else:
                response = model.generate_content(args.prompt) # Text-only prompt
            
            print(response.text)

        except ImportError:
            return """Error: google-generativeai library not found. 

Please run the following command to install it:
pip install google-generativeai"""
        except Exception as e:
            # Catching potential API errors, configuration issues, etc.
            return f"Error calling Google Gemini API: {e}"
        
    elif args.provider == "openai":
        try:
            import openai
            
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key or api_key == "your_openai_api_key_here":
                return """⚠️ OPENAI_API_KEY not properly configured!

To use OpenAI features, you need to:
1. Get your API key from https://platform.openai.com/api-keys
2. Add to your .env file:
   OPENAI_API_KEY=your_actual_key_here
3. Restart the application"""
                
            openai.api_key = api_key
            
            # Use gpt-4o as default model
            model_name_to_use = args.model if args.model else "gpt-4o"
            
            # Create a more structured conversation history
            messages = [{"role": "system", "content": "You are a helpful AI assistant for CRISPR genome editing."}]
            
            # Extract user/assistant messages from the prompt
            lines = args.prompt.strip().split("\n\n")
            for line in lines:
                if line.startswith("User:"):
                    messages.append({"role": "user", "content": line[5:].strip()})
                elif line.startswith("Assistant:"):
                    messages.append({"role": "assistant", "content": line[10:].strip()})
                elif line.startswith("System:"):
                    # Override the default system message if provided
                    messages[0] = {"role": "system", "content": line[7:].strip()}
            
            response = openai.chat.completions.create(
                model=model_name_to_use,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            return """Error: OpenAI library not found.

Please run the following command to install it:
pip install openai>=1.0.0"""
        except Exception as e:
            return f"Error calling OpenAI API: {e}"

    # Add support for Anthropic Claude
    elif args.provider == "anthropic":
        try:
            import anthropic
            
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key or api_key == "your_anthropic_api_key_here":
                return """⚠️ ANTHROPIC_API_KEY not properly configured!

To use Claude features, you need to:
1. Get your API key from https://console.anthropic.com/settings/keys
2. Add to your .env file:
   ANTHROPIC_API_KEY=your_actual_key_here
3. Restart the application"""
            
            client = anthropic.Anthropic(api_key=api_key)
            
            # Use Claude 3 Sonnet as default model
            model_name_to_use = args.model if args.model else "claude-3-sonnet-20240229"
            
            # Format message history for Claude
            # For a basic implementation, we'll just use the input prompt directly
            response = client.messages.create(
                model=model_name_to_use,
                max_tokens=1000,
                temperature=0.7,
                system="You are a helpful AI assistant for CRISPR genome editing.",
                messages=[{"role": "user", "content": args.prompt}]
            )
            
            return response.content[0].text
            
        except ImportError:
            return """Error: Anthropic library not found.

Please run the following command to install it:
pip install anthropic>=0.5.0"""
        except Exception as e:
            return f"Error calling Anthropic API: {e}"

    else:
        return f"""Provider '{args.provider}' is not fully implemented.

Currently supported providers:
- gemini (requires GEMINI_API_KEY)
- openai (requires OPENAI_API_KEY)
- anthropic (requires ANTHROPIC_API_KEY)

Please add the appropriate API key to your .env file."""

if __name__ == "__main__":
    result = main_cli()
    if result:
        print(result) 