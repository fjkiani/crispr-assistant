import unittest
import sys
import os
import subprocess
import tempfile
import time
import json
from pathlib import Path

# Add the parent directory to the path so we can import the streamlit_app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestStreamlitIntegration(unittest.TestCase):
    """Integration tests for the Streamlit application"""
    
    @classmethod
    def setUpClass(cls):
        """Set up class fixtures - run once for the class"""
        # Verify that streamlit is installed
        try:
            subprocess.run(["streamlit", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise unittest.SkipTest("Streamlit is not installed. Skipping integration tests.")
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create a sample .env file if it doesn't exist
        self.env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        self.created_env = False
        if not os.path.exists(self.env_file):
            with open(self.env_file, "w") as f:
                f.write("# Test .env file\n")
                f.write("GEMINI_API_KEY=your_test_key_here\n")
            self.created_env = True
        
        # Create a sample config_local.json for CHOPCHOP
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "chopchop")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "config_local.json")
        self.created_config = False
        if not os.path.exists(self.config_file):
            with open(self.config_file, "w") as f:
                json.dump({
                    "Human": {
                        "hg38": {
                            "twobitfile": "/path/to/hg38.2bit",
                            "bowtie": "/path/to/bowtie",
                            "gff": "/path/to/genes.gtf"
                        }
                    }
                }, f)
            self.created_config = True
    
    def tearDown(self):
        """Tear down test fixtures"""
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(self.test_dir)
        
        # Remove the .env file if we created it
        if self.created_env and os.path.exists(self.env_file):
            os.remove(self.env_file)
        
        # Remove the config file if we created it
        if self.created_config and os.path.exists(self.config_file):
            os.remove(self.config_file)
    
    def test_streamlit_starts(self):
        """Test that the Streamlit app starts without errors"""
        # Start the Streamlit app
        app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "streamlit_app.py")
        
        # Run the app with a timeout
        process = subprocess.Popen(
            ["streamlit", "run", app_path, "--server.headless", "true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for the app to start (allow up to 10 seconds)
        start_time = time.time()
        timeout = 10
        app_started = False
        
        while time.time() - start_time < timeout:
            returncode = process.poll()
            if returncode is not None:
                # Process ended - this is an error
                stdout, stderr = process.communicate()
                self.fail(f"Streamlit app failed to start: {stderr}")
            
            # Check stdout for the "Streamlit app running" message
            stdout = process.stdout.readline()
            if "You can now view your Streamlit app" in stdout:
                app_started = True
                break
            
            time.sleep(0.1)
        
        # Terminate the process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # Check that the app started successfully
        self.assertTrue(app_started, "Streamlit app failed to start within the timeout period")
    
    def test_mock_llm_workflow(self):
        """Test a mock workflow with the LLM components"""
        # Here we'll create a mock LLM module to test the workflow
        mock_llm_path = os.path.join(self.test_dir, "mock_llm_api.py")
        with open(mock_llm_path, "w") as f:
            f.write("""
def query_llm(prompt, provider="mock", image_path=None):
    '''Mock implementation of query_llm'''
    return f"Mock LLM response for: {prompt[:50]}..."
""")
        
        # Import the mock module
        sys.path.insert(0, self.test_dir)
        import mock_llm_api
        
        # Test the get_llm_tooltip function from streamlit_app.py
        # We'll need to monkey patch the ask_llm function to use our mock
        from streamlit_app import get_llm_tooltip
        
        # Store the original function
        import streamlit_app
        original_ask_llm = streamlit_app.ask_llm
        
        # Replace with our mock
        streamlit_app.ask_llm = lambda prompt, provider="mock": mock_llm_api.query_llm(prompt, provider)
        
        try:
            # Now test the function
            tooltip = get_llm_tooltip("PAM Sequence")
            self.assertTrue(tooltip.startswith("Mock LLM response for:"))
            
            # Test the explain_results_with_llm function
            from streamlit_app import explain_results_with_llm
            explanation = explain_results_with_llm("test_data", "Sample data")
            self.assertTrue(explanation.startswith("Mock LLM response for:"))
            
        finally:
            # Restore the original function
            streamlit_app.ask_llm = original_ask_llm
            
            # Remove the mock module from sys.modules
            if "mock_llm_api" in sys.modules:
                del sys.modules["mock_llm_api"]
            
            # Remove the directory from sys.path
            sys.path.remove(self.test_dir)
    
    # Add more integration tests as needed

if __name__ == "__main__":
    unittest.main() 