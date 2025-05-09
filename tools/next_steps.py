#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Next Steps Module

This module provides recommendations for follow-up experiments, troubleshooting
suggestions, and analysis recommendations based on CRISPR editing outcomes.
"""

import os
import json
import sys
from typing import Dict, List, Any, Optional, Tuple, Union

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

# Troubleshooting guides for common CRISPR issues
TROUBLESHOOTING_GUIDES = {
    "low_editing_efficiency": {
        "issue": "Low Editing Efficiency",
        "description": "Editing efficiency (indel frequency) is below 20% in your target cells.",
        "potential_causes": [
            {"cause": "Poor guide RNA design", "likelihood": "High"},
            {"cause": "Inefficient delivery method", "likelihood": "High"},
            {"cause": "Cell type resistance to editing", "likelihood": "Medium"},
            {"cause": "Competing repair pathways", "likelihood": "Medium"},
            {"cause": "Chromatin accessibility issues", "likelihood": "Medium"}
        ],
        "solutions": [
            "Redesign guide RNA targeting a different site in the same region",
            "Optimize transfection/delivery protocol for your specific cell type",
            "Try a different delivery method (e.g., nucleofection instead of lipofection)",
            "Use RNP complex instead of plasmid-based delivery",
            "Confirm Cas9 expression in your cells using Western blot or GFP reporter",
            "Optimize Cas9:gRNA ratio",
            "Consider cell cycle synchronization (HDR works best in S/G2 phase)"
        ]
    },
    "high_off_target": {
        "issue": "High Off-Target Effects",
        "description": "Significant editing observed at predicted off-target sites.",
        "potential_causes": [
            {"cause": "Guide RNA with low specificity", "likelihood": "High"},
            {"cause": "Too high Cas9 concentration", "likelihood": "High"},
            {"cause": "Extended expression of Cas9 (plasmid delivery)", "likelihood": "Medium"}
        ],
        "solutions": [
            "Redesign guide with higher specificity score",
            "Use high-fidelity Cas9 variants (e.g., SpCas9-HF1, eSpCas9, HypaCas9)",
            "Switch to RNP delivery for transient Cas9 expression",
            "Reduce Cas9 concentration",
            "Use Cas9 nickase (paired guide RNAs) approach",
            "Consider alternative PAM Cas9 variants for greater targeting flexibility"
        ]
    },
    "no_editing": {
        "issue": "No Detectable Editing",
        "description": "No indels detected at the target site.",
        "potential_causes": [
            {"cause": "Failed delivery", "likelihood": "Very High"},
            {"cause": "Inactive guide RNA", "likelihood": "High"},
            {"cause": "Insufficient Cas9 expression", "likelihood": "High"},
            {"cause": "Inaccessible chromatin region", "likelihood": "Medium"},
            {"cause": "Detection method insensitivity", "likelihood": "Medium"}
        ],
        "solutions": [
            "Confirm transfection/delivery efficiency with reporter gene",
            "Verify Cas9 expression using Western blot or GFP reporter",
            "Test guide RNA activity using validated reporter assay",
            "Try multiple guides targeting the same region",
            "Use more sensitive detection method (NGS instead of T7E1)",
            "Check for mutations in PAM sequence or guide binding site in your cell line",
            "Verify guide RNA sequence and structure"
        ]
    },
    "low_hdr_efficiency": {
        "issue": "Low HDR Efficiency (for knock-in experiments)",
        "description": "Poor integration of donor template (<5% HDR efficiency).",
        "potential_causes": [
            {"cause": "Inefficient NHEJ inhibition", "likelihood": "High"},
            {"cause": "Suboptimal donor design", "likelihood": "High"},
            {"cause": "Distance between cut site and insertion site", "likelihood": "Medium"},
            {"cause": "Cell cycle issues (HDR is active mainly in S/G2)", "likelihood": "Medium"}
        ],
        "solutions": [
            "Optimize homology arm length (typically 500-1000bp each)",
            "Ensure cut site is within 10-30bp of insertion site",
            "Use HDR enhancers (e.g., RS-1, SCR7, or L755507)",
            "Synchronize cells in S/G2 phase",
            "Increase donor template concentration",
            "Try ssODN donors for small insertions (<50bp)",
            "Inhibit NHEJ pathway using small molecules (e.g., SCR7)"
        ]
    },
    "mixed_population": {
        "issue": "Heterogeneous Editing Results",
        "description": "Wide variety of indels or mosaic editing pattern.",
        "potential_causes": [
            {"cause": "Ongoing Cas9 activity after initial editing", "likelihood": "High"},
            {"cause": "Polyclonal cell population", "likelihood": "High"},
            {"cause": "Multiple DNA repair outcomes", "likelihood": "Medium"}
        ],
        "solutions": [
            "Use single-cell cloning to isolate and expand edited clones",
            "Switch to RNP delivery for more defined editing window",
            "Consider inducible Cas9 systems for temporal control",
            "Design guide RNAs that favor specific repair outcomes"
        ]
    },
    "base_editing_bystander": {
        "issue": "Bystander Edits in Base Editing",
        "description": "Unwanted edits of other bases within the editing window.",
        "potential_causes": [
            {"cause": "Wide editing window of base editor", "likelihood": "Very High"},
            {"cause": "Multiple target nucleotides in window", "likelihood": "High"}
        ],
        "solutions": [
            "Use newer generation base editors with narrow editing windows (e.g., YE1-BE4max)",
            "Redesign guide RNA to position target base optimally in the window",
            "Try alternative PAM variants to reposition editing window",
            "Consider prime editing for more precise edits",
            "Optimize the delivery amount of base editor to reduce off-targets"
        ]
    }
}

# Follow-up experiment templates
FOLLOWUP_EXPERIMENT_TEMPLATES = {
    "knockout_validation": {
        "title": "CRISPR Knockout Validation Protocol",
        "prerequisite": "Successful generation of indels at target site",
        "purpose": "To validate complete loss of protein function in edited cells",
        "methods": [
            {
                "name": "Western Blot",
                "description": "Detect absence of target protein",
                "requirements": "Specific antibody against target protein",
                "timeline": "2-3 days",
                "sensitivity": "Medium (may miss in-frame mutations that preserve epitope)"
            },
            {
                "name": "RT-qPCR",
                "description": "Measure changes in mRNA expression (e.g., nonsense-mediated decay)",
                "requirements": "Primers for target gene and reference gene",
                "timeline": "1-2 days",
                "sensitivity": "Medium (may miss mutations that don't affect transcript level)"
            },
            {
                "name": "Functional Assay",
                "description": "Test for loss of protein function",
                "requirements": "Cell-based assay specific to the protein function",
                "timeline": "Varies by assay",
                "sensitivity": "High (directly tests functional consequence)"
            },
            {
                "name": "Sanger Sequencing of Clones",
                "description": "Confirm frameshift mutations in isolated clones",
                "requirements": "Single-cell cloning capability, PCR primers flanking target site",
                "timeline": "2-3 weeks (including clone expansion)",
                "sensitivity": "High (directly confirms genotype)"
            }
        ],
        "considerations": [
            "Multiple functional validations provide stronger evidence than sequencing alone",
            "Some proteins have long half-lives; validation may need to be delayed to allow protein turnover",
            "Consider possible compensatory mechanisms that may mask phenotype",
            "For essential genes, check for hypomorphic alleles or compensatory mutations"
        ]
    },
    "knockin_validation": {
        "title": "CRISPR Knock-in Validation Protocol",
        "prerequisite": "Detection of HDR-mediated insertion at target site",
        "purpose": "To confirm precise and functional integration of the donor sequence",
        "methods": [
            {
                "name": "Junction PCR",
                "description": "PCR across the integration junctions (genomic-insert boundaries)",
                "requirements": "Primers spanning integration junctions (one in genome, one in insert)",
                "timeline": "1 day",
                "sensitivity": "Medium (confirms presence but not precision or zygosity)"
            },
            {
                "name": "Sequencing of Integration Site",
                "description": "Sanger or NGS sequencing across the entire modified region",
                "requirements": "PCR primers flanking the entire modified region",
                "timeline": "2-3 days",
                "sensitivity": "High (confirms precise sequence integration)"
            },
            {
                "name": "Expression Validation",
                "description": "Verify expression of the inserted sequence (for coding sequences)",
                "requirements": "Antibodies, RT-PCR primers, or functional assays specific to the insert",
                "timeline": "1-3 days",
                "sensitivity": "High (confirms functional expression)"
            },
            {
                "name": "Flow Cytometry",
                "description": "Quantify knock-in efficiency for fluorescent reporter insertions",
                "requirements": "Flow cytometer access, appropriate controls",
                "timeline": "1 day",
                "sensitivity": "High (for fluorescent reporters)"
            }
        ],
        "considerations": [
            "Confirm both 5' and 3' junctions to rule out partial integrations",
            "Check for additional random integrations of the donor template",
            "Verify proper expression/function of the inserted sequence",
            "Single-cell cloning is often necessary to obtain homogeneous cell lines"
        ]
    },
    "base_editing_validation": {
        "title": "Base Editing Validation Protocol",
        "prerequisite": "Delivery of base editor components to target cells",
        "purpose": "To confirm precise base conversion at target site and assess bystander edits",
        "methods": [
            {
                "name": "Sanger Sequencing + EditR Analysis",
                "description": "Sequence the target region and analyze chromatograms for mixed base calls",
                "requirements": "PCR primers flanking edit site, EditR software access",
                "timeline": "2-3 days",
                "sensitivity": "Medium (detection limit ~5-10% editing)"
            },
            {
                "name": "Next-Generation Sequencing",
                "description": "Deep sequencing of the target region for quantitative analysis",
                "requirements": "NGS access, library preparation reagents",
                "timeline": "1-2 weeks",
                "sensitivity": "Very high (detection limit <1% editing)"
            },
            {
                "name": "Restriction Digest Assay",
                "description": "If edit creates/destroys restriction site, digest PCR products to estimate editing",
                "requirements": "Appropriate restriction enzyme, PCR primers",
                "timeline": "1 day",
                "sensitivity": "Medium (semiquantitative)"
            },
            {
                "name": "Functional Validation",
                "description": "Assay for expected functional consequence of the base edit",
                "requirements": "Cell-based assay specific to the expected effect",
                "timeline": "Varies by assay",
                "sensitivity": "High for functional outcome"
            }
        ],
        "considerations": [
            "Always check for bystander edits within the editing window",
            "Consider off-target analysis at sites with high sequence similarity",
            "Single-cell cloning may be necessary to obtain cells with homogeneous edits",
            "RNA off-targeting is possible with some base editors - consider RNA sequencing"
        ]
    },
    "off_target_analysis": {
        "title": "CRISPR Off-Target Analysis Protocol",
        "prerequisite": "Successful on-target editing",
        "purpose": "To assess unintended editing at genomic sites similar to the target sequence",
        "methods": [
            {
                "name": "Targeted Amplicon Sequencing",
                "description": "PCR and sequence predicted off-target sites based on computational prediction",
                "requirements": "Primers for predicted off-target sites, NGS access",
                "timeline": "1-2 weeks",
                "sensitivity": "High for predicted sites"
            },
            {
                "name": "GUIDE-seq",
                "description": "Genome-wide unbiased detection of Cas9-induced double-strand breaks",
                "requirements": "Specialized reagents and expertise for GUIDE-seq protocol",
                "timeline": "2-3 weeks",
                "sensitivity": "High (genome-wide)"
            },
            {
                "name": "DISCOVER-seq",
                "description": "Maps DNA repair protein recruitment to DSB sites genome-wide",
                "requirements": "ChIP-seq expertise, antibodies against DNA repair factors (e.g., MRE11)",
                "timeline": "2-3 weeks",
                "sensitivity": "High (genome-wide)"
            },
            {
                "name": "Whole Genome Sequencing",
                "description": "Comprehensive analysis of all genomic changes",
                "requirements": "High-coverage WGS, bioinformatics expertise",
                "timeline": "3-4 weeks",
                "sensitivity": "Medium-high (depth-dependent)"
            }
        ],
        "considerations": [
            "Computational prediction alone is insufficient for safety-critical applications",
            "Unbiased methods are more comprehensive but also more expensive and complex",
            "Consider comparing edited cells to unedited parental cells",
            "Off-target analysis is especially important for therapeutic applications"
        ]
    }
}

# Decision support templates for common outcomes
DECISION_SUPPORT = {
    "knockout_results": [
        {
            "scenario": "High editing efficiency (>50% indels), mostly frameshift",
            "interpretation": "Successful editing with high likelihood of functional knockout",
            "recommended_next_steps": [
                "Validate protein loss by Western blot",
                "Isolate single-cell clones for pure knockout population",
                "Perform functional assays specific to the gene's role"
            ]
        },
        {
            "scenario": "Moderate editing efficiency (20-50% indels), mixed frameshift/in-frame",
            "interpretation": "Partially successful editing with heterogeneous population",
            "recommended_next_steps": [
                "Isolate single-cell clones and screen for frameshift mutations",
                "Consider redesigning guide for higher frameshift probability",
                "Optimize transfection/delivery for higher efficiency"
            ]
        },
        {
            "scenario": "Low editing efficiency (<20% indels)",
            "interpretation": "Suboptimal editing, likely inadequate for phenotypic studies",
            "recommended_next_steps": [
                "Optimize delivery method or conditions",
                "Try alternative guide RNAs targeting the same gene",
                "Consider using a different Cas9 variant",
                "For difficult targets, consider CRISPRi instead of knockout"
            ]
        },
        {
            "scenario": "Mostly in-frame mutations",
            "interpretation": "Editing occurred but may not disrupt protein function",
            "recommended_next_steps": [
                "Verify if protein function is affected despite in-frame mutations",
                "Redesign guide to target critical functional domains",
                "Consider using two guides simultaneously to create larger deletion"
            ]
        }
    ],
    "knockin_results": [
        {
            "scenario": "High HDR efficiency (>20% precise integration)",
            "interpretation": "Successful knock-in with good efficiency",
            "recommended_next_steps": [
                "Validate integration junctions by sequencing",
                "Confirm expression/function of the inserted sequence",
                "Isolate single-cell clones with correct integration"
            ]
        },
        {
            "scenario": "Low HDR efficiency (5-20% precise integration)",
            "interpretation": "Knock-in achieved but with suboptimal efficiency",
            "recommended_next_steps": [
                "Optimize HDR conditions (cell synchronization, HDR enhancers)",
                "Redesign donor template (optimize homology arm length)",
                "Isolate single-cell clones to obtain pure population"
            ]
        },
        {
            "scenario": "Very low HDR efficiency (<5% precise integration)",
            "interpretation": "Inefficient knock-in, improvements needed before proceeding",
            "recommended_next_steps": [
                "Verify cutting efficiency at target site",
                "Redesign donor and/or guide RNA",
                "Try alternative delivery methods (e.g., RNP + donor)",
                "Consider using selection markers in donor for enrichment"
            ]
        },
        {
            "scenario": "Off-target integrations detected",
            "interpretation": "Donor integrated at unintended locations",
            "recommended_next_steps": [
                "Perform whole-genome sequencing to map integration sites",
                "Isolate and screen clones for correct single-integration events",
                "Consider using more specific guides or high-fidelity Cas9"
            ]
        }
    ],
    "base_editing_results": [
        {
            "scenario": "High on-target base conversion (>50%) with minimal bystander edits",
            "interpretation": "Successful and precise base editing",
            "recommended_next_steps": [
                "Validate functional consequence of the edit",
                "Isolate single-cell clones with homogeneous edits",
                "Check for off-target editing at predicted sites"
            ]
        },
        {
            "scenario": "High on-target base conversion with significant bystander edits",
            "interpretation": "Base editing occurred but with undesired edits in the activity window",
            "recommended_next_steps": [
                "Try newer generation base editors with narrower editing windows",
                "Redesign guide to reposition editing window",
                "Screen clones for cells with desired edit but minimal bystanders"
            ]
        },
        {
            "scenario": "Low on-target base conversion (<30%)",
            "interpretation": "Suboptimal base editing efficiency",
            "recommended_next_steps": [
                "Optimize delivery of base editor components",
                "Try alternative PAM-variant base editors for better positioning",
                "Consider prime editing as an alternative for precise edits"
            ]
        }
    ]
}

def suggest_troubleshooting(editing_type: str, observed_issues: List[str]) -> Dict[str, Any]:
    """
    Suggest troubleshooting steps based on observed issues.
    
    Args:
        editing_type: Type of editing experiment (knockout, knockin, base_editing)
        observed_issues: List of observed issues (e.g., low_editing_efficiency)
        
    Returns:
        Dictionary with troubleshooting suggestions
    """
    result = {
        "editing_type": editing_type,
        "issues": [],
        "overall_recommendation": ""
    }
    
    # Find matching issues in the troubleshooting guide
    for issue in observed_issues:
        if issue in TROUBLESHOOTING_GUIDES:
            result["issues"].append({
                "issue": TROUBLESHOOTING_GUIDES[issue]["issue"],
                "description": TROUBLESHOOTING_GUIDES[issue]["description"],
                "potential_causes": TROUBLESHOOTING_GUIDES[issue]["potential_causes"],
                "solutions": TROUBLESHOOTING_GUIDES[issue]["solutions"]
            })
    
    # If no specific issues found, provide general guidance
    if not result["issues"]:
        general_issues = []
        
        if editing_type == "knockout":
            general_issues = ["low_editing_efficiency", "no_editing"]
        elif editing_type == "knockin":
            general_issues = ["low_hdr_efficiency", "mixed_population"]
        elif editing_type == "base_editing":
            general_issues = ["base_editing_bystander", "low_editing_efficiency"]
        
        for issue in general_issues:
            if issue in TROUBLESHOOTING_GUIDES:
                result["issues"].append({
                    "issue": TROUBLESHOOTING_GUIDES[issue]["issue"],
                    "description": TROUBLESHOOTING_GUIDES[issue]["description"],
                    "potential_causes": TROUBLESHOOTING_GUIDES[issue]["potential_causes"],
                    "solutions": TROUBLESHOOTING_GUIDES[issue]["solutions"]
                })
    
    # Generate an overall recommendation based on the issues
    if result["issues"]:
        result["overall_recommendation"] = "Focus first on addressing " + result["issues"][0]["issue"] + \
                                           " as it likely has the biggest impact on your experiment success."
    
    return result

def recommend_next_experiment(editing_type: str, current_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recommend the next logical experiment based on current results.
    
    Args:
        editing_type: Type of editing experiment (knockout, knockin, base_editing)
        current_results: Dictionary with current experimental results
        
    Returns:
        Dictionary with next experiment recommendations
    """
    # Map editing type to validation template
    validation_type = editing_type + "_validation"
    if validation_type not in FOLLOWUP_EXPERIMENT_TEMPLATES:
        validation_type = "knockout_validation"  # Default to knockout validation
    
    # Get the validation template
    validation_template = FOLLOWUP_EXPERIMENT_TEMPLATES[validation_type]
    
    # Add off-target analysis if appropriate
    include_off_target = False
    if editing_type == "knockout" and current_results.get("editing_efficiency", 0) > 30:
        include_off_target = True
    elif editing_type == "knockin" and current_results.get("hdr_efficiency", 0) > 10:
        include_off_target = True
    
    off_target_template = None
    if include_off_target:
        off_target_template = FOLLOWUP_EXPERIMENT_TEMPLATES.get("off_target_analysis")
    
    # Build the recommendation
    recommendation = {
        "editing_type": editing_type,
        "current_stage": "Initial editing completed",
        "validation_experiment": validation_template,
        "off_target_analysis": off_target_template,
        "prioritized_next_steps": []
    }
    
    # Prioritize next steps based on editing type and results
    if editing_type == "knockout":
        if current_results.get("editing_efficiency", 0) > 50:
            recommendation["prioritized_next_steps"] = [
                "Isolate single-cell clones to obtain pure populations",
                "Validate knockout at protein level using Western blot",
                "Perform functional assays specific to the gene of interest"
            ]
        else:
            recommendation["prioritized_next_steps"] = [
                "Optimize editing conditions to improve efficiency",
                "Try alternative guide RNAs for the same target",
                "Consider pooled validation if clonal isolation is not feasible"
            ]
    
    elif editing_type == "knockin":
        if current_results.get("hdr_efficiency", 0) > 20:
            recommendation["prioritized_next_steps"] = [
                "Validate precise integration by sequencing both junctions",
                "Confirm expression and function of the inserted sequence",
                "Isolate and expand clones with verified insertions"
            ]
        else:
            recommendation["prioritized_next_steps"] = [
                "Optimize HDR conditions (cell synchronization, HDR enhancers)",
                "Redesign donor with longer homology arms if using short donor",
                "Consider using selection markers for enrichment of edited cells"
            ]
    
    elif editing_type == "base_editing":
        if current_results.get("editing_efficiency", 0) > 30:
            recommendation["prioritized_next_steps"] = [
                "Sequence to confirm desired base conversion and check bystander edits",
                "Validate the functional consequence of the edit",
                "Isolate clones with clean edits (desired change, minimal bystanders)"
            ]
        else:
            recommendation["prioritized_next_steps"] = [
                "Optimize delivery of base editor components",
                "Try alternative PAM variants to reposition the editing window",
                "Consider alternative base editor variants for your target base"
            ]
    
    return recommendation

