#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Educational Context Module

This module provides scientifically accurate explanations of CRISPR concepts,
terminology, visualizations, and references to help researchers better
understand genome editing methodologies and results.
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

# CRISPR Terminology dictionary
CRISPR_TERMINOLOGY = {
    "CRISPR": {
        "term": "CRISPR",
        "full_name": "Clustered Regularly Interspaced Short Palindromic Repeats",
        "definition": "A family of DNA sequences found in prokaryotes that forms the basis for CRISPR-Cas genome editing technology.",
        "context": "Originally part of bacterial immune systems, CRISPR sequences and Cas proteins have been adapted as a revolutionary tool for precise DNA modification.",
        "related_terms": ["Cas9", "gRNA", "sgRNA", "tracrRNA", "crRNA"]
    },
    "Cas9": {
        "term": "Cas9",
        "full_name": "CRISPR associated protein 9",
        "definition": "An RNA-guided endonuclease (enzyme) that cuts DNA at specific locations determined by a guide RNA sequence.",
        "context": "The most commonly used Cas protein in genome editing. It creates double-strand breaks that, when repaired, can introduce mutations or allow insertion of new DNA sequences.",
        "related_terms": ["SpCas9", "SaCas9", "Cas12a", "Cas13", "dCas9"]
    },
    "gRNA": {
        "term": "gRNA",
        "full_name": "guide RNA",
        "definition": "RNA molecule that guides Cas9 to a specific DNA target sequence through complementary base pairing.",
        "context": "In CRISPR-Cas9 systems, the gRNA contains a sequence that matches the target DNA, allowing Cas9 to make precise cuts at specific genomic locations.",
        "related_terms": ["sgRNA", "tracrRNA", "crRNA", "spacer sequence"]
    },
    "PAM": {
        "term": "PAM",
        "full_name": "Protospacer Adjacent Motif",
        "definition": "A short DNA sequence (typically 2-6 base pairs) required for Cas9 binding, located adjacent to the target DNA sequence.",
        "context": "Different Cas proteins recognize different PAM sequences. For SpCas9, the most common PAM is NGG (where N is any nucleotide).",
        "related_terms": ["SpCas9 PAM", "SaCas9 PAM", "Cas12a PAM"]
    },
    "HDR": {
        "term": "HDR",
        "full_name": "Homology Directed Repair",
        "definition": "A cellular DNA repair mechanism that uses a homologous DNA template to repair double-strand breaks.",
        "context": "In CRISPR editing, HDR is exploited to introduce precise changes by providing a donor DNA template with desired modifications flanked by sequences matching those around the cut site.",
        "related_terms": ["NHEJ", "knock-in", "donor template", "homology arms"]
    },
    "NHEJ": {
        "term": "NHEJ",
        "full_name": "Non-Homologous End Joining",
        "definition": "A cellular DNA repair mechanism that directly reconnects broken DNA ends, often introducing small insertions or deletions.",
        "context": "NHEJ is the predominant repair pathway in most cells and is exploited in CRISPR knockout experiments to create frameshift mutations that disrupt gene function.",
        "related_terms": ["HDR", "indel", "knockout", "DSB repair"]
    },
    "Indel": {
        "term": "Indel",
        "full_name": "Insertion or Deletion",
        "definition": "Small insertions or deletions of nucleotides in DNA, often resulting from NHEJ repair of double-strand breaks.",
        "context": "Indels near the start of a gene's coding sequence often lead to frameshift mutations that create premature stop codons, resulting in gene knockout.",
        "related_terms": ["NHEJ", "frameshift", "knockout"]
    },
    "Base editing": {
        "term": "Base editing",
        "full_name": "CRISPR base editing",
        "definition": "A CRISPR technique that changes individual DNA bases without making double-strand breaks, using Cas9 fused to deaminase enzymes.",
        "context": "Allows precise C→T or A→G conversions (and their complements) at specific positions, useful for correcting point mutations or introducing specific amino acid changes.",
        "related_terms": ["CBE", "ABE", "deaminase", "nick", "prime editing"]
    },
    "Prime editing": {
        "term": "Prime editing",
        "full_name": "Prime editing",
        "definition": "A precise genome editing method using a Cas9 nickase fused to reverse transcriptase and a prime editing guide RNA (pegRNA).",
        "context": "Allows various DNA modifications including all possible base-to-base conversions, small insertions, and small deletions without requiring double-strand breaks or donor DNA templates.",
        "related_terms": ["pegRNA", "reverse transcriptase", "nickase", "base editing"]
    },
    "Off-target effects": {
        "term": "Off-target effects",
        "full_name": "Off-target effects",
        "definition": "Unintended edits made by CRISPR systems at genomic sites that are similar but not identical to the target sequence.",
        "context": "A major consideration in CRISPR experimental design. Guide RNA selection tools help minimize off-target effects by evaluating potential binding to similar sequences elsewhere in the genome.",
        "related_terms": ["specificity", "high-fidelity Cas9", "guide design"]
    },
    "Knockout": {
        "term": "Knockout",
        "full_name": "Gene knockout",
        "definition": "The complete inactivation of a gene's function, typically through frameshift mutations that disrupt the coding sequence.",
        "context": "Often achieved using CRISPR-Cas9 to create double-strand breaks that, when repaired by NHEJ, introduce indels that disrupt the gene's reading frame.",
        "related_terms": ["indel", "frameshift", "loss-of-function"]
    },
    "Knock-in": {
        "term": "Knock-in",
        "full_name": "Gene knock-in",
        "definition": "The insertion of a DNA sequence (e.g., a reporter gene, tag, or corrected sequence) at a specific genomic location.",
        "context": "Achieved through HDR following a CRISPR-induced cut, requiring a donor template with homology arms matching sequences flanking the cut site.",
        "related_terms": ["HDR", "homology arms", "donor template"]
    }
}

