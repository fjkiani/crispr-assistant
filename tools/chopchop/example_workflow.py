#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Example workflow integrating CHOPCHOP guide design with CRISPResso2 analysis
'''

import os
import sys
import json
import argparse
import subprocess
import pandas as pd
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser(description='Example workflow integrating CHOPCHOP with CRISPResso2')
    parser.add_argument('--genome', '-G', type=str, required=True, help='Genome to use (must be configured in CHOPCHOP config)')
    parser.add_argument('--target', '-T', type=str, required=True, help='Target gene or sequence')
    parser.add_argument('--fastq_r1', type=str, help='FASTQ R1 for CRISPResso2 analysis')
    parser.add_argument('--fastq_r2', type=str, help='FASTQ R2 for CRISPResso2 analysis (optional)')
    parser.add_argument('--output', '-o', type=str, default='chopchop_crispresso_workflow', help='Output directory')
    
    return parser.parse_args()

def run_chopchop(genome, target, output_dir):
    """Run CHOPCHOP to design guides"""
    # Get path to integration script
    chopchop_dir = os.path.dirname(os.path.abspath(__file__))
    integration_script = os.path.join(chopchop_dir, 'chopchop_integration.py')
    
    cmd = [
        sys.executable,
        integration_script,
        '--genome', genome,
        '--target', target,
        '--output', os.path.join(output_dir, 'chopchop_results')
    ]
    
    print(f"Running CHOPCHOP with command: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Error running CHOPCHOP: {stderr.decode('utf-8')}")
        sys.exit(1)
    
    # Load the top guides
    json_file = os.path.join(output_dir, 'chopchop_results', 'top_guides.json')
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            guides = json.load(f)
        return guides
    else:
        print(f"Could not find CHOPCHOP results: {json_file}")
        sys.exit(1)

def run_crispresso2(target_seq, fastq_r1, fastq_r2, output_dir):
    """Run CRISPResso2 to analyze editing outcomes"""
    # Ensure output directory exists
    os.makedirs(os.path.join(output_dir, 'crispresso_results'), exist_ok=True)
    
    # Build CRISPResso2 command
    cmd = ['CRISPResso']
    
    # Add common parameters
    cmd.extend([
        '--amplicon_seq', target_seq,
        '--fastq_r1', fastq_r1,
        '--output_folder', os.path.join(output_dir, 'crispresso_results')
    ])
    
    # Add R2 if provided
    if fastq_r2:
        cmd.extend(['--fastq_r2', fastq_r2])
    
    # Run CRISPResso2
    print(f"Running CRISPResso2 with command: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Error running CRISPResso2: {stderr.decode('utf-8')}")
        sys.exit(1)
    
    print(f"CRISPResso2 completed successfully. Results saved to {os.path.join(output_dir, 'crispresso_results')}")

def main():
    args = parse_arguments()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Step 1: Run CHOPCHOP to design guides
    print("\n=== STEP 1: Designing guides with CHOPCHOP ===")
    guides = run_chopchop(args.genome, args.target, args.output)
    
    # Display top guide
    if guides and len(guides) > 0:
        top_guide = guides[0]
        print(f"\nTop guide selected: {top_guide.get('Target sequence', 'Unknown')}")
        print(f"Efficiency score: {top_guide.get('Efficiency', 'Unknown')}")
        print(f"Position: {top_guide.get('Location', 'Unknown')}")
        
        # Save to output directory
        with open(os.path.join(args.output, 'selected_guide.json'), 'w') as f:
            json.dump(top_guide, f, indent=2)
    
    # Step 2: If FASTQ files are provided, run CRISPResso2 for analysis
    if args.fastq_r1:
        print("\n=== STEP 2: Analyzing editing outcomes with CRISPResso2 ===")
        if guides and len(guides) > 0:
            # Extract target sequence from top guide
            target_seq = top_guide.get('Target sequence', '')
            if target_seq:
                run_crispresso2(target_seq, args.fastq_r1, args.fastq_r2, args.output)
            else:
                print("Could not extract target sequence from CHOPCHOP results.")
        else:
            print("No guides found from CHOPCHOP. Cannot run CRISPResso2 analysis.")
    else:
        print("\nFASTQ files not provided. Skipping CRISPResso2 analysis.")
        print("To run the complete workflow, provide --fastq_r1 and optionally --fastq_r2 parameters.")
    
    print("\n=== Workflow Completed ===")
    print(f"All results are saved in: {args.output}")

if __name__ == "__main__":
    main() 