def analyze_results_decision_support(editing_type: str, results_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide decision support based on editing results.
    
    Args:
        editing_type: Type of editing experiment (knockout, knockin, base_editing)
        results_data: Dictionary with experimental results
        
    Returns:
        Dictionary with decision support
    """
    # Initialize response
    support = {
        "editing_type": editing_type,
        "interpretation": "",
        "decision_points": [],
        "recommended_path": ""
    }
    
    # Get the relevant decision support template
    template_key = editing_type + "_results"
    if template_key not in DECISION_SUPPORT:
        template_key = "knockout_results"  # Default to knockout
    
    decision_templates = DECISION_SUPPORT[template_key]
    
    # Match the current results to the most appropriate scenario
    best_match = None
    
    if editing_type == "knockout":
        editing_efficiency = results_data.get("editing_efficiency", 0)
        frameshift_percent = results_data.get("frameshift_percent", 0)
        
        if editing_efficiency > 50 and frameshift_percent > 70:
            scenario = "High editing efficiency (>50% indels), mostly frameshift"
        elif editing_efficiency > 20:
            scenario = "Moderate editing efficiency (20-50% indels), mixed frameshift/in-frame"
        elif frameshift_percent < 50 and editing_efficiency > 10:
            scenario = "Mostly in-frame mutations"
        else:
            scenario = "Low editing efficiency (<20% indels)"
        
        # Find the matching scenario
        for template in decision_templates:
            if template["scenario"] == scenario:
                best_match = template
                break
    
    elif editing_type == "knockin":
        hdr_efficiency = results_data.get("hdr_efficiency", 0)
        off_target_integration = results_data.get("off_target_integration", False)
        
        if off_target_integration:
            scenario = "Off-target integrations detected"
        elif hdr_efficiency > 20:
            scenario = "High HDR efficiency (>20% precise integration)"
        elif hdr_efficiency > 5:
            scenario = "Low HDR efficiency (5-20% precise integration)"
        else:
            scenario = "Very low HDR efficiency (<5% precise integration)"
        
        # Find the matching scenario
        for template in decision_templates:
            if template["scenario"] == scenario:
                best_match = template
                break
    
    elif editing_type == "base_editing":
        editing_efficiency = results_data.get("editing_efficiency", 0)
        bystander_edits = results_data.get("bystander_edits", False)
        
        if editing_efficiency > 50 and not bystander_edits:
            scenario = "High on-target base conversion (>50%) with minimal bystander edits"
        elif editing_efficiency > 30 and bystander_edits:
            scenario = "High on-target base conversion with significant bystander edits"
        else:
            scenario = "Low on-target base conversion (<30%)"
        
        # Find the matching scenario
        for template in decision_templates:
            if template["scenario"] == scenario:
                best_match = template
                break
    
    # If we found a match, use it for decision support
    if best_match:
        support["interpretation"] = best_match["interpretation"]
        support["recommended_path"] = best_match["recommended_next_steps"][0]  # Primary recommendation
        support["decision_points"] = [
            {
                "scenario": best_match["scenario"],
                "interpretation": best_match["interpretation"],
                "next_steps": best_match["recommended_next_steps"]
            }
        ]
    
    # Add other decision points for context
    for template in decision_templates:
        if template != best_match:
            support["decision_points"].append({
                "scenario": template["scenario"],
                "interpretation": template["interpretation"],
                "next_steps": template["recommended_next_steps"]
            })
    
    return support

def get_next_steps_recommendation(editing_type: str, 
                                 result_data: Dict[str, Any],
                                 issue_list: Optional[List[str]] = None) -> str:
    """
    Generate a comprehensive next steps recommendation using the LLM.
    
    Args:
        editing_type: Type of editing experiment (knockout, knockin, base_editing)
        result_data: Dictionary with experimental results
        issue_list: Optional list of observed issues
        
    Returns:
        LLM-generated recommendation as a string
    """
    # Get troubleshooting suggestions
    troubleshooting = suggest_troubleshooting(editing_type, issue_list or [])
    
    # Get next experiment recommendation
    next_experiment = recommend_next_experiment(editing_type, result_data)
    
    # Get decision support
    decision_support = analyze_results_decision_support(editing_type, result_data)
    
    # Create a prompt for the LLM
    prompt = f"""
    As a scientific advisor, provide a clear and actionable plan for the next steps in this CRISPR genome editing experiment.
    
    EXPERIMENT TYPE: {editing_type}
    
    CURRENT RESULTS:
    {json.dumps(result_data, indent=2)}
    
    TROUBLESHOOTING SUGGESTIONS:
    {json.dumps(troubleshooting, indent=2)}
    
    RECOMMENDED NEXT EXPERIMENTS:
    {json.dumps(next_experiment, indent=2)}
    
    DECISION SUPPORT:
    {json.dumps(decision_support, indent=2)}
    
    Please provide:
    1. A brief interpretation of the current results (1-2 sentences)
    2. The 3-4 most important next steps, prioritized by importance
    3. Specific suggestions for optimization if needed
    4. A timeline for these next steps
    
    Your recommendation should be practical, concise, and backed by the technical data provided.
    """
    
    # Call the LLM
    recommendation = query_llm(prompt)
    
    return recommendation

def generate_validation_protocol(editing_type: str, 
                               gene_info: Dict[str, Any], 
                               current_results: Dict[str, Any]) -> str:
    """
    Generate a detailed validation protocol for the specific experiment.
    
    Args:
        editing_type: Type of editing experiment (knockout, knockin, base_editing)
        gene_info: Dictionary with information about the target gene
        current_results: Dictionary with current experimental results
        
    Returns:
        LLM-generated protocol as a string
    """
    # Get the validation template
    validation_type = editing_type + "_validation"
    if validation_type not in FOLLOWUP_EXPERIMENT_TEMPLATES:
        validation_type = "knockout_validation"  # Default to knockout validation
    
    validation_template = FOLLOWUP_EXPERIMENT_TEMPLATES[validation_type]
    
    # Create a prompt for the LLM
    prompt = f"""
    Generate a detailed, experiment-specific validation protocol for a CRISPR {editing_type} experiment.
    
    TARGET GENE INFORMATION:
    {json.dumps(gene_info, indent=2)}
    
    CURRENT EDITING RESULTS:
    {json.dumps(current_results, indent=2)}
    
    VALIDATION TEMPLATE:
    {json.dumps(validation_template, indent=2)}
    
    Please create a customized validation protocol that includes:
    1. A clear title and purpose statement specific to this gene and editing type
    2. Materials needed (including gene-specific reagents like antibodies or primers)
    3. Step-by-step methods for the 2-3 most appropriate validation approaches
    4. Expected results and interpretation guidelines
    5. Estimated timeline and critical checkpoints
    
    Make your protocol scientifically rigorous but practical for a lab to implement.
    Focus on validation methods most suited to this specific gene and editing outcome.
    """
    
    # Call the LLM
    protocol = query_llm(prompt)
    
    return protocol

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='CRISPR Next Steps Advisor')
    parser.add_argument('--type', '-t', type=str, required=True,
                        choices=['knockout', 'knockin', 'base_editing'],
                        help='Type of CRISPR experiment')
    parser.add_argument('--results', '-r', type=str, required=True,
                        help='Path to JSON file with experiment results')
    parser.add_argument('--issues', '-i', type=str, nargs='+',
                        choices=['low_editing_efficiency', 'high_off_target', 'no_editing',
                                'low_hdr_efficiency', 'mixed_population', 'base_editing_bystander'],
                        help='List of issues observed (optional)')
    parser.add_argument('--gene', '-g', type=str,
                        help='Path to JSON file with gene information (optional)')
    parser.add_argument('--output', '-o', type=str,
                        help='Path to save recommendation in JSON format (optional)')
    parser.add_argument('--validation', '-v', action='store_true',
                        help='Generate a detailed validation protocol')
    
    args = parser.parse_args()
    
    # Load results data
    try:
        with open(args.results, 'r') as f:
            results_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading results file: {e}")
        sys.exit(1)
    
    # Load gene info if provided
    gene_info = {}
    if args.gene:
        try:
            with open(args.gene, 'r') as f:
                gene_info = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading gene info file: {e}")
    
    # Generate recommendation
    if args.validation:
        result = generate_validation_protocol(args.type, gene_info, results_data)
        print("\n=== VALIDATION PROTOCOL ===\n")
    else:
        result = get_next_steps_recommendation(args.type, results_data, args.issues)
        print("\n=== NEXT STEPS RECOMMENDATION ===\n")
    
    print(result)
    
    # Save to file if requested
    if args.output:
        output_data = {
            "experiment_type": args.type,
            "issues": args.issues,
            "recommendation": result
        }
        
        if args.validation:
            output_data["validation_protocol"] = result
        else:
            output_data["next_steps"] = result
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nOutput saved to {args.output}") 