# More specialized CRISPR concepts
ADVANCED_CONCEPTS = {
    "CRISPR screening": {
        "concept": "CRISPR screening",
        "definition": "High-throughput approach using CRISPR libraries to simultaneously test thousands of genetic perturbations.",
        "applications": [
            "Identifying essential genes",
            "Drug target discovery",
            "Understanding genetic interactions",
            "Elucidating biological pathways"
        ],
        "types": [
            {"name": "Knockout screens", "approach": "Uses guide RNAs targeting coding regions to disrupt gene function"},
            {"name": "Activation screens (CRISPRa)", "approach": "Uses dCas9-activators to upregulate gene expression"},
            {"name": "Interference screens (CRISPRi)", "approach": "Uses dCas9-repressors to downregulate gene expression"}
        ],
        "considerations": [
            "Guide RNA library design and coverage",
            "Screen selection conditions",
            "Analysis of screen results",
            "Validation of hits"
        ]
    },
    "CRISPR tiling": {
        "concept": "CRISPR tiling",
        "definition": "Systematic targeting of multiple sites across a gene or genomic region using many guide RNAs.",
        "applications": [
            "Identifying functional domains",
            "Mapping regulatory elements",
            "Fine-mapping disease variants",
            "Optimizing gene editing outcomes"
        ],
        "approach": "Guide RNAs are designed at regular intervals across the region of interest to create a comprehensive 'tile' of targeted sites.",
        "analysis": "The phenotypic effect of each guide is measured, creating a functional map of the targeted region."
    },
    "Base editor types": {
        "concept": "Base editor types",
        "definition": "Different engineered variants of base editors that modify specific nucleotides.",
        "types": [
            {"name": "CBE (Cytosine Base Editors)", "action": "Convert C→T (or G→A on opposite strand)", "example": "BE4, evoCDA"},
            {"name": "ABE (Adenine Base Editors)", "action": "Convert A→G (or T→C on opposite strand)", "example": "ABE8e, ABEmax"},
            {"name": "Precision editors", "action": "Reduced bystander editing", "example": "YE1-BE4max"}
        ],
        "editing window": "Most base editors edit within a window of ~4-8 nucleotides from the PAM site",
        "considerations": [
            "PAM requirements",
            "Editing window width and position",
            "Bystander editing",
            "RNA off-targets"
        ]
    },
    "CRISPR delivery methods": {
        "concept": "CRISPR delivery methods",
        "definition": "Different approaches for introducing CRISPR components into cells or organisms.",
        "methods": [
            {"name": "Plasmid transfection", "applications": "Cell lines, easy-to-transfect cells", "considerations": "Longer expression, potential for genomic integration"},
            {"name": "RNP (ribonucleoprotein) delivery", "applications": "Primary cells, clinical applications", "considerations": "Transient, reduced off-targets, less toxicity"},
            {"name": "Viral vectors", "applications": "In vivo editing, hard-to-transfect cells", "considerations": "AAV has limited cargo capacity but good safety profile; lentivirus allows stable expression"},
            {"name": "Lipid nanoparticles", "applications": "In vivo delivery, clinical applications", "considerations": "Can be targeted to specific tissues, good safety profile"},
            {"name": "Physical methods", "applications": "Various cell types", "considerations": "Includes electroporation, microinjection, cell squeezing"}
        ],
        "selection factors": [
            "Cell/tissue type",
            "Editing efficiency requirements",
            "Transient vs. stable expression needs",
            "Safety considerations",
            "Scale of application"
        ]
    }
}

