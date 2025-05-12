#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced Results Interpreter Module

This module provides advanced interpretation of CRISPR genome editing results,
with context-aware analysis, specialized visualizations, and comparative metrics
across different editing approaches (NHEJ, HDR, base editing).
"""

import os
import json
import sys
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from io import BytesIO
import base64

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

# Constants for result interpretation
NHEJ_EFFICIENCY_THRESHOLDS = {
    "excellent": 80,
    "good": 60,
    "moderate": 40,
    "low": 20,
    "very_low": 5
}

HDR_EFFICIENCY_THRESHOLDS = {
    "excellent": 40,
    "good": 25,
    "moderate": 15,
    "low": 5,
    "very_low": 1
}

BASE_EDITING_THRESHOLDS = {
    "excellent": 70,
    "good": 50,
    "moderate": 30,
    "low": 15,
    "very_low": 5
}

# Expected outcomes by experiment type
EXPECTED_OUTCOMES = {
    "knockout": {
        "indel_frequency": ">60%",
        "frameshift_frequency": ">70% of indels",
        "common_deletions": "1-10bp deletions around cut site",
        "protein_expression": "Significant reduction or absence",
        "ideal_profile": "High frequency of frameshift mutations leading to protein loss"
    },
    "knockin": {
        "hdr_frequency": ">10% for small insertions, >5% for large insertions",
        "precise_insertions": ">80% of integration events",
        "indel_byproducts": "<50% of total editing outcomes",
        "expression": "Correct expression of inserted sequence",
        "ideal_profile": "Precise HDR events with minimal indel formation"
    },
    "base_editing": {
        "target_base_conversion": ">50%",
        "bystander_edits": "<20% of editing events",
        "indel_formation": "<5%",
        "specificity": "Minimal off-target editing",
        "ideal_profile": "High on-target base conversion with minimal bystander and indel formation"
    }
}

# Main classes and functions will be implemented in subsequent edits

class EnhancedResultParser:
    """
    Enhanced parser for CRISPResso2 result files with advanced interpretation.
    """
    
    def __init__(self, result_dir: str, experiment_type: str):
        """
        Initialize the parser with the CRISPResso2 results directory.
        
        Args:
            result_dir: Path to CRISPResso2 results directory
            experiment_type: Type of experiment (knockout, knockin, base_editing)
        """
        self.result_dir = os.path.abspath(result_dir)
        self.experiment_type = experiment_type
        self.results = {}
        self.alleles_data = None
        self.quantification_data = None
        self.alignment_data = None
        
        # Validate directory
        if not os.path.isdir(self.result_dir):
            raise ValueError(f"Result directory not found: {self.result_dir}")
        
        # Check for CRISPResso2 info file
        self.info_file = os.path.join(self.result_dir, "CRISPResso_info.json")
        if not os.path.isfile(self.info_file):
            raise ValueError(f"CRISPResso_info.json not found in {self.result_dir}")
        
        # Load the results
        self.load_results()
    
    def load_results(self):
        """Load and parse all relevant result files from the CRISPResso2 output directory."""
        # Load the main info file
        with open(self.info_file, 'r') as f:
            self.results["info"] = json.load(f)
        
        # Load the allele frequency table if it exists
        allele_file = os.path.join(self.result_dir, "Alleles_frequency_table.txt")
        if os.path.isfile(allele_file):
            try:
                self.alleles_data = pd.read_csv(allele_file, sep='\t')
                self.results["alleles"] = self.alleles_data.to_dict(orient='records')
            except Exception as e:
                print(f"Warning: Could not parse allele frequency table: {e}")
        
        # Load the quantification window file if it exists
        quant_file = os.path.join(self.result_dir, "Quantification_window_nucleotide_percentage_table.txt")
        if os.path.isfile(quant_file):
            try:
                self.quantification_data = pd.read_csv(quant_file, sep='\t')
                self.results["quantification"] = self.quantification_data.to_dict(orient='records')
            except Exception as e:
                print(f"Warning: Could not parse quantification window table: {e}")
        
        # Load frameshift analysis if it exists
        frameshift_file = os.path.join(self.result_dir, "Frameshift_analysis.txt")
        if os.path.isfile(frameshift_file):
            try:
                with open(frameshift_file, 'r') as f:
                    lines = f.readlines()
                    frameshift_data = {}
                    for line in lines:
                        if ':' in line:
                            key, value = line.strip().split(':', 1)
                            try:
                                # Try to convert values to numbers if possible
                                value = float(value.strip().replace('%', ''))
                            except ValueError:
                                value = value.strip()
                            frameshift_data[key.strip()] = value
                    self.results["frameshift"] = frameshift_data
            except Exception as e:
                print(f"Warning: Could not parse frameshift analysis: {e}")
        
        # Load indel size distribution if it exists
        indel_file = os.path.join(self.result_dir, "Insertion_deletion_substitution_size_distribution.txt")
        if os.path.isfile(indel_file):
            try:
                indel_data = pd.read_csv(indel_file, sep='\t')
                self.results["indel_size"] = indel_data.to_dict(orient='records')
            except Exception as e:
                print(f"Warning: Could not parse indel size distribution: {e}")
    
    def get_editing_efficiency(self) -> Dict[str, float]:
        """
        Calculate overall editing efficiency metrics.
        
        Returns:
            Dictionary with editing efficiency metrics
        """
        efficiency = {}
        
        # Try to get editing efficiency from the info file
        if "info" in self.results:
            info = self.results["info"]
            
            # Check for overall modification rate
            if "Modified" in info and "Total" in info:
                modified = float(info["Modified"])
                total = float(info["Total"])
                efficiency["overall_modification_rate"] = (modified / total) * 100 if total > 0 else 0
            
            # Check for NHEJ and HDR rates if available
            if "NHEJ" in info and "Total" in info:
                nhej = float(info["NHEJ"])
                total = float(info["Total"])
                efficiency["nhej_rate"] = (nhej / total) * 100 if total > 0 else 0
            
            if "HDR" in info and "Total" in info:
                hdr = float(info["HDR"])
                total = float(info["Total"])
                efficiency["hdr_rate"] = (hdr / total) * 100 if total > 0 else 0
            
            # For base editing, look for specific substitution rates
            if self.experiment_type == "base_editing":
                if "Substitutions" in info and "Total" in info:
                    substitutions = float(info["Substitutions"])
                    total = float(info["Total"])
                    efficiency["substitution_rate"] = (substitutions / total) * 100 if total > 0 else 0
        
        # Get frameshift rate from frameshift analysis
        if "frameshift" in self.results:
            frameshift = self.results["frameshift"]
            if "Frameshift mutations" in frameshift and "Non-frameshift mutations" in frameshift:
                fs = frameshift["Frameshift mutations"]
                nfs = frameshift["Non-frameshift mutations"]
                total_indels = fs + nfs
                efficiency["frameshift_rate"] = (fs / total_indels) * 100 if total_indels > 0 else 0
        
        return efficiency
    
    def get_top_alleles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the top edited alleles.
        
        Args:
            limit: Maximum number of alleles to return
            
        Returns:
            List of dictionaries with allele information
        """
        if self.alleles_data is None:
            return []
        
        # Sort by percentage
        sorted_alleles = self.alleles_data.sort_values(by="%Reads", ascending=False)
        
        # Get top alleles
        top_alleles = []
        for _, row in sorted_alleles.head(limit).iterrows():
            allele = dict(row)
            
            # Add additional analysis for the allele if needed
            if "#Reads" in allele and "Aligned_Sequence" in allele:
                if "Reference_Sequence" in sorted_alleles.columns:
                    ref_seq = sorted_alleles["Reference_Sequence"].iloc[0]
                    # Determine the type of edit
                    if allele["Aligned_Sequence"] == ref_seq:
                        allele["edit_type"] = "Unmodified"
                    elif len(allele["Aligned_Sequence"]) < len(ref_seq):
                        allele["edit_type"] = "Deletion"
                    elif len(allele["Aligned_Sequence"]) > len(ref_seq):
                        allele["edit_type"] = "Insertion"
                    else:
                        allele["edit_type"] = "Substitution"
            
            top_alleles.append(allele)
        
        return top_alleles
    
    def analyze_nucleotide_changes(self) -> Dict[str, Any]:
        """
        Analyze nucleotide-level changes for base editing experiments.
        
        Returns:
            Dictionary with analysis of nucleotide changes
        """
        if self.quantification_data is None:
            return {}
        
        result = {
            "positions": [],
            "nucleotide_percentages": {},
            "major_changes": []
        }
        
        # Check if we have the right columns
        required_cols = ["Nucleotide position", "Reference", "A", "C", "G", "T", "-"]
        if not all(col in self.quantification_data.columns for col in required_cols[:2]):
            return result
        
        # Prepare position data
        positions = self.quantification_data["Nucleotide position"].tolist()
        result["positions"] = positions
        
        # Get reference sequence
        ref_sequence = ''.join(self.quantification_data["Reference"].tolist())
        result["reference_sequence"] = ref_sequence
        
        # Get nucleotide percentages at each position
        for nt in ["A", "C", "G", "T", "-"]:
            if nt in self.quantification_data.columns:
                result["nucleotide_percentages"][nt] = self.quantification_data[nt].tolist()
        
        # Identify major changes (e.g., for base editing)
        changes = []
        for i, row in self.quantification_data.iterrows():
            ref_nt = row["Reference"]
            max_alt_nt = None
            max_alt_pct = 0
            
            for nt in ["A", "C", "G", "T", "-"]:
                if nt in row and nt != ref_nt:
                    if row[nt] > max_alt_pct:
                        max_alt_nt = nt
                        max_alt_pct = row[nt]
            
            if max_alt_pct > 10:  # Only report significant changes (>10%)
                changes.append({
                    "position": row["Nucleotide position"],
                    "reference": ref_nt,
                    "alternative": max_alt_nt,
                    "alt_percentage": max_alt_pct,
                    "change": f"{ref_nt}→{max_alt_nt}"
                })
        
        result["major_changes"] = changes
        
        return result
    
    def analyze_indel_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns of insertions and deletions.
        
        Returns:
            Dictionary with indel pattern analysis
        """
        result = {
            "deletion_hotspots": [],
            "common_insertion_sequences": [],
            "size_distribution": {},
            "microhomology_analysis": []
        }
        
        # Check if we have indel size distribution data
        if "indel_size" in self.results:
            indel_data = self.results["indel_size"]
            
            # Convert to a more structured format if it's a list of records
            size_counts = {}
            if isinstance(indel_data, list):
                for record in indel_data:
                    if "Size" in record and "#Reads" in record:
                        size = record["Size"]
                        count = record["#Reads"]
                        size_counts[size] = count
            
            result["size_distribution"] = size_counts
        
        # Analyze alleles for patterns if available
        if self.alleles_data is not None and "Reference_Sequence" in self.alleles_data.columns:
            ref_seq = self.alleles_data["Reference_Sequence"].iloc[0]
            
            # Analyze for microhomology patterns in deletions
            deletions = self.alleles_data[self.alleles_data["Aligned_Sequence"].str.len() < len(ref_seq)]
            
            if not deletions.empty:
                # Basic analysis of deletion positions
                deletion_positions = []
                for _, row in deletions.iterrows():
                    aligned_seq = row["Aligned_Sequence"]
                    
                    # Simplified deletion position analysis
                    # In a real implementation, would use alignment algorithms
                    i = j = 0
                    start_pos = end_pos = None
                    
                    while i < len(aligned_seq) and j < len(ref_seq):
                        if aligned_seq[i] == ref_seq[j]:
                            i += 1
                            j += 1
                        else:
                            if start_pos is None:
                                start_pos = j
                            j += 1
                    
                    if start_pos is not None:
                        end_pos = j - 1
                        deletion_positions.append({
                            "start": start_pos,
                            "end": end_pos,
                            "size": end_pos - start_pos + 1,
                            "reads": row["#Reads"]
                        })
                
                # Find hotspots (positions that appear in multiple deletions)
                position_counts = {}
                for deletion in deletion_positions:
                    for pos in range(deletion["start"], deletion["end"] + 1):
                        if pos not in position_counts:
                            position_counts[pos] = 0
                        position_counts[pos] += deletion["reads"]
                
                # Get top deletion hotspots
                hotspots = sorted(position_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                result["deletion_hotspots"] = [{"position": pos, "count": count} for pos, count in hotspots]
        
        return result
    
    def evaluate_experiment_success(self) -> Dict[str, Any]:
        """
        Evaluate the success of the experiment based on the type and expected outcomes.
        
        Returns:
            Dictionary with evaluation results
        """
        efficiency = self.get_editing_efficiency()
        evaluation = {
            "experiment_type": self.experiment_type,
            "metrics": efficiency,
            "assessment": "",
            "rating": "",
            "recommendations": []
        }
        
        if self.experiment_type == "knockout":
            # For knockout, look at overall modification and frameshift rates
            overall_rate = efficiency.get("overall_modification_rate", 0)
            frameshift_rate = efficiency.get("frameshift_rate", 0)
            
            # Determine success rating based on thresholds
            if overall_rate >= NHEJ_EFFICIENCY_THRESHOLDS["excellent"] and frameshift_rate >= 70:
                rating = "Excellent"
            elif overall_rate >= NHEJ_EFFICIENCY_THRESHOLDS["good"] and frameshift_rate >= 60:
                rating = "Good"
            elif overall_rate >= NHEJ_EFFICIENCY_THRESHOLDS["moderate"] and frameshift_rate >= 50:
                rating = "Moderate"
            elif overall_rate >= NHEJ_EFFICIENCY_THRESHOLDS["low"]:
                rating = "Low"
            else:
                rating = "Very Low"
            
            evaluation["rating"] = rating
            
            # Provide assessment and recommendations
            if rating in ["Excellent", "Good"]:
                evaluation["assessment"] = f"Successfully created indels with high efficiency ({overall_rate:.1f}%) and good frameshift rate ({frameshift_rate:.1f}%)."
                evaluation["recommendations"] = [
                    "Proceed with single-cell cloning to isolate knockout clones",
                    "Validate protein loss by Western blot",
                    "Perform functional assays to confirm knockout phenotype"
                ]
            elif rating == "Moderate":
                evaluation["assessment"] = f"Moderate editing efficiency ({overall_rate:.1f}%) with acceptable frameshift rate ({frameshift_rate:.1f}%)."
                evaluation["recommendations"] = [
                    "Consider optimizing delivery method for higher efficiency",
                    "Screen more clones to find complete knockouts",
                    "Verify results with a different guide RNA as backup"
                ]
            else:
                evaluation["assessment"] = f"Low editing efficiency ({overall_rate:.1f}%) or low frameshift rate ({frameshift_rate:.1f}%)."
                evaluation["recommendations"] = [
                    "Redesign guide RNA or try alternative guides",
                    "Optimize transfection/delivery protocol",
                    "Consider using RNP delivery instead of plasmid",
                    "Check for potential barriers to editing (e.g., chromatin state)"
                ]
        
        elif self.experiment_type == "knockin":
            # For knock-in, focus on HDR rate
            hdr_rate = efficiency.get("hdr_rate", 0)
            
            # Determine success rating based on thresholds
            if hdr_rate >= HDR_EFFICIENCY_THRESHOLDS["excellent"]:
                rating = "Excellent"
            elif hdr_rate >= HDR_EFFICIENCY_THRESHOLDS["good"]:
                rating = "Good"
            elif hdr_rate >= HDR_EFFICIENCY_THRESHOLDS["moderate"]:
                rating = "Moderate"
            elif hdr_rate >= HDR_EFFICIENCY_THRESHOLDS["low"]:
                rating = "Low"
            else:
                rating = "Very Low"
            
            evaluation["rating"] = rating
            
            # Provide assessment and recommendations
            if rating in ["Excellent", "Good"]:
                evaluation["assessment"] = f"Successfully achieved high HDR efficiency ({hdr_rate:.1f}%)."
                evaluation["recommendations"] = [
                    "Proceed with single-cell cloning to isolate knock-in clones",
                    "Validate precise integration by sequencing",
                    "Confirm expression and function of inserted sequence"
                ]
            elif rating == "Moderate":
                evaluation["assessment"] = f"Moderate HDR efficiency ({hdr_rate:.1f}%), sufficient for further development."
                evaluation["recommendations"] = [
                    "Optimize HDR conditions for future experiments",
                    "Screen more clones to find desired knock-in events",
                    "Consider enrichment strategies for edited cells"
                ]
            else:
                evaluation["assessment"] = f"Low HDR efficiency ({hdr_rate:.1f}%), improvement needed."
                evaluation["recommendations"] = [
                    "Optimize donor template design (check homology arm length)",
                    "Try HDR enhancers (e.g., RS-1, SCR7)",
                    "Synchronize cells in S/G2 phase for higher HDR",
                    "Consider using selection markers in donor template"
                ]
        
        elif self.experiment_type == "base_editing":
            # For base editing, look at substitution rate and specificity
            substitution_rate = efficiency.get("substitution_rate", 0)
            
            # Analyze nucleotide changes to check for bystander edits
            nucleotide_analysis = self.analyze_nucleotide_changes()
            major_changes = nucleotide_analysis.get("major_changes", [])
            
            # Count desired vs. bystander edits (simplified - would need more context)
            total_changes = len(major_changes)
            bystander_rate = 0
            if total_changes > 0:
                # This is a simplification - real implementation would need target base info
                bystander_rate = (total_changes - 1) / total_changes * 100 if total_changes > 1 else 0
            
            # Determine success rating based on thresholds
            if substitution_rate >= BASE_EDITING_THRESHOLDS["excellent"] and bystander_rate < 20:
                rating = "Excellent"
            elif substitution_rate >= BASE_EDITING_THRESHOLDS["good"] and bystander_rate < 30:
                rating = "Good"
            elif substitution_rate >= BASE_EDITING_THRESHOLDS["moderate"]:
                rating = "Moderate"
            elif substitution_rate >= BASE_EDITING_THRESHOLDS["low"]:
                rating = "Low"
            else:
                rating = "Very Low"
            
            evaluation["rating"] = rating
            evaluation["metrics"]["bystander_rate"] = bystander_rate
            
            # Provide assessment and recommendations
            if rating in ["Excellent", "Good"]:
                evaluation["assessment"] = f"Successfully achieved high base editing efficiency ({substitution_rate:.1f}%) with acceptable bystander editing ({bystander_rate:.1f}%)."
                evaluation["recommendations"] = [
                    "Proceed with single-cell cloning to isolate edited clones",
                    "Validate functional consequence of the edit",
                    "Consider sequencing to check for off-target effects"
                ]
            elif rating == "Moderate":
                evaluation["assessment"] = f"Moderate base editing efficiency ({substitution_rate:.1f}%) or higher bystander editing."
                evaluation["recommendations"] = [
                    "Try newer generation base editors with narrower editing windows",
                    "Optimize guide RNA design for better positioning of target base",
                    "Screen more clones to find cleanly edited cells"
                ]
            else:
                evaluation["assessment"] = f"Low base editing efficiency ({substitution_rate:.1f}%)."
                evaluation["recommendations"] = [
                    "Check base editor expression and delivery",
                    "Try alternative PAM variants for better positioning",
                    "Consider prime editing as an alternative approach",
                    "Optimize transfection conditions"
                ]
        
        return evaluation
    
    def generate_enhanced_summary(self, provide_therapeutic_context: bool = False) -> str:
        """
        Generate an enhanced, context-aware summary of the results using LLM.
        
        Args:
            provide_therapeutic_context (bool): Whether to include therapeutic context.
        
        Returns:
            String with enhanced summary
        """
        # Collect the key data for the summary
        efficiency = self.get_editing_efficiency()
        top_alleles = self.get_top_alleles(5)  # Get top 5 alleles
        nucleotide_analysis = self.analyze_nucleotide_changes() if self.experiment_type == "base_editing" else {}
        indel_analysis = self.analyze_indel_patterns()
        evaluation = self.evaluate_experiment_success()
        
        # Create a data package for the LLM
        data_package = {
            "experiment_type": self.experiment_type,
            "crispresso_reference_name": self.results.get("info", {}).get("Reference_Name", "Not specified"),
            "total_reads_analyzed": self.results.get("info", {}).get("Total", "Not specified"),
            "efficiency_metrics": efficiency,
            "top_alleles": top_alleles,
            "nucleotide_analysis": nucleotide_analysis,
            "indel_analysis": indel_analysis,
            "evaluation": {
                "rating": evaluation.get("rating"),
                "assessment": evaluation.get("assessment")
            },
            "expected_outcomes_for_this_experiment_type": EXPECTED_OUTCOMES.get(self.experiment_type, {})
        }
        
        # Create a prompt for the LLM
        prompt = f"""As an expert computational biologist specializing in CRISPR data analysis, provide a comprehensive and insightful interpretation of the following CRISPR experiment results for the reference '{data_package['crispresso_reference_name']}'.
        The experiment type is: {self.experiment_type}.

        EXPERIMENTAL DATA:
        {json.dumps(data_package, indent=2)}

        Please structure your analysis clearly. Use markdown for formatting.
        Start with an "Overall Assessment" of editing success based on the provided evaluation rating and key efficiency metrics.
        
        Then, for each relevant data section below, provide a detailed interpretation:
        
        1.  **Editing Efficiency:**
            *   Summarize the key efficiency metrics (e.g., overall modification, NHEJ/HDR/Substitution rates, frameshift rate).
            *   Interpret what these percentages mean in the context of a '{self.experiment_type}' experiment.
            *   Are these rates generally considered high, moderate, or low for this type of experiment?

        2.  **Top Alleles & Editing Outcomes:**
            *   Describe the most frequent unmodified and modified alleles. What are their characteristics (e.g., type of indel, size, specific base change)?
            *   For a '{self.experiment_type}' experiment, do these top alleles represent the desired outcome (e.g., frameshifts for knockout, precise HDR integration, correct base conversion)?
            *   Discuss the heterogeneity of the edited population based on these top alleles.

        3.  **Indel Patterns (if applicable, especially for NHEJ/knockout):**
            *   Summarize key findings from the indel analysis (e.g., common deletion/insertion sizes, hotspots).
            *   What do these patterns suggest about the repair mechanisms or guide activity?

        4.  **Nucleotide-Level Changes (critically important for Base Editing, may be relevant for others if substitutions are high):**
            *   If base editing: What is the efficiency of the desired A>G or C>T conversion at the target site(s)? Are there significant bystander edits (unintended conversions at nearby G/C or A/T bases)? What is the rate of undesired indels?
            *   If not base editing but substitutions are noted: Are there any unexpected substitution patterns?

        5.  **Comparison to Expected Outcomes:**
            *   How do the key metrics (e.g., indel frequency, HDR rate, base conversion rate) compare to the general expectations for a '{self.experiment_type}' experiment (refer to `expected_outcomes_for_this_experiment_type` in the data if helpful)?

        Finally, conclude with:
        - **Key Conclusions:** Summarize the 2-3 most important takeaways from this dataset regarding the success and nature of the editing.
        - **Actionable Recommendations:** Provide 2-3 specific, actionable recommendations for the researcher based *solely* on these CRISPResso2 results (e.g., proceed with clonal isolation, optimize gRNA, repeat with different conditions, perform off-target analysis next, validate functional consequence). 

        Your interpretation should be detailed, scientifically sound, and easy for a researcher to understand. Use specific values from the data to support your points. Focus only on the provided data.
        """
        
        if provide_therapeutic_context:
            prompt += f"""

