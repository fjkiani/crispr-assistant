#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Experiment Advisor Module

This module provides scientifically-validated experimental design advice for CRISPR genome editing.
It helps researchers plan experiments based on guide selection, experimental goals, and best practices.
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

# Template experiments for different editing goals
EXPERIMENT_TEMPLATES = {
    "knockout": {
        "title": "Gene Knockout Protocol",
        "description": "Protocol for disrupting gene function through frameshift indels or early stop codons",
        "applications": ["Loss-of-function studies", "Essential gene identification", "Functional genomics"],
        "cas_variants": ["SpCas9", "SaCas9"],
        "guide_selection_criteria": [
            "Target early exons",
            "Target functionally critical domains",
            "Avoid alternative splicing sites when complete knockout is desired"
        ],
        "delivery_methods": [
            {"method": "Plasmid transfection", "cell_types": "Adherent cell lines", "considerations": "Lower efficiency but stable expression"},
            {"method": "RNP complex", "cell_types": "Primary cells, sensitive cell types", "considerations": "Higher efficiency, less off-targets, transient"},
            {"method": "Lentiviral delivery", "cell_types": "Hard-to-transfect cells, in vivo", "considerations": "Integration, long-term expression"}
        ],
        "validation_methods": [
            {"method": "T7 Endonuclease I assay", "timeline": "3-4 days", "description": "Detects mismatches in heteroduplex DNA"},
            {"method": "Sanger sequencing + TIDE analysis", "timeline": "1 week", "description": "Sequence trace decomposition"},
            {"method": "Next-gen sequencing", "timeline": "1-2 weeks", "description": "Most accurate, can be analyzed with CRISPResso2"},
            {"method": "Western blot", "timeline": "3-4 days", "description": "Confirms protein loss"},
            {"method": "RT-qPCR", "timeline": "2-3 days", "description": "Checks mRNA expression"}
        ],
        "typical_timeline": [
            {"stage": "Guide RNA design", "duration": "1-2 days"},
            {"stage": "Cloning (if using plasmid)", "duration": "3-7 days"},
            {"stage": "Transfection/Electroporation", "duration": "1 day"},
            {"stage": "Cell recovery", "duration": "2-3 days"},
            {"stage": "Initial validation", "duration": "3-4 days"},
            {"stage": "Clone isolation (optional)", "duration": "2-3 weeks"},
            {"stage": "Final validation", "duration": "1 week"}
        ],
        "reagents": [
            {"name": "Cas9 protein or plasmid", "considerations": "Ensure nuclear localization signal is present"},
            {"name": "Guide RNA or sgRNA plasmid", "considerations": "Chemically synthesized or in vitro transcribed"},
            {"name": "Transfection reagent", "considerations": "Optimize for cell type"},
            {"name": "Genomic DNA extraction kit", "considerations": "High purity for validation"}
        ]
    },
    "knock-in": {
        "title": "Targeted Gene Knock-in Protocol",
        "description": "Protocol for precise insertion of DNA sequences via HDR pathway",
        "applications": ["Reporter tagging", "Point mutation introduction", "Gene correction"],
        "cas_variants": ["SpCas9", "High-fidelity variants (eSpCas9, SpCas9-HF1, HypaCas9)"],
        "guide_selection_criteria": [
            "Cut site should be within 10-30bp of insertion site",
            "High on-target efficiency",
            "Minimal off-targets due to HDR sensitvity"
        ],
        "delivery_methods": [
            {"method": "RNP complex + donor DNA", "cell_types": "Most cell types", "considerations": "Higher HDR efficiency, less toxicity"},
            {"method": "Plasmid delivery", "cell_types": "Easily transfected cells", "considerations": "Include donor template"}
        ],
        "validation_methods": [
            {"method": "PCR across insertion junction", "timeline": "1-2 days", "description": "Confirms successful insertion"},
            {"method": "Restriction digest (if site created/removed)", "timeline": "1 day", "description": "Quick screen for successful edits"},
            {"method": "Sanger sequencing", "timeline": "2-3 days", "description": "Confirms precise sequence insertion"},
            {"method": "Flow cytometry (for fluorescent reporters)", "timeline": "1 day", "description": "Quantifies knock-in efficiency"},
            {"method": "Next-gen sequencing", "timeline": "1-2 weeks", "description": "Comprehensive analysis of edited sites"}
        ],
        "typical_timeline": [
            {"stage": "Guide RNA design", "duration": "1-2 days"},
            {"stage": "Donor template design and synthesis", "duration": "1-2 weeks"},
            {"stage": "Transfection/Electroporation", "duration": "1 day"},
            {"stage": "Cell recovery", "duration": "2-3 days"},
            {"stage": "HDR enhancer treatment (optional)", "duration": "1-2 days"},
            {"stage": "Initial validation", "duration": "3-4 days"},
            {"stage": "Clone isolation", "duration": "2-3 weeks"},
            {"stage": "Final validation", "duration": "1 week"}
        ],
        "reagents": [
            {"name": "Cas9 protein", "considerations": "RNP complex recommended for HDR"},
            {"name": "Guide RNA", "considerations": "Chemical synthesis recommended"},
            {"name": "Donor DNA template", "considerations": "Homology arms typically 500-1000bp each"},
            {"name": "HDR enhancers", "considerations": "Small molecules like RS-1, SCR7 or cell cycle synchronizers"},
            {"name": "Transfection reagent", "considerations": "Nucleofection often preferred for HDR"}
        ],
        "optimization_tips": [
            "Synchronize cells in G2/M phase to increase HDR frequency",
            "Consider using Cas9 nickase for larger insertions",
            "Inhibit NHEJ pathway to favor HDR (e.g., with SCR7)",
            "Use ssODN donors for small insertions (<50bp)"
        ]
    },
    "base-editing": {
        "title": "Base Editing Protocol",
        "description": "Protocol for precise base substitutions without double-strand breaks",
        "applications": ["Point mutation introduction/correction", "SNP studies", "Disease modeling"],
        "cas_variants": [
            {"name": "CBE (Cytosine Base Editor)", "conversions": "C→T conversions (or G→A on opposite strand)"},
            {"name": "ABE (Adenine Base Editor)", "conversions": "A→G conversions (or T→C on opposite strand)"},
            {"name": "Precision editors", "conversions": "New generation editors with reduced bystander edits (e.g., YE1-BE4max)"}
        ],
        "guide_selection_criteria": [
            "Target base must be within editing window (typically positions 4-8 for CBEs, 4-7 for ABEs)",
            "Minimize potential bystander edits in the editing window",
            "Consider PAM positioning carefully for optimal target base positioning"
        ],
        "delivery_methods": [
            {"method": "Plasmid transfection", "cell_types": "Easily transfected cells", "considerations": "Lower efficiency due to large construct size"},
            {"method": "mRNA transfection", "cell_types": "Primary cells, sensitive cells", "considerations": "Higher efficiency, transient expression"},
            {"method": "Lentiviral delivery", "cell_types": "Hard-to-transfect cells, in vivo", "considerations": "Integration, long-term expression"}
        ],
        "validation_methods": [
            {"method": "Sanger sequencing + EditR analysis", "timeline": "2-3 days", "description": "Sequence trace analysis specific for base editing"},
            {"method": "Restriction digest (if site created/removed)", "timeline": "1 day", "description": "Quick screen for successful edits"},
            {"method": "Next-gen sequencing", "timeline": "1-2 weeks", "description": "Comprehensive analysis with custom pipeline (not standard CRISPResso)"},
            {"method": "RT-qPCR (for RNA changes)", "timeline": "2-3 days", "description": "Confirms RNA-level changes"},
            {"method": "Protein functional assays", "timeline": "Variable", "description": "Confirms effect of amino acid substitution"}
        ],
        "typical_timeline": [
            {"stage": "Guide RNA design for base editing", "duration": "1-2 days"},
            {"stage": "Cloning (for plasmid delivery)", "duration": "3-7 days"},
            {"stage": "Transfection", "duration": "1 day"},
            {"stage": "Cell recovery", "duration": "3-5 days (longer than for Cas9)"},
            {"stage": "Initial validation", "duration": "3-4 days"},
            {"stage": "Clone isolation", "duration": "2-3 weeks"},
            {"stage": "Final validation", "duration": "1-2 weeks"}
        ],
        "reagents": [
            {"name": "Base editor plasmid or mRNA", "considerations": "Large constructs, may need optimization"},
            {"name": "Guide RNA", "considerations": "Target positioning is critical for base editing window"},
            {"name": "Transfection reagent", "considerations": "May need higher amounts due to construct size"}
        ],
        "optimization_tips": [
            "Use newest generation base editors with increased efficiency and specificity",
            "Consider RNA off-targeting for certain base editors",
            "Extend culture time for higher editing efficiency"
        ]
    }
}

