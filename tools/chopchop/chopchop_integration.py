#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
CRISPResso2 - CHOPCHOP Integration
This script provides a simple interface to call CHOPCHOP from within CRISPResso2
'''

import os
import sys
import argparse
import subprocess
import json
import pandas as pd
import tempfile
import re
import shlex

def parse_arguments():
    parser = argparse.ArgumentParser(description='CHOPCHOP integration for CRISPResso2')
    parser.add_argument('--genome', '-G', type=str, required=True, help='Genome to use (must be configured in chopchop config)')
    parser.add_argument('--target', '-T', type=str, required=True, help='Target sequence or gene name')
    parser.add_argument('--output', '-o', type=str, default='chopchop_output', help='Output directory')
    parser.add_argument('--enzyme', '-e', type=str, default='Cas9', help='CRISPR enzyme type (Cas9, Cpf1)')
    parser.add_argument('--pam', '-p', type=str, default='NGG', help='PAM sequence')
    parser.add_argument('--guide_length', '-g', type=int, default=20, help='Guide length (excluding PAM)')
    parser.add_argument('--additional_args', type=str, default='', help='Additional arguments to pass to CHOPCHOP')
    return parser.parse_args()

def is_dna_sequence(text):
    """Check if the given text is likely a DNA sequence (containing mostly A, T, G, C)"""
    # Remove whitespace and standardize to uppercase
    text = ''.join(text.split()).upper()
    
    # If the text is very short, it's likely not a sequence
    if len(text) < 20:
        return False
    
    # Count DNA bases (A, T, G, C)
    base_count = sum(1 for c in text if c in 'ATGC')
    
    # If more than 90% of characters are DNA bases, it's likely a sequence
    return (base_count / len(text) > 0.9) if len(text) > 0 else False

def run_chopchop(args):
    """Run CHOPCHOP with the given arguments and return the output directory"""
    # Determine path to CHOPCHOP script and simple guide finder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chopchop_script = os.path.join(script_dir, 'chopchop.py')
    simple_guide_finder = os.path.join(os.path.dirname(script_dir), 'simple_guide_finder.py')
    
    # Import the COMMON_GENES dictionary from simple_guide_finder
    sys.path.append(os.path.dirname(script_dir))
    from simple_guide_finder import COMMON_GENES
    
    # Detect if running on Apple Silicon (M1/M2/M3)
    is_apple_silicon = False
    try:
        # Check architecture on macOS
        if sys.platform == 'darwin':
            import platform
            is_apple_silicon = platform.processor() == 'arm'
    except Exception:
        # If detection fails, we assume it's not Apple Silicon
        pass
    
    # If target is a known gene that has compatibility issues with CHOPCHOP,
    # or if we're on Apple Silicon (where twoBitToFa often fails),
    # use our simple_guide_finder directly
    if args.target.upper() in COMMON_GENES:
        print(f"Using built-in guide finder for {args.target} (avoids CHOPCHOP compatibility issues)")
        return run_simple_guide_finder(args.target, args.output, args.guide_length, args.pam)
    elif is_apple_silicon:
        print(f"Detected Apple Silicon. Using simple guide finder to avoid compatibility issues.")
        # For targets not in COMMON_GENES that might be sequence inputs
        if is_dna_sequence(args.target):
            print(f"Processing DNA sequence input with simple guide finder.")
            return run_simple_guide_finder(args.target, args.output, args.guide_length, args.pam)
        else:
            print(f"Warning: {args.target} is not in our built-in gene database and you're using Apple Silicon.")
            print("We'll attempt to use CHOPCHOP, but it may fail due to binary compatibility issues.")
            print("Consider providing a DNA sequence directly if CHOPCHOP fails.")
            # Continue with CHOPCHOP attempt as a fallback
    
    # For all other targets, proceed with CHOPCHOP
    
    # Ensure the genome parameter has no extra spaces
    genome = args.genome.strip()
    
    # Check if the target is a DNA sequence
    target = args.target
    temp_fasta_file = None
    
    if is_dna_sequence(target):
        # Create a temporary FASTA file for the sequence
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as temp_file:
            temp_fasta_file = temp_file.name
            temp_file.write(f">target_sequence\n{target}\n")
        
        # Update target to point to the FASTA file
        target = temp_fasta_file
        
        # Add -F flag to additional args to indicate this is a FASTA file
        args.additional_args += " -F"
        # Disable off-target search to avoid Bowtie issues
        if " -nonO" not in args.additional_args:
            args.additional_args += " -nonO"
        print(f"Detected DNA sequence input. Created temporary FASTA file: {temp_fasta_file}")
    else:
        # For gene symbols, add target region parameter
        if not "-targetRegion" in args.additional_args:
            # For general gene symbols, use -t WHOLE
            args.additional_args += " -t WHOLE" 
        
        # Disable off-target search to avoid Bowtie issues
        if " -nonO" not in args.additional_args:
            args.additional_args += " -nonO"
    
    # Build the command
    cmd = [sys.executable, chopchop_script]
    cmd.extend(['-G', genome])  
    cmd.extend(['-o', args.output])
    cmd.extend(['-Target', target])
    cmd.extend(['-g', str(args.guide_length)])
    cmd.extend(['-M', args.pam])
    cmd.extend(['-T', '1'])  # Mode 1 = Cas9
    
    # Add any additional arguments - split them properly
    if args.additional_args:
        # Split by space but preserve quoted strings
        additional_args = shlex.split(args.additional_args)
        cmd.extend(additional_args)
    
    # Print the command for debugging
    cmd_str = ' '.join(cmd)
    print(f"Running CHOPCHOP with command: {cmd_str}")
    
    # Run CHOPCHOP
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             universal_newlines=True)
        # Check if top_guides.json exists
        top_guides_path = os.path.join(args.output, 'top_guides.json')
        if os.path.exists(top_guides_path):
            # Clean up temporary file if used
            if temp_fasta_file and os.path.exists(temp_fasta_file):
                os.unlink(temp_fasta_file)
            return args.output
        else:
            print(f"CHOPCHOP ran but did not produce the expected output file: {top_guides_path}")
            # Clean up temporary file if used
            if temp_fasta_file and os.path.exists(temp_fasta_file):
                os.unlink(temp_fasta_file)
            
            # FALLBACK: Try simple guide finder
            print("Using simple guide finder as fallback...")
            return run_simple_guide_finder(args.target, args.output, args.guide_length, args.pam)
    except subprocess.CalledProcessError as e:
        print(f"Error running CHOPCHOP: {e.stderr}")
        # Clean up temporary file if used
        if temp_fasta_file and os.path.exists(temp_fasta_file):
            os.unlink(temp_fasta_file)
        
        # FALLBACK: Try simple guide finder
        print("Using simple guide finder as fallback...")
        return run_simple_guide_finder(args.target, args.output, args.guide_length, args.pam)

def run_simple_guide_finder(sequence, output_dir, guide_length, pam):
    """Run the simple guide finder script as a fallback"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    simple_guide_finder = os.path.join(os.path.dirname(script_dir), 'simple_guide_finder.py')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Build command
    cmd = [
        sys.executable,
        simple_guide_finder,
        '--sequence', sequence,
        '--output', output_dir,
        '--guide_length', str(guide_length),
        '--pam', pam
    ]
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True)
        print(result.stdout)
        
        # Check if the output file was generated
        top_guides_path = os.path.join(output_dir, 'top_guides.json')
        if os.path.exists(top_guides_path):
            return output_dir
    except subprocess.CalledProcessError as e:
        print(f"Error running simple guide finder: {e.stderr}")
    except FileNotFoundError:
        print(f"Couldn't find the simple guide finder script at {simple_guide_finder}")
    
    return None

def parse_results(output_dir, target):
    """Parse the CHOPCHOP results and return a list of guides"""
    # Read the top_guides.json file
    top_guides_path = os.path.join(output_dir, 'top_guides.json')
    if not os.path.exists(top_guides_path):
        print(f"Error: Could not find top_guides.json in {output_dir}")
        return None
    
    try:
        with open(top_guides_path, 'r') as f:
            guides_data = json.load(f)
        
        # Handle both original CHOPCHOP format and our simple_guide_finder format
        if 'guides' in guides_data:
            guides = guides_data['guides']
        else:
            guides = guides_data  # Original CHOPCHOP format
        
        # Convert to pandas DataFrame for easier manipulation
        df = pd.DataFrame(guides)
        
        # Return the top guides
        return df.to_dict('records')
    except Exception as e:
        print(f"Error parsing CHOPCHOP results: {str(e)}")
        return None

def main():
    args = parse_arguments()
    
    # Run CHOPCHOP and get the output directory
    output_dir = run_chopchop(args)
    
    if output_dir:
        # Parse the results
        guides = parse_results(output_dir, args.target)
        
        # Print the results
        if guides:
            print(f"\nFound {len(guides)} guide RNAs for {args.target}")
            for i, guide in enumerate(guides[:10]):  # Show top 10
                seq = guide.get('seq', 'N/A')
                pam = guide.get('pam', 'N/A')
                score = guide.get('score', guide.get('efficiency', 'N/A'))
                print(f"{i+1}. {seq}{pam} - Score: {score}")
            
            # Save the guides to a simplified JSON file
            output_file = os.path.join(output_dir, 'top_guides_simplified.json')
            with open(output_file, 'w') as f:
                json.dump(guides, f, indent=2)
            
            print(f"\nGuide RNAs saved to {output_file}")
        else:
            print("No guides found.")
    else:
        print("CHOPCHOP execution failed.")

if __name__ == "__main__":
    main() 