#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Simple Guide Finder - Fallback for CHOPCHOP
This script provides a simple way to find guide RNA candidates in a DNA sequence for Cas9
'''

import os
import sys
import argparse
import json
import re
import tempfile
import glob
from pathlib import Path

def load_gene_from_file(gene_symbol):
    """
    Load a gene sequence from a FASTA file in the gene_database directory
    Returns None if the gene isn't found
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Look in a 'gene_database' directory at the same level as tools
    db_dir = os.path.join(os.path.dirname(script_dir), 'gene_database')
    
    # Check main project directory if gene_database doesn't exist
    if not os.path.exists(db_dir):
        db_dir = os.path.dirname(script_dir)
    
    # Look for files that might contain the gene
    potential_files = [
        # Exact match files
        os.path.join(db_dir, f"{gene_symbol}.fasta"),
        os.path.join(db_dir, f"{gene_symbol}.fa"),
        os.path.join(db_dir, f"{gene_symbol}_sequence.fasta"),
        os.path.join(db_dir, f"{gene_symbol.lower()}.fasta"),
        # Look in root directory too
        os.path.join(os.path.dirname(db_dir), f"{gene_symbol}.fasta"),
        os.path.join(os.path.dirname(db_dir), f"{gene_symbol}.fa"),
        os.path.join(os.path.dirname(db_dir), f"{gene_symbol}_sequence.fasta"),
    ]
    
    # Try each potential file path
    for file_path in potential_files:
        if os.path.exists(file_path):
            try:
                return read_fasta(file_path)
            except Exception as e:
                print(f"Error reading gene file {file_path}: {e}")
                continue
    
    return None

# Dictionary of common gene sequences
COMMON_GENES = {
    "TP53": "ATGGAGGAGCCGCAGTCAGATCCTAGCGTCGAGCCCCCTCTGAGTCAGGAAACATTTTCAGACCTATGGAAACTACTTCCTGAAAACAACGTTCTGTCCCCCTTGCCGTCCCAAGCAATGGATGATTTGATGCTGTCCCCGGACGATATTGAACAATGGTTCACTGAAGACCCAGGTCCAGATGAAGCTCCCAGAATGCCAGAGGCTGCTCCCCGCGTGGCCCCTGCACCAGCAGCTCCTACACCGGCGGCCCCTGCACCAGCCCCCTCCTGGCCCCTGTCATCTTCTGTCCCTTCCCAGAAAACCTACCAGGGCAGCTACGGTTTCCGTCTGGGCTTCTTGCATTCTGGGACAGCCAAGTCTGTGACTTGCACGTACTCCCCTGCCCTCAACAAGATGTTTTGCCAACTGGCCAAGACCTGCCCTGTGCAGCTGTGGGTTGATTCCACACCCCCGCCCGGCACCCGCGTCCGCGCCATGGCCATCTACAAGCAGTCACAGCACATGACGGAGGTTGTGAGGCGCTGCCCCCACCATGAGCGCTGCTCAGATAGCGATGGTCTGGCCCCTCCTCAGCATCTTATCCGAGTGGAAGGAAATTTGCGTGTGGAGTATTTGGATGACAGAAACACTTTTCGACATAGTGTGGTGGTGCCCTATGAGCCGCCTGAGGTTGGCTCTGACTGTACCACCATCCACTACAACTACATGTGTAACAGTTCCTGCATGGGCGGCATGAACCGGAGGCCCATCCTCACCATCATCACACTGGAAGACTCCAG"
}

def parse_arguments():
    parser = argparse.ArgumentParser(description='Simple Guide Finder - Fallback for CHOPCHOP')
    parser.add_argument('--sequence', '-s', type=str, required=True, help='DNA sequence, gene symbol, or path to FASTA file')
    parser.add_argument('--output', '-o', type=str, default='guides_output', help='Output directory')
    parser.add_argument('--guide_length', '-g', type=int, default=20, help='Guide length (excluding PAM)')
    parser.add_argument('--pam', '-p', type=str, default='NGG', help='PAM sequence')
    return parser.parse_args()

def is_valid_dna(sequence):
    """Check if a sequence contains only valid DNA bases"""
    return bool(re.match(r'^[ATGCN]+$', sequence.upper()))

def read_fasta(fasta_path):
    """Read sequence from FASTA file"""
    with open(fasta_path, 'r') as f:
        lines = f.readlines()
    
    # Skip header lines starting with '>'
    sequence = ''
    for line in lines:
        if not line.startswith('>'):
            sequence += line.strip()
    
    return sequence.upper()

def find_guides(sequence, guide_length=20, pam_pattern='NGG'):
    """Find all potential guide RNA sites in the sequence"""
    sequence = sequence.upper()
    guides = []
    
    # Replace the PAM pattern with regex pattern
    pam_regex = pam_pattern.replace('N', '[ATGC]')
    
    # Find all occurrences of the PAM
    for i in range(len(sequence) - guide_length - len(pam_pattern) + 1):
        potential_pam = sequence[i + guide_length:i + guide_length + len(pam_pattern)]
        if re.match(pam_regex, potential_pam):
            guide_seq = sequence[i:i + guide_length]
            pam = potential_pam
            
            # Skip guides with N in the sequence
            if 'N' in guide_seq:
                continue
            
            # Calculate a basic score (placeholder)
            # In a real implementation, you would add proper scoring metrics
            gc_content = (guide_seq.count('G') + guide_seq.count('C')) / len(guide_seq)
            score = 0.5  # Default score
            
            # Adjust score based on GC content (simple heuristic)
            if 0.4 <= gc_content <= 0.6:
                score += 0.3
            
            # Prefer guides with G at position 20 (start of PAM)
            if guide_seq[-1] == 'G':
                score += 0.1
            
            # Prefer guides without poly-T (4+ Ts in a row can terminate transcription)
            if 'TTTT' not in guide_seq:
                score += 0.1
            
            guide = {
                "seq": guide_seq,
                "pam": pam,
                "strand": "+",
                "start": i,
                "end": i + guide_length + len(pam_pattern),
                "efficiency": score,
                "specificity": 0.5,  # Placeholder (would require alignment for real score)
                "score": score
            }
            guides.append(guide)
    
    # Sort guides by score
    guides.sort(key=lambda x: x["score"], reverse=True)
    return guides

def main():
    args = parse_arguments()
    
    # Get the DNA sequence
    if os.path.isfile(args.sequence):
        sequence = read_fasta(args.sequence)
    elif args.sequence.upper() in COMMON_GENES:
        # Look up sequence by gene symbol in our built-in dictionary
        gene_symbol = args.sequence.upper()
        sequence = COMMON_GENES[gene_symbol]
        print(f"Found built-in sequence for gene: {gene_symbol} ({len(sequence)} bp)")
    else:
        # Check if we have this gene in an external file
        gene_symbol = args.sequence.upper()
        external_sequence = load_gene_from_file(gene_symbol)
        
        if external_sequence:
            sequence = external_sequence
            print(f"Loaded gene sequence for {gene_symbol} from file ({len(sequence)} bp)")
        else:
            # Treat as direct sequence input
            sequence = args.sequence
            print(f"Treating input as direct DNA sequence ({len(sequence)} characters)")
    
    # Validate the sequence
    if not is_valid_dna(sequence):
        print(f"Error: Invalid DNA sequence. The sequence must contain only A, T, G, C, or N.")
        sys.exit(1)
    
    # Find guide candidates
    guides = find_guides(sequence, args.guide_length, args.pam)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Save guides to JSON file
    output_file = os.path.join(args.output, 'top_guides.json')
    with open(output_file, 'w') as f:
        json.dump({"guides": guides}, f, indent=2)
    
    # Print summary
    print(f"Found {len(guides)} potential guide RNA candidates.")
    print(f"Top guides saved to {output_file}.")
    
    # Print top 5 guides
    for i, guide in enumerate(guides[:5]):
        print(f"{i+1}. {guide['seq']} (PAM: {guide['pam']}) - Score: {guide['score']:.2f}")

if __name__ == "__main__":
    main() 