# Visualization explanations
VISUALIZATION_EXPLANATIONS = {
    "allele_frequency_plot": {
        "title": "Allele Frequency Plot",
        "description": "Shows the distribution and frequency of different alleles (sequence variants) resulting from CRISPR editing.",
        "interpretation": "Taller bars represent more common alleles. The wild-type (unedited) sequence is typically shown at the top, with edited sequences below. In successful editing, you should see significant frequencies of non-wild-type alleles.",
        "key_features": [
            "The y-axis shows the percentage of reads containing each allele",
            "Each row represents a different allele sequence",
            "Deletions are often marked with '-' characters or highlighted",
            "Insertions may be shown in a different color or with '+' notation"
        ]
    },
    "alignment_visualization": {
        "title": "Sequence Alignment Visualization",
        "description": "Displays the alignment of edited sequences against the reference (target) sequence.",
        "interpretation": "Shows exactly where edits occurred relative to the guide RNA binding site and cut site. Useful for identifying patterns in the types of edits produced.",
        "key_features": [
            "The reference sequence is shown at the top",
            "The guide RNA binding site is often highlighted",
            "The expected cut site (typically 3bp upstream of PAM) is marked",
            "Edited sequences are aligned below, with dots indicating matches to the reference"
        ]
    },
    "editing_efficiency_plot": {
        "title": "Editing Efficiency Plot",
        "description": "Summarizes the overall efficiency of genome editing by showing percentages of different modification types.",
        "interpretation": "Provides a quantitative measure of how effectively the target site was modified. In knockout experiments, high NHEJ (indel) percentages indicate success; in knock-in experiments, high HDR percentages are desired.",
        "key_features": [
            "Typically a pie or bar chart",
            "Shows proportion of reads with insertions, deletions, substitutions, and unmodified sequences",
            "May further categorize modifications (e.g., frameshift vs non-frameshift indels)"
        ]
    },
    "frameshift_analysis": {
        "title": "Frameshift Analysis",
        "description": "Categorizes indels based on whether they cause a frameshift in the coding sequence.",
        "interpretation": "Important for knockout experiments, as frameshift mutations typically disrupt protein function. The ideal result for knockouts is a high percentage of frameshift mutations.",
        "key_features": [
            "Categorizes indels by their length modulo 3 (e.g., 3n, 3n+1, 3n+2)",
            "3n indels maintain the reading frame (in-frame)",
            "3n+1 and 3n+2 indels shift the reading frame (frameshift)",
            "Often presented as a pie chart or bar graph"
        ]
    },
    "indel_size_distribution": {
        "title": "Indel Size Distribution",
        "description": "Shows the distribution of insertion and deletion sizes at the target site.",
        "interpretation": "Reveals patterns in the types of edits created. CRISPR-Cas9 typically creates small indels, often with a preference for specific deletion sizes based on microhomology near the cut site.",
        "key_features": [
            "X-axis shows indel size (negative numbers for deletions, positive for insertions)",
            "Y-axis shows frequency or percentage",
            "Common pattern includes predominant 1-10bp deletions",
            "Insertions are typically smaller and less frequent than deletions"
        ]
    },
    "nucleotide_percentage_plot": {
        "title": "Nucleotide Percentage Plot",
        "description": "Shows the percentage of each nucleotide (A, C, G, T) at each position across the target region.",
        "interpretation": "Useful for identifying positions with mixed editing outcomes. In base editing experiments, shows the efficiency of the targeted base conversion.",
        "key_features": [
            "X-axis represents position in the target sequence",
            "Y-axis shows percentage of each nucleotide",
            "Stacked bar or line format showing all four nucleotides",
            "Deviations from 100% of the reference base indicate editing"
        ]
    }
}