### Therapeutic Development Contextual Analysis (based *only* on these on-target CRISPResso2 results):
Now, as an expert in translating CRISPR editing results into therapeutic development insights, provide additional context for a '{self.experiment_type}' experiment targeting '{data_package.get("crispresso_reference_name", "the target gene")}' for potential therapeutic application.

A. Therapeutic Efficacy Implications:
   - Based on the observed editing efficiency (e.g., NHEJ % from overall modification, HDR %, base conversion %), how do these on-target results align with achieving a therapeutically meaningful level of gene modification in a potential cell product? 
   - Discuss the importance of the specific allele profile (e.g., high percentage of frameshifts for knockout; precise HDR for knock-in; clean, high-efficiency base conversion for base editing) for therapeutic potency and predictability of the functional outcome.

B. On-Target Safety Profile & Manufacturability Hints:
   - While these results primarily show on-target editing, what aspects (e.g., very high indel rates or complex rearrangements if implied by alleles in base editing; significant NHEJ byproducts in HDR; high heterogeneity of edited alleles) might raise early flags for downstream safety assessments or manufacturability (e.g., product consistency) if this were a therapeutic candidate?
   - What types of *additional* off-target analyses (not covered by CRISPResso2 here, e.g., GUIDE-seq) would be critical next steps for a therapeutic program based on these on-target results?

