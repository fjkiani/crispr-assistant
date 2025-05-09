#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Guide Interpreter Module

This module provides scientifically-validated, contextual explanations for guide RNA results.
It helps researchers understand their guide selection, scores, and makes recommendations
based on the experimental goals.
"""

import os
import json
import sys
from typing import Dict, List, Any, Optional, Tuple, Union
import re

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import LLM API
try:
    from tools.llm_api import query_llm
except ImportError:
    # Create a stub if llm_api is not available
    def query_llm(prompt, provider="gemini"):
        print(f"Warning: LLM API not available. Would have sent prompt: {prompt[:100]}...")
        return "LLM explanation not available. Please ensure tools/llm_api.py is accessible."

# Scientific information about guide properties
GUIDE_PROPERTY_INFO = {
    "gc_content": {
        "description": "The percentage of G and C nucleotides in the guide sequence",
        "optimal_range": "40-60%",
        "impact": "Guides with GC content between 40-60% tend to have better efficiency. Too low GC content may reduce binding strength, while too high can lead to secondary structures or off-target effects."
    },
    "self_complementarity": {
        "description": "The tendency of the guide sequence to fold back on itself forming secondary structures",
        "impact": "Guides with high self-complementarity may form hairpin structures that reduce guide efficiency."
    },
    "poly_t": {
        "description": "Presence of 4 or more consecutive T nucleotides",
        "impact": "Poly-T sequences can act as transcription termination signals for RNA polymerase III, reducing guide expression from common vector systems."
    },
    "position": {
        "description": "The location of the target site within the gene",
        "impact": "Targeting the start of a coding sequence or functional domains often leads to more effective gene knockout. For knock-in applications, targeting close to the desired insertion site is preferred."
    },
    "terminal_g": {
        "description": "Presence of G nucleotide at position 20 (right before the PAM)",
        "impact": "A G before the PAM can increase editing efficiency for many Cas9 variants."
    },
    "pam_context": {
        "description": "The sequence context around the PAM site",
        "impact": "Some PAM-adjacent nucleotides can influence Cas9 binding and cutting efficiency."
    },
    "off_targets": {
        "description": "Potential binding sites elsewhere in the genome with similar sequences",
        "impact": "Guides with fewer off-target sites are more specific and reduce the risk of unintended edits."
    }
}

# Known functional domains for common genes
GENE_DOMAINS = {
    "TP53": [
        {"name": "Transactivation Domain", "start": 1, "end": 42, "function": "Activates transcription factors"},
        {"name": "DNA Binding Domain", "start": 102, "end": 292, "function": "Binds to specific DNA sequences"},
        {"name": "Tetramerization Domain", "start": 325, "end": 356, "function": "Required for tetramer formation"},
        {"name": "Regulatory Domain", "start": 363, "end": 393, "function": "Regulates activity"}
    ],
    "BRCA1": [
        {"name": "RING Domain", "start": 8, "end": 96, "function": "Binds BARD1, has E3 ubiquitin ligase activity"},
        {"name": "BRCT Domains", "start": 1642, "end": 1855, "function": "Phosphopeptide binding, critical for tumor suppression"}
    ],
    "BRAF": [
        {"name": "RBD (Ras Binding Domain)", "start": 156, "end": 227, "function": "Interacts with Ras proteins"},
        {"name": "Kinase Domain", "start": 457, "end": 717, "function": "Catalyzes phosphorylation"},
        {"name": "V600 Hotspot", "start": 600, "end": 600, "function": "Common mutation site (V600E) in cancer"}
    ]
}

def explain_guide_score(guide: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a guide and explain the factors contributing to its score.
    
    Args:
        guide: A dictionary containing guide information (seq, score, etc.)
        
    Returns:
        Dictionary with explanations of score components
    """
    seq = guide.get("seq", "")
    score = guide.get("score", 0)
    pam = guide.get("pam", "")
    
    # Calculate properties
    gc_content = (seq.count('G') + seq.count('C')) / len(seq) if seq else 0
    has_poly_t = 'TTTT' in seq
    ends_with_g = seq.endswith('G') if seq else False
    
    explanation = {
        "score": score,
        "sequence": seq,
        "pam": pam,
        "properties": {
            "gc_content": {
                "value": f"{gc_content:.1%}",
                "optimal": 0.4 <= gc_content <= 0.6,
                "explanation": f"{'Optimal' if 0.4 <= gc_content <= 0.6 else 'Suboptimal'} GC content. {GUIDE_PROPERTY_INFO['gc_content']['impact']}"
            },
            "poly_t": {
                "value": "Present" if has_poly_t else "Absent",
                "optimal": not has_poly_t,
                "explanation": f"{'Contains' if has_poly_t else 'Does not contain'} poly-T stretches. {GUIDE_PROPERTY_INFO['poly_t']['impact']}"
            },
            "terminal_g": {
                "value": "Present" if ends_with_g else "Absent",
                "optimal": ends_with_g,
                "explanation": f"{'Has' if ends_with_g else 'Lacks'} G at position {len(seq)}. {GUIDE_PROPERTY_INFO['terminal_g']['impact']}"
            }
        },
        "summary": f"Guide {seq} has a score of {score:.2f}, with {gc_content:.1%} GC content, {'contains' if has_poly_t else 'no'} poly-T stretches, and {'has' if ends_with_g else 'lacks'} a G nucleotide before the PAM."
    }
    
    return explanation

