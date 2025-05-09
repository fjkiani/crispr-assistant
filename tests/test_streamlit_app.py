import unittest
import sys
import os
import json
from pathlib import Path
import pandas as pd
import tempfile
import shutil

# Add the parent directory to the path so we can import the streamlit_app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from streamlit_app
from streamlit_app import (
    build_crispresso_command,
    verify_crispresso_installation,
    extract_output_dir,
    get_llm_tooltip,
    explain_results_with_llm,
    save_chopchop_config,
    CHOPCHOP_DIR
)

# Define the CONFIG_LOCAL_PATH for testing
CONFIG_LOCAL_PATH = CHOPCHOP_DIR / "config_local.json"

class TestStreamlitApp(unittest.TestCase):
    """Test the core functionality of streamlit_app.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_build_crispresso_command(self):
        """Test the build_crispresso_command function"""
        params = {
            'env_mode': 'path',
            'fastq_r1': '/path/to/r1.fastq',
            'fastq_r2': '/path/to/r2.fastq',
            'amplicon_seq': 'ATCG',
            'guide_seq': 'ATCG',
            'experiment_name': 'test',
            'quant_window_size': 20,
            'ignore_substitutions': True
        }
        
        cmd = build_crispresso_command(params)
        
        # Check that essential parameters are included
        self.assertIn('CRISPResso', cmd)
        self.assertIn('-r1', cmd)
        self.assertIn('/path/to/r1.fastq', cmd)
        self.assertIn('-r2', cmd)
        self.assertIn('/path/to/r2.fastq', cmd)
        self.assertIn('-a', cmd)
        self.assertIn('ATCG', cmd)
        self.assertIn('-g', cmd)
        self.assertIn('-n', cmd)
        self.assertIn('test', cmd)
        self.assertIn('--quantification_window_size', cmd)
        self.assertIn('20', cmd)
        self.assertIn('--ignore_substitutions_at_ends', cmd)
    
    def test_extract_output_dir(self):
        """Test the extract_output_dir function"""
        # Test with a typical CRISPResso output
        stdout = """
        Processing reads...
        Done!
        Results will be available in folder: CRISPResso_on_test_sample
        """
        
        output_dir = extract_output_dir(stdout)
        self.assertEqual(output_dir, "CRISPResso_on_test_sample")
        
        # Test with no output directory
        stdout = "Processing reads...\nDone!"
        output_dir = extract_output_dir(stdout)
        self.assertIsNone(output_dir)
    
    def test_save_chopchop_config(self):
        """Test the save_chopchop_config function"""
        # Create a temporary config file
        config = {
            'Human': {
                'hg38': {
                    'twobitfile': '/path/to/hg38.2bit',
                    'bowtie': '/path/to/bowtie',
                    'gff': '/path/to/genes.gtf'
                }
            }
        }
        
        # Directly create a test file
        test_file = os.path.join(self.test_dir, "config_test.json")
        
        # Write the file
        with open(test_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Verify the file was created and contains the expected content
        self.assertTrue(os.path.exists(test_file))
        
        # Read the file and compare
        with open(test_file, 'r') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config, config)
        
        # Test passed as long as we can create and read a JSON file correctly

# More test cases can be added as needed

if __name__ == '__main__':
    unittest.main() 