C. Potential for Durability of Therapeutic Effect:
   - Based *only* on the on-target allele characteristics (e.g., types of indels, precision of HDR or base edits), are there any inferences that can be drawn about the potential for a durable therapeutic effect (e.g., likelihood of stable knockout, risk of reversion for specific edits if applicable)?

D. Cell Product Considerations (Ex Vivo Editing Context):
   - If these results were from *ex vivo* editing of cells intended for therapy (e.g., T-cells, HSCs), how might the observed on-target editing efficiency and the purity of the desired edited alleles impact considerations like the required cell dose for patients, potential for engraftment, or the need for cell enrichment strategies post-editing?

E. Overall Therapeutic Perspective (from on-target data):
   - Based *strictly on these on-target CRISPResso2 results*, what is your initial perspective on the suitability of this editing outcome for advancing a therapeutic program? What are the 1-2 most critical *on-target* characterizations or improvements (if any indicated by this data) needed before focusing heavily on off-target effects or *in vivo* studies?

Integrate these therapeutic considerations clearly, perhaps as a separate section or by weaving them into your main analysis points where appropriate, always emphasizing that these are interpretations of the provided *on-target* data.
            """
        
        # Call the LLM
        summary = query_llm(prompt)
        
        return summary
    
    def generate_visualizations(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Generate enhanced visualizations of the results.
        
        Args:
            output_dir: Directory to save visualizations (optional)
            
        Returns:
            Dictionary mapping visualization names to file paths or base64 encoded images
        """
        visualizations = {}
        
        # Create output directory if needed
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Generate editing efficiency plot
        vis_path_or_data = self._generate_efficiency_plot(output_dir)
        if vis_path_or_data:
            visualizations["editing_efficiency"] = vis_path_or_data
        
        # Generate allele frequency plot for top alleles
        vis_path_or_data = self._generate_allele_plot(output_dir)
        if vis_path_or_data:
            visualizations["allele_frequency"] = vis_path_or_data
        
        # Generate nucleotide percentage plot for base editing
        if self.experiment_type == "base_editing":
            vis_path_or_data = self._generate_nucleotide_plot(output_dir)
            if vis_path_or_data:
                visualizations["nucleotide_percentage"] = vis_path_or_data
        
        # Generate indel size distribution
        vis_path_or_data = self._generate_indel_size_plot(output_dir)
        if vis_path_or_data:
            visualizations["indel_size"] = vis_path_or_data
        
        return visualizations
    
    def _generate_efficiency_plot(self, output_dir: Optional[str] = None) -> Optional[str]:
        """Generate a visualization of editing efficiency metrics."""
        efficiency = self.get_editing_efficiency()
        if not efficiency:
            return None
        
        # Select the relevant metrics based on experiment type
        plot_data = {}
        if self.experiment_type == "knockout":
            relevant_metrics = ["overall_modification_rate", "frameshift_rate"]
        elif self.experiment_type == "knockin":
            relevant_metrics = ["overall_modification_rate", "nhej_rate", "hdr_rate"]
        elif self.experiment_type == "base_editing":
            relevant_metrics = ["overall_modification_rate", "substitution_rate"]
        else:
            relevant_metrics = ["overall_modification_rate"]
        
        # Filter for available metrics
        for metric in relevant_metrics:
            if metric in efficiency:
                plot_data[metric] = efficiency[metric]
        
        if not plot_data:
            return None
        
        # Create the plot
        plt.figure(figsize=(8, 6))
        bars = plt.bar(range(len(plot_data)), plot_data.values(), color='skyblue')
        plt.xticks(range(len(plot_data)), [m.replace('_', ' ').title() for m in plot_data.keys()], rotation=45)
        plt.ylabel('Percentage (%)')
        plt.title(f'Editing Efficiency Metrics - {self.experiment_type.title()} Experiment')
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save or return as base64
        if output_dir:
            output_path = os.path.join(output_dir, "efficiency_plot.png")
            plt.savefig(output_path)
            plt.close()
            return output_path
        else:
            # Return as base64 encoded string
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)
            img_str = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/png;base64,{img_str}"
    
    def _generate_allele_plot(self, output_dir: Optional[str] = None) -> Optional[str]:
        """Generate a visualization of top allele frequencies."""
        top_alleles = self.get_top_alleles(10)
        if not top_alleles:
            return None
        
        # Extract data for plotting
        labels = []
        freqs = []
        colors = []
        
        for allele in top_alleles:
            if "%Reads" in allele:
                freq = allele["%Reads"]
                
                # Create a simplified label
                label = "WT"  # Default for reference sequence
                color = 'green'
                
                if "edit_type" in allele:
                    if allele["edit_type"] == "Deletion":
                        label = f"Del ({len(allele.get('Reference_Sequence', '')) - len(allele.get('Aligned_Sequence', ''))}bp)"
                        color = 'red'
                    elif allele["edit_type"] == "Insertion":
                        label = f"Ins ({len(allele.get('Aligned_Sequence', '')) - len(allele.get('Reference_Sequence', ''))}bp)"
                        color = 'blue'
                    elif allele["edit_type"] == "Substitution":
                        label = "Subst"
                        color = 'orange'
                    elif allele["edit_type"] == "Unmodified":
                        label = "WT"
                        color = 'green'
                
                labels.append(label)
                freqs.append(freq)
                colors.append(color)
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        bars = plt.bar(range(len(freqs)), freqs, color=colors)
        plt.xticks(range(len(labels)), labels, rotation=45)
        plt.ylabel('Frequency (%)')
        plt.title('Top Allele Frequencies')
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save or return as base64
        if output_dir:
            output_path = os.path.join(output_dir, "allele_plot.png")
            plt.savefig(output_path)
            plt.close()
            return output_path
        else:
            # Return as base64 encoded string
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)
            img_str = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/png;base64,{img_str}"
    
    def _generate_nucleotide_plot(self, output_dir: Optional[str] = None) -> Optional[str]:
        """Generate a nucleotide percentage plot for base editing."""
        nuc_analysis = self.analyze_nucleotide_changes()
        if not nuc_analysis or not nuc_analysis.get("positions") or not nuc_analysis.get("nucleotide_percentages"):
            return None
        
        positions = nuc_analysis["positions"]
        nuc_pcts = nuc_analysis["nucleotide_percentages"]
        
        # Create a stacked bar plot
        plt.figure(figsize=(12, 6))
        
        bottom = np.zeros(len(positions))
        for nt, pcts in nuc_pcts.items():
            if len(pcts) == len(positions):  # Ensure lengths match
                if nt == 'A':
                    color = 'green'
                elif nt == 'C':
                    color = 'blue'
                elif nt == 'G':
                    color = 'black'
                elif nt == 'T':
                    color = 'red'
                else:  # Gap
                    color = 'gray'
                
                plt.bar(positions, pcts, bottom=bottom, label=nt, color=color, alpha=0.7)
                bottom += np.array(pcts)
        
        plt.xlabel('Position')
        plt.ylabel('Percentage (%)')
        plt.title('Nucleotide Composition by Position')
        plt.legend(title='Nucleotide')
        
        # Mark reference sequence on x-axis if available
        if "reference_sequence" in nuc_analysis:
            ref_seq = nuc_analysis["reference_sequence"]
            if len(ref_seq) == len(positions):
                plt.xticks(positions, ref_seq, rotation=0)
        
        # Highlight major changes
        if "major_changes" in nuc_analysis:
            for change in nuc_analysis["major_changes"]:
                plt.axvline(x=change["position"], color='purple', linestyle='--', alpha=0.5)
                plt.text(change["position"], 105, f"{change['change']}\n{change['alt_percentage']:.1f}%",
                        rotation=90, ha='center', va='bottom')
        
        plt.ylim(0, 100)
        plt.tight_layout()
        
        # Save or return as base64
        if output_dir:
            output_path = os.path.join(output_dir, "nucleotide_plot.png")
            plt.savefig(output_path)
            plt.close()
            return output_path
        else:
            # Return as base64 encoded string
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)
            img_str = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/png;base64,{img_str}"
    
    def _generate_indel_size_plot(self, output_dir: Optional[str] = None) -> Optional[str]:
        """Generate indel size distribution plot."""
        indel_analysis = self.analyze_indel_patterns()
        if not indel_analysis or not indel_analysis.get("size_distribution"):
            return None
        
        size_dist = indel_analysis["size_distribution"]
        
        # Convert to lists for plotting
        sizes = []
        counts = []
        for size, count in size_dist.items():
            sizes.append(int(size))
            counts.append(int(count))
        
        # Sort by size
        sorted_data = sorted(zip(sizes, counts))
        sizes = [x[0] for x in sorted_data]
        counts = [x[1] for x in sorted_data]
        
        # Convert counts to percentages
        total = sum(counts)
        percentages = [count/total*100 for count in counts] if total > 0 else counts
        
        # Create colors based on indel type
        colors = ['red' if s < 0 else 'blue' if s > 0 else 'green' for s in sizes]
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(range(len(sizes)), percentages, color=colors)
        plt.xticks(range(len(sizes)), sizes, rotation=90)
        plt.xlabel('Indel Size (negative = deletion, positive = insertion)')
        plt.ylabel('Frequency (%)')
        plt.title('Indel Size Distribution')
        
        # Add value labels for significant bars
        for bar, pct in zip(bars, percentages):
            if pct > 2:  # Only label bars with >2% frequency
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{pct:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save or return as base64
        if output_dir:
            output_path = os.path.join(output_dir, "indel_size_plot.png")
            plt.savefig(output_path)
            plt.close()
            return output_path
        else:
            # Return as base64 encoded string
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)
            img_str = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/png;base64,{img_str}"
    
    def compare_with_expected(self, expected_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compare results with expected outcomes or reference data.
        
        Args:
            expected_data: Dictionary with expected metrics (optional)
            
        Returns:
            Dictionary with comparison results
        """
        # If no expected data provided, use the standard expectations
        if not expected_data:
            expected_data = EXPECTED_OUTCOMES.get(self.experiment_type, {})
        
        # Get actual metrics
        efficiency = self.get_editing_efficiency()
        evaluation = self.evaluate_experiment_success()
        
        # Initialize comparison results
        comparison = {
            "experiment_type": self.experiment_type,
            "metrics_comparison": [],
            "overall_assessment": "",
            "exceeds_expectations": False,
            "meets_expectations": False,
            "below_expectations": False
        }
        
        # Compare each relevant metric
        for metric, expected in expected_data.items():
            if metric == "indel_frequency" and "overall_modification_rate" in efficiency:
                actual = efficiency["overall_modification_rate"]
                expected_min = self._parse_percentage(expected)
                comparison["metrics_comparison"].append({
                    "metric": "Indel Frequency",
                    "expected": expected,
                    "actual": f"{actual:.1f}%",
                    "assessment": "Above Target" if actual >= expected_min else "Below Target"
                })
            
            elif metric == "frameshift_frequency" and "frameshift_rate" in efficiency:
                actual = efficiency["frameshift_rate"]
                expected_min = self._parse_percentage(expected)
                comparison["metrics_comparison"].append({
                    "metric": "Frameshift Frequency",
                    "expected": expected,
                    "actual": f"{actual:.1f}%",
                    "assessment": "Above Target" if actual >= expected_min else "Below Target"
                })
            
            elif metric == "hdr_frequency" and "hdr_rate" in efficiency:
                actual = efficiency["hdr_rate"]
                expected_min = self._parse_percentage(expected)
                comparison["metrics_comparison"].append({
                    "metric": "HDR Frequency",
                    "expected": expected,
                    "actual": f"{actual:.1f}%",
                    "assessment": "Above Target" if actual >= expected_min else "Below Target"
                })
            
            elif metric == "target_base_conversion" and "substitution_rate" in efficiency:
                actual = efficiency["substitution_rate"]
                expected_min = self._parse_percentage(expected)
                comparison["metrics_comparison"].append({
                    "metric": "Target Base Conversion",
                    "expected": expected,
                    "actual": f"{actual:.1f}%",
                    "assessment": "Above Target" if actual >= expected_min else "Below Target"
                })
        
        # Determine overall assessment
        above_target_count = sum(1 for item in comparison["metrics_comparison"] if item["assessment"] == "Above Target")
        total_metrics = len(comparison["metrics_comparison"])
        
        if total_metrics > 0:
            if above_target_count == total_metrics:
                comparison["overall_assessment"] = "Exceeds expectations"
                comparison["exceeds_expectations"] = True
            elif above_target_count >= total_metrics / 2:
                comparison["overall_assessment"] = "Meets expectations"
                comparison["meets_expectations"] = True
            else:
                comparison["overall_assessment"] = "Below expectations"
                comparison["below_expectations"] = True
        
        return comparison
    
    def _parse_percentage(self, percentage_str: str) -> float:
        """Parse percentage strings like '>60%' to get the minimum value."""
        if not percentage_str:
            return 0
        
        match = re.search(r'([<>]?)(\d+(?:\.\d+)?)', percentage_str)
        if match:
            operator, value = match.groups()
            value = float(value)
            
            if operator == '>':
                return value
            elif operator == '<':
                return 0  # For < operator, any value above 0 is acceptable
            else:
                return value
        
        return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced CRISPR Results Interpreter")
    parser.add_argument("--results", "-r", type=str, required=True,
                      help="Path to CRISPResso2 results directory")
    parser.add_argument("--experiment", "-e", type=str, required=True,
                      choices=["knockout", "knockin", "base_editing"],
                      help="Type of experiment for context-aware interpretation")
    parser.add_argument("--output", "-o", type=str, help="Output directory for reports and visualizations")
    parser.add_argument("--advanced", "-a", action="store_true", help="Generate advanced metrics and visualizations")
    parser.add_argument("--compare", "-c", type=str, help="Path to expected outcomes or reference results for comparison")
    
    args = parser.parse_args()
    
    try:
        # Initialize the parser
        print(f"Loading results from {args.results}...")
        parser = EnhancedResultParser(args.results, args.experiment)
        
        # Get basic metrics
        efficiency = parser.get_editing_efficiency()
        print("\nEditing Efficiency Metrics:")
        for metric, value in efficiency.items():
            print(f"  {metric.replace('_', ' ').title()}: {value:.2f}%")
        
        # Get experimental success evaluation
        evaluation = parser.evaluate_experiment_success()
        print(f"\nExperiment Evaluation: {evaluation['rating']} - {evaluation['assessment']}")
        print("Recommendations:")
        for rec in evaluation["recommendations"]:
            print(f"  - {rec}")
        
        # Generate and save visualizations if output directory provided
        if args.output:
            print(f"\nGenerating visualizations in {args.output}...")
            visualizations = parser.generate_visualizations(args.output)
            print(f"Generated {len(visualizations)} visualizations:")
            for name, path in visualizations.items():
                print(f"  - {name}: {path}")
        
        # Compare with expected outcomes if provided
        if args.compare:
            try:
                with open(args.compare, 'r') as f:
                    expected_data = json.load(f)
                comparison = parser.compare_with_expected(expected_data)
            except Exception as e:
                print(f"Error loading comparison data: {e}")
                comparison = parser.compare_with_expected()
        else:
            comparison = parser.compare_with_expected()
        
        print(f"\nComparison with Expected Outcomes: {comparison['overall_assessment']}")
        for item in comparison["metrics_comparison"]:
            print(f"  {item['metric']}: {item['actual']} vs {item['expected']} - {item['assessment']}")
        
        # Generate enhanced summary
        print("\nGenerating enhanced summary...")
        summary = parser.generate_enhanced_summary(args.advanced)
        print("\n=== Enhanced Result Summary ===")
        print(summary)
        
        # Save comprehensive report if output directory provided
        if args.output:
            report_data = {
                "experiment_type": args.experiment,
                "efficiency_metrics": efficiency,
                "evaluation": evaluation,
                "comparison": comparison,
                "top_alleles": parser.get_top_alleles(),
                "summary": summary
            }
            
            # Save as JSON
            report_path = os.path.join(args.output, "enhanced_report.json")
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            # Save summary as text
            summary_path = os.path.join(args.output, "enhanced_summary.txt")
            with open(summary_path, 'w') as f:
                f.write(summary)
            
            print(f"\nComprehensive report saved to {report_path}")
            print(f"Summary saved to {summary_path}")
        
    except Exception as e:
        print(f"Error processing results: {e}")
        import traceback
        traceback.print_exc() 