# Scientific references
SCIENTIFIC_REFERENCES = {
    "original_crispr_papers": [
        {
            "title": "A Programmable Dual-RNA–Guided DNA Endonuclease in Adaptive Bacterial Immunity",
            "authors": "Jinek M, Chylinski K, Fonfara I, Hauer M, Doudna JA, Charpentier E",
            "journal": "Science",
            "year": 2012,
            "doi": "10.1126/science.1225829",
            "description": "Landmark paper demonstrating that Cas9 can be programmed with a single guide RNA to cut specific DNA sequences."
        },
        {
            "title": "RNA-Guided Human Genome Engineering via Cas9",
            "authors": "Mali P, Yang L, Esvelt KM, Aach J, Guell M, DiCarlo JE, Norville JE, Church GM",
            "journal": "Science",
            "year": 2013,
            "doi": "10.1126/science.1232033",
            "description": "One of the first demonstrations of CRISPR-Cas9 genome editing in human cells."
        },
        {
            "title": "Multiplex Genome Engineering Using CRISPR/Cas Systems",
            "authors": "Cong L, Ran FA, Cox D, Lin S, Barretto R, Habib N, Hsu PD, Wu X, Jiang W, Marraffini LA, Zhang F",
            "journal": "Science",
            "year": 2013,
            "doi": "10.1126/science.1231143",
            "description": "Demonstrated CRISPR-Cas9 as an efficient tool for genome editing in mammalian cells, including multiplex editing."
        }
    ],
    "base_editing": [
        {
            "title": "Programmable editing of a target base in genomic DNA without double-stranded DNA cleavage",
            "authors": "Komor AC, Kim YB, Packer MS, Zuris JA, Liu DR",
            "journal": "Nature",
            "year": 2016,
            "doi": "10.1038/nature17946",
            "description": "Introduced cytosine base editors (CBEs) for C→T conversions without double-strand breaks."
        },
        {
            "title": "Programmable base editing of A•T to G•C in genomic DNA without DNA cleavage",
            "authors": "Gaudelli NM, Komor AC, Rees HA, Packer MS, Badran AH, Bryson DI, Liu DR",
            "journal": "Nature",
            "year": 2017,
            "doi": "10.1038/nature24644",
            "description": "Introduced adenine base editors (ABEs) for A→G conversions."
        }
    ],
    "prime_editing": [
        {
            "title": "Search-and-replace genome editing without double-strand breaks or donor DNA",
            "authors": "Anzalone AV, Randolph PB, Davis JR, Sousa AA, Koblan LW, Levy JM, Chen PJ, Wilson C, Newby GA, Raguram A, Liu DR",
            "journal": "Nature",
            "year": 2019,
            "doi": "10.1038/s41586-019-1711-4",
            "description": "Introduced prime editing, which combines Cas9 nickase with reverse transcriptase for precise editing without double-strand breaks."
        }
    ],
    "crispresso2": [
        {
            "title": "CRISPResso2 provides accurate and rapid genome editing sequence analysis",
            "authors": "Clement K, Rees H, Canver MC, Gehrke JM, Farouni R, Hsu JY, Cole MA, Liu DR, Joung JK, Pinello L",
            "journal": "Nature Biotechnology",
            "year": 2019,
            "doi": "10.1038/s41587-019-0032-3",
            "description": "Describes the CRISPResso2 software for analysis of genome editing outcomes from sequencing data."
        }
    ]
}

def get_term_definition(term: str, detailed: bool = False) -> Dict[str, Any]:
    """
    Get the definition and context for a CRISPR-related term.
    
    Args:
        term: The term to look up
        detailed: Whether to include related terms and additional context
        
    Returns:
        Dictionary with term information
    """
    # Normalize the term for lookup
    term_normalized = term.lower()
    
    # Check direct matches first
    for key, info in CRISPR_TERMINOLOGY.items():
        if key.lower() == term_normalized:
            if detailed:
                return info
            else:
                return {
                    "term": info["term"],
                    "definition": info["definition"]
                }
    
    # Check partial matches in term and full name
    matches = []
    for key, info in CRISPR_TERMINOLOGY.items():
        if term_normalized in key.lower() or term_normalized in info["full_name"].lower():
            matches.append(info)
    
    if matches:
        if detailed:
            return matches[0]
        else:
            return {
                "term": matches[0]["term"],
                "definition": matches[0]["definition"]
            }
    
    # If still not found, check related terms
    for key, info in CRISPR_TERMINOLOGY.items():
        for related in info.get("related_terms", []):
            if term_normalized == related.lower():
                if detailed:
                    related_info = info.copy()
                    related_info["note"] = f"This term is related to {info['term']}"
                    return related_info
                else:
                    return {
                        "term": related,
                        "note": f"Related to {info['term']}",
                        "context": f"See {info['term']} for more information"
                    }
    
    # Not found
    return {
        "term": term,
        "definition": "Term not found in our CRISPR terminology database."
    }