def locate_guide_in_gene(guide_seq: str, gene_symbol: str) -> Optional[Dict[str, Any]]:
    """
    Locate a guide sequence within a known gene and identify nearby functional domains.
    
    Args:
        guide_seq: The guide RNA sequence
        gene_symbol: The gene symbol (e.g., TP53)
        
    Returns:
        Dictionary with location information or None if not found
    """
    # Look up the gene sequence - first check COMMON_GENES
    gene_seq = None
    
    # Try to import from simple_guide_finder
    try:
        from simple_guide_finder import COMMON_GENES
        if gene_symbol.upper() in COMMON_GENES:
            gene_seq = COMMON_GENES[gene_symbol.upper()]
    except ImportError:
        # If simple_guide_finder isn't available, try to look in gene_database
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               "gene_database", f"{gene_symbol}.fasta")
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                content = f.read()
                # Parse FASTA and remove header
                gene_seq = ''.join([line.strip() for line in content.split('\n') if not line.startswith('>')])
    
    if not gene_seq:
        return None
    
    # Find the guide in the gene sequence
    position = gene_seq.find(guide_seq)
    if position == -1:
        # Try the reverse complement
        rc_guide = reverse_complement(guide_seq)
        position = gene_seq.find(rc_guide)
        strand = "-" if position != -1 else "unknown"
    else:
        strand = "+"
    
    if position == -1:
        return None
    
    # Convert position to amino acid coordinates (approximate)
    aa_position_start = position // 3
    aa_position_end = (position + len(guide_seq) - 1) // 3
    
    # Check if the guide is near any known domains
    nearby_domains = []
    if gene_symbol.upper() in GENE_DOMAINS:
        for domain in GENE_DOMAINS[gene_symbol.upper()]:
            # Check if the guide target overlaps with this domain
            if (aa_position_start <= domain["end"] and aa_position_end >= domain["start"]):
                nearby_domains.append({
                    "name": domain["name"],
                    "function": domain["function"],
                    "distance": 0,  # Direct overlap
                    "relation": "overlaps"
                })
            elif abs(aa_position_start - domain["end"]) <= 10 or abs(aa_position_end - domain["start"]) <= 10:
                nearby_domains.append({
                    "name": domain["name"],
                    "function": domain["function"],
                    "distance": min(abs(aa_position_start - domain["end"]), abs(aa_position_end - domain["start"])),
                    "relation": "near"
                })
    
    return {
        "gene": gene_symbol,
        "nucleotide_position": position,
        "amino_acid_position": aa_position_start,
        "strand": strand,
        "nearby_domains": nearby_domains
    }

def reverse_complement(seq: str) -> str:
    """Return the reverse complement of a DNA sequence"""
    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    return ''.join(complement.get(base, base) for base in reversed(seq.upper()))