# Primer design parameters
PRIMER_DESIGN_PARAMS = {
    "pcr_validation": {
        "length_range": (18, 25),
        "gc_content": (40, 60),
        "tm_range": (58, 62),
        "amplicon_size": (400, 800),
        "considerations": [
            "For knock-in validation, one primer should bind outside the homology arm",
            "For indel detection, amplicon should be centered on expected cut site",
            "Avoid primer binding to the guide RNA target site which may be mutated"
        ]
    },
    "rt_pcr": {
        "length_range": (18, 22),
        "gc_content": (40, 60),
        "tm_range": (58, 60),
        "amplicon_size": (80, 150),
        "considerations": [
            "Design primers across exon junctions when possible",
            "For knockout validation, design primers spanning the targeted exon",
            "Include established reference gene primers"
        ]
    }
}

def suggest_experiment_workflow(
    experiment_type: str,
    guide_info: Optional[Dict[str, Any]] = None,
    target_gene: Optional[str] = None,
    cell_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a customized experimental workflow based on the experiment type and guide information.
    
    Args:
        experiment_type: The type of experiment (knockout, knock-in, base-editing)
        guide_info: Optional dictionary containing information about the selected guide
        target_gene: Optional name of the target gene
        cell_type: Optional cell type for the experiment
        
    Returns:
        Dictionary with customized experimental workflow
    """
    if experiment_type not in EXPERIMENT_TEMPLATES:
        return {
            "error": f"Unknown experiment type: {experiment_type}. Available types: {', '.join(EXPERIMENT_TEMPLATES.keys())}"
        }
    
    # Get the template for this experiment type
    template = EXPERIMENT_TEMPLATES[experiment_type]
    
    # Customize the workflow based on the provided information
    customized = {
        "experiment_type": experiment_type,
        "target_gene": target_gene,
        "cell_type": cell_type,
        "title": template["title"],
        "description": template["description"],
        "timeline": template["typical_timeline"],
        "validation_methods": template["validation_methods"],
        "reagents": template["reagents"]
    }
    
    # Customize delivery method recommendation based on cell type if provided
    if cell_type:
        for delivery in template["delivery_methods"]:
            if cell_type.lower() in delivery["cell_types"].lower():
                customized["recommended_delivery"] = delivery
                break
        if "recommended_delivery" not in customized:
            customized["recommended_delivery"] = template["delivery_methods"][0]  # Default to first method
    
    # Add guide-specific recommendations if a guide is provided
    if guide_info:
        guide_seq = guide_info.get("seq", "")
        customized["guide_sequence"] = guide_seq
        
        # Add any guide-specific notes
        guide_notes = []
        
        # Look at GC content for delivery recommendations
        if guide_seq:
            gc_content = (guide_seq.count('G') + guide_seq.count('C')) / len(guide_seq) if guide_seq else 0
            if gc_content < 0.4:
                guide_notes.append("Guide has low GC content, may need higher concentrations for efficient targeting.")
            elif gc_content > 0.6:
                guide_notes.append("Guide has high GC content, consider checking for secondary structures.")
        
        customized["guide_notes"] = guide_notes
    
    return customized

def design_pcr_primers(
    target_sequence: str,
    experiment_type: str,
    cut_site_index: Optional[int] = None,
    insertion_site: Optional[int] = None
) -> Dict[str, Any]:
    """
    Design PCR primers for experiment validation based on the target sequence and experiment type.
    
    Args:
        target_sequence: The target DNA sequence
        experiment_type: The type of experiment (knockout, knock-in, base-editing)
        cut_site_index: Optional index of the cut site in the target sequence
        insertion_site: Optional index of insertion site for knock-in experiments
        
    Returns:
        Dictionary with primer designs and recommendations
    """
    if experiment_type not in EXPERIMENT_TEMPLATES:
        return {"error": f"Unknown experiment type: {experiment_type}"}
    
    # Simple primer design logic - in a real implementation, would use a more sophisticated algorithm
    # or integrate with primer3 or similar tool
    
    # For demonstration, we'll implement a basic approach
    # In practice, this would be much more sophisticated
    
    # Default to middle of sequence if no cut site specified
    if cut_site_index is None:
        cut_site_index = len(target_sequence) // 2
    
    # For knockout validation
    if experiment_type == "knockout":
        # Design primers flanking the cut site by ~200bp on each side
        left_start = max(0, cut_site_index - 250)
        right_start = min(len(target_sequence) - 25, cut_site_index + 150)
        
        left_primer_region = target_sequence[left_start:left_start + 200]
        right_primer_region = target_sequence[right_start:right_start + 200]
        
        # Very simplified - would use proper primer design algorithm in practice
        left_primer = left_primer_region[:20]
        right_primer = reverse_complement(right_primer_region[:20])
        
        amplicon_size = right_start - left_start + 20
        
        return {
            "experiment_type": experiment_type,
            "validation_method": "PCR amplification across cut site",
            "primers": {
                "forward": left_primer,
                "reverse": right_primer,
                "amplicon_size": amplicon_size
            },
            "notes": [
                f"Primers designed to amplify region spanning the cut site at position {cut_site_index}",
                "After editing, PCR products can be analyzed with T7E1 assay or sequencing",
                "Expected to see mixed PCR products after successful editing"
            ]
        }
    
    # For knock-in validation
    elif experiment_type == "knock-in" and insertion_site is not None:
        # Design primers - one inside insert, one outside homology arm
        # This is simplified - real design would be more complex
        left_start = max(0, insertion_site - 400)
        
        left_primer_region = target_sequence[left_start:left_start + 200]
        # Right primer would be in the inserted sequence - not available here
        
        left_primer = left_primer_region[:20]
        right_primer = "DESIGN_BASED_ON_INSERT"  # Placeholder
        
        return {
            "experiment_type": experiment_type,
            "validation_method": "PCR across insertion junction",
            "primers": {
                "forward": left_primer,
                "reverse": right_primer,
                "notes": "Right primer should be designed based on the insertion sequence"
            },
            "notes": [
                "One primer binds genomic DNA outside the homology arm",
                "The other primer binds the inserted sequence",
                "PCR product will only form if insertion is successful"
            ]
        }
    
    # For base editing validation
    elif experiment_type == "base-editing":
        # Center the amplicon on the expected edit site
        left_start = max(0, cut_site_index - 200)
        right_start = min(len(target_sequence) - 25, cut_site_index + 150)
        
        left_primer_region = target_sequence[left_start:left_start + 200]
        right_primer_region = target_sequence[right_start:right_start + 200]
        
        left_primer = left_primer_region[:20]
        right_primer = reverse_complement(right_primer_region[:20])
        
        amplicon_size = right_start - left_start + 20
        
        return {
            "experiment_type": experiment_type,
            "validation_method": "PCR for sequence validation",
            "primers": {
                "forward": left_primer,
                "reverse": right_primer,
                "amplicon_size": amplicon_size
            },
            "notes": [
                f"Primers designed to amplify region containing the base editing target site",
                "PCR products should be Sanger sequenced and analyzed with EditR or similar tool",
                "Look for clean base substitution without indels"
            ]
        }
    
    return {"error": "Could not design primers with the given parameters"}

def reverse_complement(seq: str) -> str:
    """Return the reverse complement of a DNA sequence"""
    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    return ''.join(complement.get(base, base) for base in reversed(seq.upper()))

def estimate_experiment_timeline(
    experiment_type: str,
    has_cloning: bool = True,
    clone_isolation: bool = True,
    extensive_validation: bool = False
) -> Dict[str, Any]:
    """
    Estimate a timeline for the experiment based on the type and options.
    
    Args:
        experiment_type: The type of experiment (knockout, knock-in, base-editing)
        has_cloning: Whether cloning is needed (False for RNP delivery)
        clone_isolation: Whether single cell clones will be isolated
        extensive_validation: Whether extensive validation (sequencing, functional) is planned
        
    Returns:
        Dictionary with timeline estimates
    """
    if experiment_type not in EXPERIMENT_TEMPLATES:
        return {"error": f"Unknown experiment type: {experiment_type}"}
    
    template = EXPERIMENT_TEMPLATES[experiment_type]
    timeline = []
    
    # Always include guide design
    timeline.append({
        "stage": "Guide RNA design and validation",
        "duration": "1-2 days",
        "notes": "Using tools like CHOPCHOP for design and validation"
    })
    
    # Cloning if needed
    if has_cloning:
        timeline.append({
            "stage": "Cloning and plasmid preparation",
            "duration": "3-7 days",
            "notes": "Guide RNA cloning into expression vector"
        })
    else:
        timeline.append({
            "stage": "Guide RNA and Cas9 preparation",
            "duration": "1-2 days",
            "notes": "RNP complex formation for direct delivery"
        })
    
    # For knock-in, add donor preparation
    if experiment_type == "knock-in":
        timeline.append({
            "stage": "Donor template design and preparation",
            "duration": "7-14 days",
            "notes": "Design and synthesis of donor with homology arms"
        })
    
    # Delivery
    timeline.append({
        "stage": "Transfection/delivery",
        "duration": "1 day",
        "notes": "Delivery of CRISPR components to cells"
    })
    
    # Cell recovery
    recovery_time = "3-5 days" if experiment_type == "base-editing" else "2-3 days"
    timeline.append({
        "stage": "Cell recovery",
        "duration": recovery_time,
        "notes": "Allow cells to recover and editing to occur"
    })
    
    # Initial validation
    timeline.append({
        "stage": "Initial validation",
        "duration": "3-4 days",
        "notes": "Preliminary assessment of editing efficiency"
    })
    
    # Clone isolation if needed
    if clone_isolation:
        timeline.append({
            "stage": "Single cell cloning and expansion",
            "duration": "2-3 weeks",
            "notes": "Isolation and expansion of edited clones"
        })
    
    # Final validation
    validation_time = "1-2 weeks" if extensive_validation else "3-5 days"
    validation_notes = "Comprehensive validation including sequencing and functional assays" if extensive_validation else "Basic validation of editing outcomes"
    timeline.append({
        "stage": "Final validation",
        "duration": validation_time,
        "notes": validation_notes
    })
    
    # Calculate total time (using minimum estimates for simplicity)
    total_days = 0
    for stage in timeline:
        # Parse the minimum days from ranges like "3-5 days" or "2-3 weeks"
        duration = stage["duration"]
        if "weeks" in duration:
            days = int(duration.split("-")[0]) * 7
        else:
            days = int(duration.split("-")[0])
        total_days += days
    
    return {
        "experiment_type": experiment_type,
        "detailed_timeline": timeline,
        "estimated_total_days": total_days,
        "estimated_total_weeks": round(total_days / 7, 1)
    }

def generate_protocol(
    experiment_type: str,
    guide_info: Optional[Dict[str, Any]] = None,
    target_gene: Optional[str] = None,
    cell_type: Optional[str] = None,
    custom_options: Optional[Dict[str, Any]] = None,
    provide_therapeutic_context: bool = False
) -> str:
    """
    Generate a customized experimental protocol using the LLM.
    
    Args:
        experiment_type: The type of experiment (knockout, knock-in, base-editing)
        guide_info: Optional dictionary containing information about the selected guide
        target_gene: Optional name of the target gene
        cell_type: Optional cell type for the experiment
        custom_options: Optional dictionary with custom experimental parameters
        provide_therapeutic_context (bool): Whether to include therapeutic context.
        
    Returns:
        String containing the generated protocol
    """
    if experiment_type not in EXPERIMENT_TEMPLATES:
        return f"Error: Unknown experiment type: {experiment_type}"
    
    # Get the basic workflow
    workflow = suggest_experiment_workflow(experiment_type, guide_info, target_gene, cell_type)
    
    # Get timeline estimate
    has_cloning = custom_options.get("delivery_method", "") != "RNP" if custom_options else True
    clone_isolation = custom_options.get("clone_isolation", True) if custom_options else True
    extensive_validation = custom_options.get("extensive_validation", False) if custom_options else False
    
    timeline = estimate_experiment_timeline(
        experiment_type, 
        has_cloning=has_cloning,
        clone_isolation=clone_isolation,
        extensive_validation=extensive_validation
    )
    
    # Design primers if we have a sequence
    primers = None
    if guide_info and "context_seq" in guide_info:
        cut_site = len(guide_info["context_seq"]) // 2 if "cut_site" not in guide_info else guide_info["cut_site"]
        primers = design_pcr_primers(
            guide_info["context_seq"],
            experiment_type,
            cut_site_index=cut_site
        )
    
    # Create a prompt for the LLM
    prompt = f"""
    Generate a detailed, scientifically accurate experimental protocol for a CRISPR {experiment_type} experiment.
    
    EXPERIMENT DETAILS:
    Type: {experiment_type}
    Target Gene: {target_gene if target_gene else "Not specified"}
    Cell Type: {cell_type if cell_type else "Not specified"}
    
    GUIDE RNA INFORMATION:
    {json.dumps(guide_info, indent=2) if guide_info else "Not provided"}
    
    WORKFLOW INFORMATION:
    {json.dumps(workflow, indent=2)}
    
    TIMELINE ESTIMATE:
    {json.dumps(timeline, indent=2)}
    
    {"PRIMER DESIGN:" if primers else ""}
    {json.dumps(primers, indent=2) if primers else ""}
    
    CUSTOM OPTIONS:
    {json.dumps(custom_options, indent=2) if custom_options else "None specified"}
    
    Please provide a detailed protocol that includes:
    1. A clear title and brief overview of the experiment for general research.
    2. Materials and reagents needed for general research.
    3. Step-by-step procedure with specific details and tips for general research.
    4. Expected results and how to interpret them in a research context.
    5. Troubleshooting advice for common issues in research experiments.
    """
    
    if provide_therapeutic_context:
        prompt += f"""

    ### Therapeutic Development Considerations:
    As a CRISPR therapeutic development expert, please add a distinct section or integrate comments covering the following for this {experiment_type} experiment targeting {target_gene if target_gene else 'the specified gene'} in {cell_type if cell_type else 'a relevant therapeutic cell model'}:

    1.  **Delivery Vector Choices & Implications (Task 7.4.1):**
        *   Discuss common delivery vector choices (e.g., AAV, LNP, electroporation of RNP, lentivirus) suitable for therapeutic applications of a {experiment_type} strategy in {cell_type if cell_type else 'relevant primary cells/in vivo models'}.
        *   For each relevant delivery option, briefly outline its implications regarding efficiency, safety (e.g., integration risk, immunogenicity), payload capacity, and potential tropism, especially in the context of targeting {target_gene if target_gene else 'this gene'}.

    2.  **Crucial Controls for Therapeutic Validation (Task 7.4.2):**
        *   Beyond standard research controls, what *additional* control experiments are essential when developing this towards a therapeutic product?
        *   Specifically detail controls for:
            *   **On-target Efficacy & Function:** Validating robust on-target editing and the desired functional consequence (e.g., protein knockout, specific base correction) in a therapeutically relevant cell model (e.g., patient-derived cells, primary human cells if applicable).
            *   **Comprehensive Off-Target Analysis:** Emphasize the need for unbiased, genome-wide off-target nomination methods (e.g., GUIDE-seq, CIRCLE-seq, digenome-seq, or others) and subsequent validation of top candidates. Discuss the importance of this for safety assessment.
            *   **Safety/Potency Assays:** Suggest any specific safety assays (e.g., cell viability, transformation potential if applicable) or potency assays (demonstrating the therapeutic mechanism) that would be critical for this particular gene target and {experiment_type} approach.

    Ensure these therapeutic considerations are clearly delineated from the general research protocol.
    """
    
    prompt += "\nFormat the overall protocol in a clear, professional manner that would be suitable for a laboratory notebook or methods section, with clear headings for each part.\n"
    
    # Call the LLM
    protocol = query_llm(prompt)
    
    return protocol

def recommend_reagents(experiment_type: str, cell_type: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
    """
    Recommend specific reagents for the experiment.
    
    Args:
        experiment_type: The type of experiment (knockout, knock-in, base-editing)
        cell_type: Optional cell type for the experiment
        
    Returns:
        Dictionary with reagent recommendations
    """
    if experiment_type not in EXPERIMENT_TEMPLATES:
        return {"error": f"Unknown experiment type: {experiment_type}"}
    
    # Base reagents from the template
    template = EXPERIMENT_TEMPLATES[experiment_type]
    base_reagents = template["reagents"]
    
    # Specific product recommendations (examples)
    # In a real implementation, this would be a more extensive database
    specific_reagents = {
        "knockout": {
            "Cas9 protein": [
                {"name": "Cas9 Nuclease, S. pyogenes", "supplier": "NEB", "cat_no": "M0386"},
                {"name": "TrueCut Cas9 Protein v2", "supplier": "Thermo Fisher", "cat_no": "A36498"}
            ],
            "Guide RNA synthesis": [
                {"name": "EnGen sgRNA Synthesis Kit", "supplier": "NEB", "cat_no": "E3322"},
                {"name": "GeneArt Precision gRNA Synthesis Kit", "supplier": "Thermo Fisher", "cat_no": "A29377"}
            ],
            "Transfection reagents": [
                {"name": "Lipofectamine CRISPRMAX", "supplier": "Thermo Fisher", "cat_no": "CMAX00003", "cell_types": "Adherent lines"},
                {"name": "Nucleofector Kit", "supplier": "Lonza", "cat_no": "Various", "cell_types": "Primary, suspension cells"}
            ],
            "Validation": [
                {"name": "T7 Endonuclease I", "supplier": "NEB", "cat_no": "M0302"},
                {"name": "GeneArt Genomic Cleavage Detection Kit", "supplier": "Thermo Fisher", "cat_no": "A24372"}
            ]
        },
        "knock-in": {
            "Cas9 protein": [
                {"name": "Cas9 Nuclease, S. pyogenes", "supplier": "NEB", "cat_no": "M0386"},
                {"name": "Alt-R S.p. HiFi Cas9 Nuclease", "supplier": "IDT", "cat_no": "1081060"}
            ],
            "HDR enhancers": [
                {"name": "HDR Enhancer", "supplier": "IDT", "cat_no": "1081072"},
                {"name": "Alt-R HDR Enhancer", "supplier": "IDT", "cat_no": "10007921"}
            ],
            "Donor DNA": [
                {"name": "Ultramer DNA Oligos (for small inserts)", "supplier": "IDT", "cat_no": "Custom"},
                {"name": "gBlocks Gene Fragments", "supplier": "IDT", "cat_no": "Custom", "note": "For larger inserts"}
            ]
        },
        "base-editing": {
            "Base editors": [
                {"name": "pCMV-ABE8e", "supplier": "Addgene", "cat_no": "138489", "type": "Adenine base editor"},
                {"name": "pCMV-BE4max", "supplier": "Addgene", "cat_no": "112093", "type": "Cytosine base editor"}
            ],
            "Guide RNA": [
                {"name": "Alt-R CRISPR-Cas9 crRNA", "supplier": "IDT", "cat_no": "Custom"},
                {"name": "Alt-R CRISPR-Cas9 tracrRNA", "supplier": "IDT", "cat_no": "1072532"}
            ]
        }
    }
    
    # Cell-type specific recommendations
    cell_type_reagents = {}
    if cell_type:
        cell_type_lower = cell_type.lower()
        if "primary" in cell_type_lower or "hard-to-transfect" in cell_type_lower:
            cell_type_reagents = {
                "Delivery method": [
                    {"name": "Nucleofection", "supplier": "Lonza", "note": "Best for primary cells"},
                    {"name": "Lentiviral delivery", "note": "For stable integration in hard-to-transfect cells"}
                ]
            }
        elif "suspension" in cell_type_lower:
            cell_type_reagents = {
                "Delivery method": [
                    {"name": "Nucleofection", "supplier": "Lonza", "note": "Best for suspension cells"},
                    {"name": "Electroporation", "supplier": "BioRad", "note": "Alternative for suspension cells"}
                ]
            }
    
    return {
        "experiment_type": experiment_type,
        "base_reagents": base_reagents,
        "specific_recommendations": specific_reagents.get(experiment_type, {}),
        "cell_type_specific": cell_type_reagents
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='CRISPR Experiment Advisor')
    parser.add_argument('--experiment', '-e', type=str, required=True, 
                        choices=['knockout', 'knock-in', 'base-editing'],
                        help='Type of experiment')
    parser.add_argument('--guide', '-g', type=str, help='Path to guide RNA JSON file')
    parser.add_argument('--gene', '-t', type=str, help='Target gene symbol')
    parser.add_argument('--cell', '-c', type=str, help='Cell type')
    parser.add_argument('--output', '-o', type=str, help='Output file for the protocol')
    parser.add_argument('--timeline', action='store_true', help='Generate timeline estimate')
    parser.add_argument('--reagents', action='store_true', help='Generate reagent recommendations')
    parser.add_argument('--protocol', action='store_true', help='Generate full experimental protocol')
    
    args = parser.parse_args()
    
    # Load guide info if provided
    guide_info = None
    if args.guide:
        try:
            with open(args.guide, 'r') as f:
                guide_data = json.load(f)
                # Extract guide info - either a single guide or the first from a list
                if isinstance(guide_data, list):
                    guide_info = guide_data[0] if guide_data else None
                elif isinstance(guide_data, dict) and "guides" in guide_data:
                    guide_info = guide_data["guides"][0] if guide_data["guides"] else None
                else:
                    guide_info = guide_data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading guide file: {e}")
    
    # Generate requested outputs
    if args.timeline:
        timeline = estimate_experiment_timeline(args.experiment)
        print("\n=== EXPERIMENT TIMELINE ===")
        print(json.dumps(timeline, indent=2))
    
    if args.reagents:
        reagents = recommend_reagents(args.experiment, args.cell)
        print("\n=== RECOMMENDED REAGENTS ===")
        print(json.dumps(reagents, indent=2))
    
    if args.protocol:
        protocol = generate_protocol(
            args.experiment,
            guide_info=guide_info,
            target_gene=args.gene,
            cell_type=args.cell
        )
        print("\n=== EXPERIMENTAL PROTOCOL ===")
        print(protocol)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(protocol)
            print(f"\nProtocol saved to {args.output}")
    
    # If no specific output requested, show workflow
    if not any([args.timeline, args.reagents, args.protocol]):
        workflow = suggest_experiment_workflow(
            args.experiment,
            guide_info=guide_info,
            target_gene=args.gene,
            cell_type=args.cell
        )
        print("\n=== EXPERIMENT WORKFLOW ===")
        print(json.dumps(workflow, indent=2)) 