def get_advanced_concept(concept: str) -> Dict[str, Any]:
    """
    Get information about an advanced CRISPR concept.
    
    Args:
        concept: The concept to look up
        
    Returns:
        Dictionary with concept information
    """
    # Normalize the concept for lookup
    concept_normalized = concept.lower()
    
    # Check direct matches first
    for key, info in ADVANCED_CONCEPTS.items():
        if key.lower() == concept_normalized:
            return info
    
    # Check partial matches in concept name
    matches = []
    for key, info in ADVANCED_CONCEPTS.items():
        if concept_normalized in key.lower():
            matches.append(info)
    
    if matches:
        return matches[0]
    
    # Not found - provide a list of available concepts
    return {
        "concept": concept,
        "definition": "Concept not found in our advanced CRISPR concepts database.",
        "available_concepts": list(ADVANCED_CONCEPTS.keys())
    }

def explain_visualization(visualization_type: str) -> Dict[str, Any]:
    """
    Get explanation for a CRISPR result visualization.
    
    Args:
        visualization_type: The type of visualization to explain
        
    Returns:
        Dictionary with visualization explanation
    """
    # Normalize the visualization type for lookup
    viz_normalized = visualization_type.lower()
    
    # Check for exact or partial matches
    for key, info in VISUALIZATION_EXPLANATIONS.items():
        if key.lower() == viz_normalized or viz_normalized in key.lower():
            return info
        if viz_normalized in info["title"].lower():
            return info
    
    # Handle common alternative names
    alternatives = {
        "pie chart": "editing_efficiency_plot",
        "pie": "editing_efficiency_plot",
        "alignment": "alignment_visualization",
        "frequencies": "allele_frequency_plot",
        "alleles": "allele_frequency_plot",
        "frame": "frameshift_analysis",
        "indels": "indel_size_distribution",
        "nucleotide": "nucleotide_percentage_plot",
        "base": "nucleotide_percentage_plot"
    }
    
    for alt, key in alternatives.items():
        if alt in viz_normalized:
            return VISUALIZATION_EXPLANATIONS[key]
    
    # Not found - provide a list of available visualizations
    return {
        "title": "Visualization explanation not found",
        "description": "The requested visualization type was not found in our database.",
        "available_visualizations": [info["title"] for key, info in VISUALIZATION_EXPLANATIONS.items()]
    }

def get_scientific_references(topic: str = None) -> List[Dict[str, Any]]:
    """
    Get scientific references related to CRISPR, optionally filtered by topic.
    
    Args:
        topic: Optional topic to filter references
        
    Returns:
        List of reference dictionaries
    """
    if not topic:
        # Return a selection of important references from each category
        result = []
        for category, refs in SCIENTIFIC_REFERENCES.items():
            result.extend(refs[:1])  # Take the first reference from each category
        return result
    
    # Normalize the topic for lookup
    topic_normalized = topic.lower()
    
    # Check direct category matches
    for category, refs in SCIENTIFIC_REFERENCES.items():
        if topic_normalized in category.lower():
            return refs
    
    # Check for matches in paper titles and descriptions
    matches = []
    for category, refs in SCIENTIFIC_REFERENCES.items():
        for ref in refs:
            if (topic_normalized in ref["title"].lower() or 
                topic_normalized in ref.get("description", "").lower()):
                matches.append(ref)
    
    if matches:
        return matches
    
    # Not found - provide a list of available reference categories
    return [{
        "note": f"No references found for topic '{topic}'",
        "available_categories": list(SCIENTIFIC_REFERENCES.keys())
    }]

