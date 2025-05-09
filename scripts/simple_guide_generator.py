#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Simple Guide Generator
This script provides a simple way to generate guide RNAs from a sequence
without requiring Bowtie or other complex dependencies
'''

import os
import sys
import argparse
import json
import re
from Bio.Seq import Seq
import pandas as pd

def parse_arguments():
    parser = argparse.ArgumentParser(description='Simple Guide RNA Generator')
    parser.add_argument('--sequence', '-s', type=str, required=True, help='DNA sequence to search for guides')
    parser.add_argument('--output', '-o', type=str, default='guides_output.json', help='Output file (.json)')
    parser.add_argument('--enzyme', '-e', type=str, default='Cas9', choices=['Cas9', 'Cpf1'], help='CRISPR enzyme to use')
    parser.add_argument('--guide_length', '-g', type=int, default=20, help='Guide RNA length')
    
    return parser.parse_args()

def find_cas9_guides(sequence, guide_length=20):
    """Find all possible guides for Cas9 (NGG PAM)"""
    guides = []
    
    # Forward strand - look for NGG pattern
    pattern = r'(?=(.{' + str(guide_length) + '})GG)'
    for match in re.finditer(pattern, sequence):
        guide_seq = match.group(1)
        pam_seq = sequence[match.end(1):match.end(1)+2]
        start_pos = match.start(1)
        
        # Calculate GC content
        gc_content = (guide_seq.count('G') + guide_seq.count('C')) / len(guide_seq) * 100
        
        guides.append({
            'sequence': guide_seq,
            'pam': pam_seq,
            'position': start_pos + 1,  # 1-based position
            'strand': '+',
            'gc_content': round(gc_content, 1)
        })
    
    # Reverse strand - look for CCN pattern and reverse complement
    rc_sequence = str(Seq(sequence).reverse_complement())
    for match in re.finditer(pattern, rc_sequence):
        guide_seq = match.group(1)
        pam_seq = rc_sequence[match.end(1):match.end(1)+2]
        start_pos = len(sequence) - match.start(1) - guide_length
        
        # Calculate GC content
        gc_content = (guide_seq.count('G') + guide_seq.count('C')) / len(guide_seq) * 100
        
        guides.append({
            'sequence': guide_seq,
            'pam': pam_seq,
            'position': start_pos + 1,  # 1-based position
            'strand': '-',
            'gc_content': round(gc_content, 1)
        })
    
    return guides

def find_cpf1_guides(sequence, guide_length=20):
    """Find all possible guides for Cpf1 (TTTN PAM)"""
    guides = []
    
    # Forward strand - look for TTTN pattern
    pattern = r'TTT[ACGT](?=(.{' + str(guide_length) + '}))'
    for match in re.finditer(pattern, sequence):
        pam_seq = sequence[match.start():match.start()+4]
        guide_seq = match.group(1)
        start_pos = match.end()
        
        # Calculate GC content
        gc_content = (guide_seq.count('G') + guide_seq.count('C')) / len(guide_seq) * 100
        
        guides.append({
            'sequence': guide_seq,
            'pam': pam_seq,
            'position': start_pos + 1,  # 1-based position
            'strand': '+',
            'gc_content': round(gc_content, 1)
        })
    
    # Reverse strand - look for NAAA pattern and reverse complement
    rc_sequence = str(Seq(sequence).reverse_complement())
    pattern = r'[ACGT]AAA(?=(.{' + str(guide_length) + '}))'
    for match in re.finditer(pattern, rc_sequence):
        pam_seq = rc_sequence[match.start():match.start()+4]
        guide_seq = match.group(1)
        start_pos = len(sequence) - match.end() - guide_length
        
        # Calculate GC content
        gc_content = (guide_seq.count('G') + guide_seq.count('C')) / len(guide_seq) * 100
        
        guides.append({
            'sequence': guide_seq,
            'pam': pam_seq,
            'position': start_pos + 1,  # 1-based position
            'strand': '-',
            'gc_content': round(gc_content, 1)
        })
    
    return guides

def filter_guides(guides, min_gc=30, max_gc=70):
    """Filter guides based on GC content"""
    return [g for g in guides if min_gc <= g['gc_content'] <= max_gc]

def main():
    args = parse_arguments()
    
    # Read sequence from file if it's a path, otherwise use directly
    if os.path.exists(args.sequence):
        with open(args.sequence, 'r') as f:
            content = f.read()
            if '>' in content:  # FASTA format
                lines = content.strip().split('\n')
                sequence = ''.join(lines[1:])
            else:  # Raw sequence
                sequence = content.strip().replace('\n', '')
    else:
        sequence = args.sequence.strip().replace('\n', '')
    
    # Find guides based on enzyme
    if args.enzyme == 'Cas9':
        guides = find_cas9_guides(sequence, args.guide_length)
    elif args.enzyme == 'Cpf1':
        guides = find_cpf1_guides(sequence, args.guide_length)
    
    # Filter guides by GC content
    guides = filter_guides(guides)
    
    # Sort guides by position
    guides.sort(key=lambda x: x['position'])
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(guides, f, indent=2)
    
    # Create a DataFrame for pretty printing
    df = pd.DataFrame(guides)
    print(f"\nFound {len(guides)} potential guides for {args.enzyme}:")
    print(df.to_string(index=False))
    print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    main() 