def compare_guides(guides: List[Dict[str, Any]], gene_symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Compare multiple guides and provide recommendations.
    
    Args:
        guides: List of guide dictionaries
        gene_symbol: Optional gene symbol for context
        
    Returns:
        Dictionary with comparison and recommendations
    """
    if not guides:
        return {"error": "No guides provided for comparison"}
    
    explained_guides = [explain_guide_score(guide) for guide in guides]
    
    # Add gene location context if available
    if gene_symbol:
        for i, guide in enumerate(explained_guides):
            location = locate_guide_in_gene(guide["sequence"], gene_symbol)
            if location:
                explained_guides[i]["location"] = location
    
    # Find best guides for different criteria
    best_gc = max(explained_guides, key=lambda g: 1 if g["properties"]["gc_content"]["optimal"] else 0)
    no_poly_t = [g for g in explained_guides if g["properties"]["poly_t"]["optimal"]]
    with_terminal_g = [g for g in explained_guides if g["properties"]["terminal_g"]["optimal"]]
    
    # Check for guides targeting important domains
    domain_targeting = []
    for guide in explained_guides:
        if "location" in guide and guide["location"]["nearby_domains"]:
            for domain in guide["location"]["nearby_domains"]:
                if domain["relation"] == "overlaps":
                    domain_targeting.append({
                        "guide": guide["sequence"],
                        "domain": domain["name"],
                        "function": domain["function"]
                    })
    
    # Generate recommendations
    recommendations = []
    if domain_targeting:
        recommendations.append({
            "type": "domain_targeting",
            "message": f"For gene knockout, consider guides that target functional domains: {', '.join(d['guide'] for d in domain_targeting[:2])}"
        })
    
    if with_terminal_g and best_gc["properties"]["gc_content"]["optimal"]:
        optimal_guides = [g for g in with_terminal_g if g["properties"]["gc_content"]["optimal"]]
        if optimal_guides:
            recommendations.append({
                "type": "overall_efficiency",
                "message": f"For highest editing efficiency, consider guides with optimal GC content and a G before the PAM: {', '.join(g['sequence'] for g in optimal_guides[:2])}"
            })
    
    return {
        "guides": explained_guides,
        "best_by_criteria": {
            "gc_content": best_gc["sequence"] if best_gc["properties"]["gc_content"]["optimal"] else None,
            "no_poly_t": [g["sequence"] for g in no_poly_t[:3]],
            "terminal_g": [g["sequence"] for g in with_terminal_g[:3]]
        },
        "domain_targeting": domain_targeting,
        "recommendations": recommendations
    }

def generate_llm_explanation(guides: List[Dict[str, Any]], gene_symbol: Optional[str] = None, 
                            experiment_type: Optional[str] = None) -> str:
    """
    Generate a natural language explanation of guide RNAs using an LLM.
    
    Args:
        guides: List of guide dictionaries
        gene_symbol: Optional gene symbol
        experiment_type: Optional experiment type (e.g., 'knockout', 'knock-in', 'base-editing')
        
    Returns:
        A natural language explanation
    """
    # Prepare the data for the LLM
    comparison = compare_guides(guides, gene_symbol)
    
    # Create a prompt for the LLM
    prompt = f"""
    I need to explain CRISPR guide RNA selection results to a researcher in clear, scientifically accurate but accessible language.

    TARGET GENE: {gene_symbol if gene_symbol else "Unspecified"}
    EXPERIMENT TYPE: {experiment_type if experiment_type else "General genome editing"}
    
    TOP GUIDES:
    {json.dumps([{"sequence": g["seq"], "pam": g.get("pam", ""), "score": g.get("score", 0)} for g in guides[:5]], indent=2)}
    
    ANALYSIS:
    {json.dumps(comparison, indent=2)}
    
    Please provide a 3-4 paragraph explanation that:
    1. Briefly explains what makes a good guide RNA (focus on GC content, position in gene, absence of poly-T, etc.)
    2. Highlights the strengths of the top guides
    3. Makes recommendations based on the specific experiment type
    4. Avoids overly technical jargon but maintains scientific accuracy
    
    Keep your explanation concise and focused on the practical aspects of guide selection.
    """
    
    # Call the LLM
    explanation = query_llm(prompt)
    
    return explanation

def add_context_to_guide_results(top_guides_file: str, gene_symbol: Optional[str] = None,
                               experiment_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Load guide RNA results from a file and add contextual explanations.
    
    Args:
        top_guides_file: Path to a JSON file containing guide RNA results
        gene_symbol: Optional gene symbol
        experiment_type: Optional experiment type
        
    Returns:
        Dictionary with guides and explanations
    """
    # Load the guides
    if not os.path.exists(top_guides_file):
        return {"error": f"File not found: {top_guides_file}"}
    
    try:
        with open(top_guides_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON file: {top_guides_file}"}
    
    # Extract guides from the data
    guides = []
    if "guides" in data:
        guides = data["guides"]
    else:
        # If it's a direct list
        guides = data if isinstance(data, list) else []
    
    if not guides:
        return {"error": "No guides found in the provided file"}
    
    # Add explanations
    comparison = compare_guides(guides, gene_symbol)
    llm_explanation = generate_llm_explanation(guides, gene_symbol, experiment_type)
    
    return {
        "guides": guides,
        "analysis": comparison,
        "explanation": llm_explanation,
        "gene_symbol": gene_symbol,
        "experiment_type": experiment_type
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Guide RNA Interpreter')
    parser.add_argument('--file', '-f', type=str, required=True, help='Path to a JSON file containing guide RNA results')
    parser.add_argument('--gene', '-g', type=str, help='Gene symbol (e.g., TP53)')
    parser.add_argument('--experiment', '-e', type=str, choices=['knockout', 'knock-in', 'base-editing'], 
                        help='Experiment type')
    parser.add_argument('--output', '-o', type=str, help='Output file for the explanation (JSON)')
    
    args = parser.parse_args()
    
    result = add_context_to_guide_results(args.file, args.gene, args.experiment)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    print(f"\n=== Guide RNA Analysis for {args.gene or 'Unknown Gene'} ===\n")
    print(result["explanation"])
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nFull analysis saved to {args.output}") 