def get_educational_context(query: str, context_type: str = "general") -> str:
    """
    Generate educational context information using the LLM based on a user query.
    
    Args:
        query: The user's question or topic
        context_type: Type of context to provide (general, term, visualization, etc.)
        
    Returns:
        Educational explanation as a string
    """
    # Prepare information based on the context type
    info = {}
    
    if context_type == "term":
        info = get_term_definition(query, detailed=True)
    elif context_type == "concept":
        info = get_advanced_concept(query)
    elif context_type == "visualization":
        info = explain_visualization(query)
    elif context_type == "reference":
        info = {"references": get_scientific_references(query)}
    
    # Create a prompt for the LLM
    if info:
        prompt = f"""
        Provide a clear, scientifically accurate explanation about the following CRISPR-related topic:
        
        USER QUERY: {query}
        
        CONTEXT TYPE: {context_type}
        
        AVAILABLE INFORMATION:
        {json.dumps(info, indent=2)}
        
        Please respond in a helpful, educational manner suitable for a researcher or student.
        Focus on providing practical understanding that would help someone working with CRISPR technology.
        Keep the explanation concise (3-4 paragraphs maximum) but comprehensive.
        """
    else:
        # General prompt if no specific information is available
        prompt = f"""
        Provide a clear, scientifically accurate explanation about the following CRISPR-related topic:
        
        USER QUERY: {query}
        
        Please respond in a helpful, educational manner suitable for a researcher or student.
        Focus on providing practical understanding that would help someone working with CRISPR technology.
        Include:
        1. A clear definition or explanation of the topic
        2. Its relevance to CRISPR genome editing
        3. Practical considerations or applications
        
        Keep the explanation concise (3-4 paragraphs maximum) but comprehensive.
        """
    
    # Call the LLM
    explanation = query_llm(prompt)
    
    return explanation

def find_crispr_terms_in_text(text: str) -> List[Dict[str, str]]:
    """
    Find CRISPR-related terms in a block of text and provide definitions.
    
    Args:
        text: Text to analyze for CRISPR terminology
        
    Returns:
        List of dictionaries with terms and definitions
    """
    terms = []
    
    # Get all terms to search for
    all_terms = list(CRISPR_TERMINOLOGY.keys())
    for info in CRISPR_TERMINOLOGY.values():
        all_terms.append(info["full_name"])
        all_terms.extend(info.get("related_terms", []))
    
    # Remove duplicates and sort by length (descending) to catch longer terms first
    all_terms = sorted(set(all_terms), key=len, reverse=True)
    
    # Find terms in the text
    found_terms = set()
    for term in all_terms:
        # Create a regex pattern that matches the term as a whole word
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_terms.add(term)
    
    # Get definitions for found terms
    for term in found_terms:
        definition = get_term_definition(term)
        terms.append(definition)
    
    return terms

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='CRISPR Educational Context Provider')
    parser.add_argument('--query', '-q', type=str, help='Query or term to explain')
    parser.add_argument('--type', '-t', type=str, choices=['term', 'concept', 'visualization', 'reference', 'general'],
                        default='general', help='Type of educational context to provide')
    parser.add_argument('--analyze', '-a', type=str, help='Text to analyze for CRISPR terminology')
    parser.add_argument('--list', '-l', type=str, choices=['terms', 'concepts', 'visualizations', 'references'],
                        help='List available items of the specified type')
    
    args = parser.parse_args()
    
    if args.list:
        if args.list == 'terms':
            print("\nAvailable CRISPR Terms:")
            for term in sorted(CRISPR_TERMINOLOGY.keys()):
                print(f"- {term}")
        elif args.list == 'concepts':
            print("\nAvailable Advanced Concepts:")
            for concept in sorted(ADVANCED_CONCEPTS.keys()):
                print(f"- {concept}")
        elif args.list == 'visualizations':
            print("\nAvailable Visualization Explanations:")
            for viz, info in VISUALIZATION_EXPLANATIONS.items():
                print(f"- {info['title']} ({viz})")
        elif args.list == 'references':
            print("\nAvailable Reference Categories:")
            for category in SCIENTIFIC_REFERENCES.keys():
                print(f"- {category}")
    
    elif args.analyze:
        terms = find_crispr_terms_in_text(args.analyze)
        if terms:
            print("\nCRISPR Terms Found:")
            for term_info in terms:
                print(f"\n- {term_info['term']}:")
                print(f"  {term_info['definition']}")
        else:
            print("\nNo CRISPR-specific terms found in the text.")
    
    elif args.query:
        result = get_educational_context(args.query, args.type)
        print(f"\n=== Educational Context: {args.query} ===\n")
        print(result)
    
    else:
        parser.print_help() 