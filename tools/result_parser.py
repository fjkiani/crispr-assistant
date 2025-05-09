#!/usr/bin/env python
"""
Result Parser for CRISPResso2 AI Research Assistant

This utility parses CRISPResso2 output files and provides summarization
capabilities for the AI Research Assistant.
"""

import os
import json
import glob
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any


class CRISPRessoResultParser:
    """Parser for CRISPResso2 results."""
    
    def __init__(self, results_directory):
        """
        Initializes the parser with the path to the CRISPResso2 output directory.
        """
        self.results_directory = results_directory
        self.info_file_path = os.path.join(results_directory, "CRISPResso_info.json")
        self.info_data = None
        self.error = None
        self.allele_data = None
        self.quantification_data = {}
        
        self._load_info_file()
        
        if self.results_directory and os.path.exists(self.results_directory):
            self._load_data()
    
    def _load_info_file(self):
        """
        Loads the CRISPResso_info.json file.
        """
        try:
            if not os.path.exists(self.info_file_path):
                self.error = f"Error: CRISPResso_info.json not found in {self.results_directory}"
                print(self.error)
                return
            
            with open(self.info_file_path, 'r') as f:
                self.info_data = json.load(f)
            print(f"Successfully loaded {self.info_file_path}")

        except json.JSONDecodeError as e:
            self.error = f"Error: Could not decode JSON from {self.info_file_path}. File might be corrupted. {e}"
            print(self.error)
            self.info_data = None
        except Exception as e:
            self.error = f"Error loading {self.info_file_path}: {e}"
            print(self.error)
            self.info_data = None
    
    def is_valid(self):
        """
        Checks if the info file was loaded successfully.
        """
        return self.info_data is not None and self.error is None
    
    def _load_data(self) -> None:
        """Load data from the CRISPResso output directory."""
        # Load Alleles_frequency_table.txt
        allele_path = os.path.join(self.results_directory, "Alleles_frequency_table.txt")
        if os.path.exists(allele_path):
            try:
                self.allele_data = pd.read_csv(allele_path, sep="\t")
            except Exception as e:
                print(f"Error loading allele data: {e}")
        
        # Load Quantification_of_editing_frequency.txt
        quant_path = os.path.join(self.results_directory, "Quantification_of_editing_frequency.txt")
        if os.path.exists(quant_path):
            try:
                quant_df = pd.read_csv(quant_path, sep="\t")
                # Convert to a more convenient dictionary format
                for _, row in quant_df.iterrows():
                    self.quantification_data[row["Amplicon"]] = {
                        "Unmodified": row["Unmodified%"],
                        "Modified": row["Modified%"],
                        "Discarded": row["Discarded%"]
                    }
            except Exception as e:
                print(f"Error loading quantification data: {e}")
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """
        Extracts basic statistics like read counts and overall editing percentage.
        """
        if not self.is_valid():
            return { "error": self.error or "Info data not loaded." }

        stats = {}
        try:
            results_info = self.info_data.get('results', {})
            stats['Experiment Name'] = self.info_data.get('name', 'N/A')
            stats['Reference Name'] = self.info_data.get('reference_name', 'N/A')
            stats['Input Reads'] = results_info.get('input_reads', 'N/A')
            stats['Total Reads Processed'] = results_info.get('reads_processed', 'N/A')
            stats['Reads Aligned'] = results_info.get('reads_aligned', 'N/A')
            stats['Reads Unaligned'] = stats['Total Reads Processed'] - stats['Reads Aligned'] if isinstance(stats['Total Reads Processed'], int) and isinstance(stats['Reads Aligned'], int) else 'N/A'
            
            quant_freq = results_info.get('general_info', {}).get('quantification_of_editing_frequency', {})
            if isinstance(quant_freq, dict): # Newer CRISPResso format
                stats['Unmodified Percentage'] = quant_freq.get('Unmodified%', 'N/A')
                stats['Modified Percentage'] = quant_freq.get('Modified%', 'N/A') # Includes NHEJ+HDR+Mixed
                stats['NHEJ Percentage'] = quant_freq.get('NHEJ%', 'N/A')
                stats['HDR Percentage'] = quant_freq.get('HDR%', 'N/A')
                stats['Mixed HDR-NHEJ Percentage'] = quant_freq.get('Mixed HDR-NHEJ%', 'N/A')
            else: # Older format might have different structure - adapt as needed
                 stats['Unmodified Percentage'] = 'N/A'
                 stats['Modified Percentage'] = 'N/A'
                 stats['NHEJ Percentage'] = 'N/A'
                 stats['HDR Percentage'] = 'N/A'
                 stats['Mixed HDR-NHEJ Percentage'] = 'N/A'

        except Exception as e:
            stats['error'] = f"Error extracting basic stats: {e}"

        return stats
    
    def get_top_alleles(self, n: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get the top N alleles for each amplicon.
        
        Args:
            n: Number of top alleles to return
            
        Returns:
            Dictionary mapping amplicon names to lists of top alleles
        """
        if self.allele_data is None:
            return {"error": "No allele data available"}
        
        top_alleles = {}
        
        # Check if 'Amplicon' column exists
        if "Amplicon" not in self.allele_data.columns:
             return {"error": "'Amplicon' column not found in allele data."}

        # Group by Amplicon and get top alleles for each
        for amplicon, group in self.allele_data.groupby("Amplicon"):
            # Sort by percentage (descending)
            sorted_alleles = group.sort_values("Percentage", ascending=False).head(n)
            
            # Convert to list of dictionaries
            allele_list = []
            for _, row in sorted_alleles.iterrows():
                allele_info = {
                    "allele_id": row["Allele"],
                    "sequence": row["Aligned_Sequence"],
                    "percentage": row["Percentage"],
                    "count": row["#Reads"],
                    "is_reference": row["Reference_Sequence"], # Boolean
                    "nhej": row["NHEJ"], # Boolean
                    "hdr": row["HDR"], # Boolean
                    "includes_substitution": row["includes_substitution"], # Boolean
                    "includes_insertion": row["includes_insertion"], # Boolean
                    "includes_deletion": row["includes_deletion"], # Boolean
                    "indel_len": row["indel_length"], # Integer or NaN
                }
                allele_list.append(allele_info)
            
            top_alleles[amplicon] = allele_list
        
        return top_alleles
    
    def get_frameshift_analysis(self) -> Dict[str, Dict[str, float]]:
        """
        Get frameshift analysis data.
        
        Returns:
            Dictionary with frameshift statistics
        """
        frameshift_path = os.path.join(self.results_directory, "Frameshift_analysis.txt")
        if not os.path.exists(frameshift_path):
            return {"error": "Frameshift analysis not available"}
        
        try:
            frameshift_df = pd.read_csv(frameshift_path, sep="\t")
            
            frameshift_data = {}
            # Check if 'Amplicon' column exists
            if "Amplicon" not in frameshift_df.columns:
                 return {"error": "'Amplicon' column not found in frameshift data."}
            
            for _, row in frameshift_df.iterrows():
                amplicon = row["Amplicon"]
                frameshift_data[amplicon] = {
                    "in_frame_percent": row.get("n_of_mutations_in_frame%", 0),
                    "frameshift_percent": row.get("n_of_mutations_frameshift%", 0),
                    "in_frame_count": row.get("n_of_mutations_in_frame", 0),
                    "frameshift_count": row.get("n_of_mutations_frameshift", 0),
                    "total_modified_reads_analyzed": row.get("n_of_mutations_all", 0)
                }
            
            return frameshift_data
        except Exception as e:
            return {"error": f"Error parsing frameshift data: {e}"}
    
    def get_nhej_hdr_analysis(self) -> Dict[str, Dict[str, float]]:
        """
        Get NHEJ vs HDR analysis if available.
        
        Returns:
            Dictionary with NHEJ/HDR statistics
        """
        nhej_path = os.path.join(self.results_directory, "Quantification_of_NHEJ_HDR_outcomes.txt")
        if not os.path.exists(nhej_path):
            return {"error": "NHEJ/HDR analysis not available"}
        
        try:
            nhej_df = pd.read_csv(nhej_path, sep="\t")
            
            nhej_data = {}
            # Check if 'Amplicon' column exists
            if "Amplicon" not in nhej_df.columns:
                 return {"error": "'Amplicon' column not found in NHEJ/HDR data."}
                 
            for _, row in nhej_df.iterrows():
                amplicon = row["Amplicon"]
                nhej_data[amplicon] = {
                    "unmodified_percent": row.get("Unmodified%", 0),
                    "nhej_percent": row.get("NHEJ%", 0),
                    "hdr_percent": row.get("HDR%", 0),
                    "mixed_percent": row.get("Mixed HDR-NHEJ%", 0)
                }
            
            return nhej_data
        except Exception as e:
            return {"error": f"Error parsing NHEJ/HDR data: {e}"}
    
    def generate_summary(self) -> str:
        """
        Generate a human-readable summary of the CRISPResso2 results.
        
        Returns:
            Formatted string summary
        """
        if not self.is_valid():
            return self.error or "CRISPResso results could not be loaded or parsed."
        
        basic_stats = self.get_basic_stats()
        top_alleles = self.get_top_alleles()
        frameshift_data = self.get_frameshift_analysis()
        nhej_data = self.get_nhej_hdr_analysis()
        
        summary_lines = [
            f"# CRISPResso2 Analysis Summary: {basic_stats.get('Experiment Name', 'Unnamed')}",
            "",
            f"## Run Overview",
            f"- Input Reads: {basic_stats.get('Input Reads', 'N/A')}",
            f"- Reads Processed: {basic_stats.get('Total Reads Processed', 'N/A')}",
            f"- Reads Aligned: {basic_stats.get('Reads Aligned', 'N/A')} ({100*basic_stats.get('Reads Aligned', 0)/basic_stats.get('Total Reads Processed', 1):.1f}% of processed)" if isinstance(basic_stats.get('Reads Aligned'), int) and isinstance(basic_stats.get('Total Reads Processed'), int) and basic_stats.get('Total Reads Processed', 0) > 0 else "",
            f"- Reads Unaligned: {basic_stats.get('Reads Unaligned', 'N/A')}",
        ]
        
        # Add editing efficiency summary
        summary_lines.append("\n## Overall Editing Frequency")
        summary_lines.append(f"- Modified Reads: {basic_stats.get('Modified Percentage', 'N/A')}%" if basic_stats.get('Modified Percentage') != 'N/A' else "- Modified Reads: N/A")
        summary_lines.append(f"- Unmodified Reads: {basic_stats.get('Unmodified Percentage', 'N/A')}%" if basic_stats.get('Unmodified Percentage') != 'N/A' else "- Unmodified Reads: N/A")
        if basic_stats.get('NHEJ Percentage') != 'N/A':
            summary_lines.append(f"  - NHEJ Reads: {basic_stats.get('NHEJ Percentage', 'N/A')}%" )
        if basic_stats.get('HDR Percentage') != 'N/A':
             summary_lines.append(f"  - HDR Reads: {basic_stats.get('HDR Percentage', 'N/A')}%" )
        if basic_stats.get('Mixed HDR-NHEJ Percentage') != 'N/A':
             summary_lines.append(f"  - Mixed HDR-NHEJ Reads: {basic_stats.get('Mixed HDR-NHEJ Percentage', 'N/A')}%" )

        # Add top alleles
        if "error" not in top_alleles:
            summary_lines.append("\n## Top Alleles (showing up to 5)")
            for amplicon, alleles in top_alleles.items():
                summary_lines.append(f"- For Amplicon '{amplicon}':")
                if not alleles:
                    summary_lines.append("    No allele data found for this amplicon.")
                    continue
                for i, allele in enumerate(alleles, 1):
                    mods = []
                    if allele['is_reference']: mods.append("Reference")
                    if allele['nhej']: mods.append("NHEJ")
                    if allele['hdr']: mods.append("HDR")
                    if allele['includes_substitution']: mods.append("Sub")
                    if allele['includes_insertion']: mods.append(f"Ins({allele['indel_len']})")
                    if allele['includes_deletion']: mods.append(f"Del({allele['indel_len']})")
                    mod_str = ", ".join(mods) if mods else "Unknown"
                    summary_lines.append(f"  {i}. {allele['percentage']:.2f}% ({allele['count']} reads) - {mod_str} - Sequence: {allele['sequence'][:20]}..." if len(allele['sequence'])>20 else f"  {i}. {allele['percentage']:.2f}% ({allele['count']} reads) - {mod_str} - Sequence: {allele['sequence']}")
        else:
             summary_lines.append(f"\n## Top Alleles: {top_alleles['error']}")

        # Add frameshift analysis summary
        if "error" not in frameshift_data:
            summary_lines.append("\n## Frameshift Analysis (of Modified Reads)")
            for amplicon, data in frameshift_data.items():
                 summary_lines.append(f"- For Amplicon '{amplicon}':")
                 if data.get('total_modified_reads_analyzed', 0) > 0:
                     summary_lines.append(f"  - In-frame mutations: {data.get('in_frame_percent', 0):.1f}% ({data.get('in_frame_count', 0)} reads)")
                     summary_lines.append(f"  - Frameshift mutations: {data.get('frameshift_percent', 0):.1f}% ({data.get('frameshift_count', 0)} reads)")
                 else:
                     summary_lines.append("    No modified reads found for frameshift analysis.")
        else:
             summary_lines.append(f"\n## Frameshift Analysis: {frameshift_data['error']}")

        # Add NHEJ/HDR analysis summary (redundant if already in basic stats, but maybe more detail here if needed)
        # if "error" not in nhej_data:
        #     summary_lines.append("\n## NHEJ vs HDR Quantification")
        #     # ... Add details from nhej_data if desired ...
        # else:
        #      summary_lines.append(f"\n## NHEJ vs HDR Quantification: {nhej_data['error']}")
        
        return "\n".join(summary_lines)


# Example Usage (for testing)
if __name__ == "__main__":
    # Replace with an actual path to a CRISPResso output directory for testing
    # Assumes a structure like: ./crispresso_output/Your_Experiment_Name/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_dir = os.path.join(project_root, "crispresso_output", "CRISPResso_on_example") # Adjust experiment name if needed
    
    if os.path.exists(test_dir):
        parser = CRISPRessoResultParser(test_dir)
        if parser.is_valid():
            # basic_stats = parser.get_basic_stats()
            # print("\nBasic Stats:")
            # print(json.dumps(basic_stats, indent=2))
            print(parser.generate_summary())
        else:
            print(f"\nCould not parse results from {test_dir}")
    else:
        print(f"Test directory not found: {test_dir}. Cannot run example usage.")
        print("Please create a dummy CRISPResso output directory with at least a CRISPResso_info.json,")
        print("or point to a real one by updating the path in result_parser.py main block.") 