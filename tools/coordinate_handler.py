#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coordinate Handler Module

This module provides functionality for working with genomic coordinates, 
converting between coordinate systems, retrieving sequence context,
and annotating features like exons, introns, and protein domains.
"""

import os
import json
import sys
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import urllib.request
import urllib.parse

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global variables
UCSC_GENOME_URL = "https://genome.ucsc.edu/cgi-bin/"
ENSEMBL_API_URL = "https://rest.ensembl.org/"
DEFAULT_GENOME = "hg38"

# Dictionary of common genome assemblies
GENOME_ASSEMBLIES = {
    "human": {
        "GRCh38": {"ucsc": "hg38", "ensembl": "GRCh38", "refseq": "GCF_000001405.39"},
        "GRCh37": {"ucsc": "hg19", "ensembl": "GRCh37", "refseq": "GCF_000001405.25"}
    },
    "mouse": {
        "GRCm39": {"ucsc": "mm39", "ensembl": "GRCm39", "refseq": "GCF_000001635.27"},
        "GRCm38": {"ucsc": "mm10", "ensembl": "GRCm38", "refseq": "GCF_000001635.20"}
    },
    "rat": {
        "mRatBN7.2": {"ucsc": "rn7", "ensembl": "Rnor_6.0", "refseq": "GCF_015227675.2"},
        "Rnor_6.0": {"ucsc": "rn6", "ensembl": "Rnor_6.0", "refseq": "GCF_000001895.5"}
    }
}

# Gene feature types
FEATURE_TYPES = [
    "gene", "transcript", "exon", "CDS", "UTR", "promoter", 
    "enhancer", "silencer", "insulator", "TFBS"
]

class GenomicCoordinate:
    """Class representing a genomic coordinate with chromosome, position, and strand."""
    
    def __init__(self, 
                 chromosome: str, 
                 position: int, 
                 strand: str = '+', 
                 assembly: str = DEFAULT_GENOME):
        """
        Initialize a genomic coordinate.
        
        Args:
            chromosome: Chromosome name (e.g., 'chr1', '1', 'X')
            position: 1-based position on the chromosome
            strand: '+' for forward strand, '-' for reverse strand
            assembly: Genome assembly (e.g., 'hg38', 'mm10')
        """
        self.chromosome = self._standardize_chromosome(chromosome)
        self.position = position
        self.strand = strand
        self.assembly = assembly
    
    def _standardize_chromosome(self, chromosome: str) -> str:
        """Standardize chromosome format (add 'chr' prefix if missing)."""
        if not chromosome.startswith('chr') and chromosome not in ['X', 'Y', 'MT', 'M']:
            return f"chr{chromosome}"
        elif chromosome in ['X', 'Y', 'MT', 'M']:
            return f"chr{chromosome}"
        return chromosome
    
    def to_ucsc_format(self) -> str:
        """Convert to UCSC browser format."""
        return f"{self.chromosome}:{self.position}-{self.position}"
    
    def to_ensembl_format(self) -> str:
        """Convert to Ensembl format (without 'chr' prefix)."""
        chrom = self.chromosome.replace('chr', '')
        return f"{chrom}:{self.position}-{self.position}:{self.strand}"
    
    def to_igv_format(self) -> str:
        """Convert to IGV format."""
        return f"{self.chromosome}:{self.position}"
    
    def get_region(self, upstream: int = 100, downstream: int = 100) -> Tuple[str, int, int]:
        """
        Get a region around this coordinate.
        
        Args:
            upstream: Number of bases upstream
            downstream: Number of bases downstream
            
        Returns:
            Tuple of (chromosome, start, end)
        """
        if self.strand == '+':
            start = max(1, self.position - upstream)
            end = self.position + downstream
        else:
            start = max(1, self.position - downstream)
            end = self.position + upstream
        
        return (self.chromosome, start, end)
    
    def get_ucsc_browser_url(self, window_size: int = 200) -> str:
        """
        Generate a UCSC Genome Browser URL for this coordinate.
        
        Args:
            window_size: Size of the window around the coordinate
            
        Returns:
            URL to UCSC Genome Browser
        """
        half_window = window_size // 2
        chrom, start, end = self.get_region(half_window, half_window)
        position = f"{chrom}:{start}-{end}"
        
        params = {
            "db": self.assembly,
            "position": position
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{UCSC_GENOME_URL}hgTracks?{query_string}"

class GenomicRegion:
    """Class representing a genomic region with start and end coordinates."""
    
    def __init__(self, 
                 chromosome: str, 
                 start: int, 
                 end: int, 
                 strand: str = '+', 
                 assembly: str = DEFAULT_GENOME,
                 feature_type: Optional[str] = None,
                 name: Optional[str] = None):
        """
        Initialize a genomic region.
        
        Args:
            chromosome: Chromosome name
            start: 1-based start position (inclusive)
            end: 1-based end position (inclusive)
            strand: '+' for forward strand, '-' for reverse strand
            assembly: Genome assembly
            feature_type: Type of genomic feature (e.g., 'gene', 'exon')
            name: Name of the region/feature
        """
        self.chromosome = self._standardize_chromosome(chromosome)
        self.start = start
        self.end = end
        self.strand = strand
        self.assembly = assembly
        self.feature_type = feature_type
        self.name = name
        self.length = end - start + 1
    
    def _standardize_chromosome(self, chromosome: str) -> str:
        """Standardize chromosome format (add 'chr' prefix if missing)."""
        if not chromosome.startswith('chr') and chromosome not in ['X', 'Y', 'MT', 'M']:
            return f"chr{chromosome}"
        elif chromosome in ['X', 'Y', 'MT', 'M']:
            return f"chr{chromosome}"
        return chromosome
    
    def contains(self, coordinate: GenomicCoordinate) -> bool:
        """Check if this region contains a specific coordinate."""
        if coordinate.chromosome != self.chromosome:
            return False
        
        return self.start <= coordinate.position <= self.end
    
    def overlaps(self, other_region: 'GenomicRegion') -> bool:
        """Check if this region overlaps with another region."""
        if other_region.chromosome != self.chromosome:
            return False
        
        return not (self.end < other_region.start or self.start > other_region.end)
    
    def distance_to(self, other: Union[GenomicCoordinate, 'GenomicRegion']) -> int:
        """
        Calculate distance to another genomic coordinate or region.
        Returns 0 if they overlap.
        """
        if isinstance(other, GenomicCoordinate):
            if other.chromosome != self.chromosome:
                return float('inf')  # Different chromosomes
            
            if self.start <= other.position <= self.end:
                return 0  # Contained
            
            return min(abs(self.start - other.position), abs(self.end - other.position))
        
        elif isinstance(other, GenomicRegion):
            if other.chromosome != self.chromosome:
                return float('inf')  # Different chromosomes
            
            if self.overlaps(other):
                return 0  # Overlapping
            
            return min(abs(self.start - other.end), abs(self.end - other.start))
    
    def to_ucsc_format(self) -> str:
        """Convert to UCSC browser format."""
        return f"{self.chromosome}:{self.start}-{self.end}"
    
    def to_bed_format(self) -> str:
        """Convert to BED format (0-based start)."""
        name = self.name if self.name else f"{self.feature_type or 'region'}_{self.chromosome}_{self.start}_{self.end}"
        score = 0
        strand = self.strand
        return f"{self.chromosome}\t{self.start - 1}\t{self.end}\t{name}\t{score}\t{strand}"
    
    def get_ucsc_browser_url(self, highlight: bool = True) -> str:
        """
        Generate a UCSC Genome Browser URL for this region.
        
        Args:
            highlight: Whether to highlight the region
            
        Returns:
            URL to UCSC Genome Browser
        """
        position = f"{self.chromosome}:{self.start}-{self.end}"
        
        params = {
            "db": self.assembly,
            "position": position
        }
        
        if highlight:
            params["highlight"] = position
        
        query_string = urllib.parse.urlencode(params)
        return f"{UCSC_GENOME_URL}hgTracks?{query_string}"

class GeneCoordinateConverter:
    """Class for converting between gene symbols and genomic coordinates."""
    
    def __init__(self, refgene_file: Optional[str] = None, assembly: str = DEFAULT_GENOME):
        """
        Initialize the converter.
        
        Args:
            refgene_file: Path to refGene.txt file (optional)
            assembly: Genome assembly
        """
        self.assembly = assembly
        self.gene_info = {}
        self.exon_info = {}
        
        # Try to load from refgene_file if provided
        if refgene_file and os.path.exists(refgene_file):
            self._load_refgene(refgene_file)
    
    def _load_refgene(self, refgene_file: str) -> None:
        """Load gene information from refGene.txt file."""
        try:
            with open(refgene_file, 'r') as f:
                for line in f:
                    fields = line.strip().split('\t')
                    if len(fields) < 16:
                        continue
                    
                    # Extract information from refGene format
                    transcript_id = fields[1]
                    gene_symbol = fields[12]
                    chromosome = fields[2]
                    strand = fields[3]
                    tx_start = int(fields[4]) + 1  # Convert to 1-based
                    tx_end = int(fields[5])
                    cds_start = int(fields[6]) + 1  # Convert to 1-based
                    cds_end = int(fields[7])
                    exon_count = int(fields[8])
                    exon_starts = [int(x) + 1 for x in fields[9].strip(',').split(',')]  # Convert to 1-based
                    exon_ends = [int(x) for x in fields[10].strip(',').split(',')]
                    
                    # Store gene information
                    if gene_symbol not in self.gene_info:
                        self.gene_info[gene_symbol] = []
                    
                    gene_record = {
                        'transcript_id': transcript_id,
                        'chromosome': chromosome,
                        'strand': strand,
                        'tx_start': tx_start,
                        'tx_end': tx_end,
                        'cds_start': cds_start,
                        'cds_end': cds_end
                    }
                    
                    self.gene_info[gene_symbol].append(gene_record)
                    
                    # Store exon information
                    if gene_symbol not in self.exon_info:
                        self.exon_info[gene_symbol] = {}
                    
                    if transcript_id not in self.exon_info[gene_symbol]:
                        self.exon_info[gene_symbol][transcript_id] = []
                    
                    for i in range(exon_count):
                        exon_record = {
                            'exon_number': i + 1,
                            'start': exon_starts[i],
                            'end': exon_ends[i]
                        }
                        self.exon_info[gene_symbol][transcript_id].append(exon_record)
        
        except Exception as e:
            print(f"Error loading refGene file: {e}")
    
    def gene_to_region(self, gene_symbol: str) -> Optional[GenomicRegion]:
        """
        Convert a gene symbol to a genomic region.
        Returns the longest transcript if multiple exist.
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            GenomicRegion object or None if not found
        """
        if gene_symbol not in self.gene_info:
            return self._fetch_gene_coordinates(gene_symbol)
        
        # Get the longest transcript
        transcripts = self.gene_info[gene_symbol]
        longest = max(transcripts, key=lambda t: t['tx_end'] - t['tx_start'])
        
        return GenomicRegion(
            chromosome=longest['chromosome'],
            start=longest['tx_start'],
            end=longest['tx_end'],
            strand=longest['strand'],
            assembly=self.assembly,
            feature_type='gene',
            name=gene_symbol
        )
    
    def gene_to_coding_region(self, gene_symbol: str) -> Optional[GenomicRegion]:
        """
        Convert a gene symbol to its coding region.
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            GenomicRegion object or None if not found
        """
        if gene_symbol not in self.gene_info:
            return None
        
        # Get the longest transcript
        transcripts = self.gene_info[gene_symbol]
        longest = max(transcripts, key=lambda t: t['cds_end'] - t['cds_start'])
        
        return GenomicRegion(
            chromosome=longest['chromosome'],
            start=longest['cds_start'],
            end=longest['cds_end'],
            strand=longest['strand'],
            assembly=self.assembly,
            feature_type='CDS',
            name=f"{gene_symbol}_CDS"
        )
    
    def get_exons(self, gene_symbol: str, transcript_id: Optional[str] = None) -> List[GenomicRegion]:
        """
        Get exons for a gene.
        
        Args:
            gene_symbol: Gene symbol
            transcript_id: Specific transcript ID (optional)
            
        Returns:
            List of GenomicRegion objects for exons
        """
        if gene_symbol not in self.exon_info:
            return []
        
        result = []
        
        # If transcript_id is specified, get exons for that transcript
        if transcript_id and transcript_id in self.exon_info[gene_symbol]:
            transcript_exons = self.exon_info[gene_symbol][transcript_id]
            chromosome = self.gene_info[gene_symbol][0]['chromosome']  # Assume same chromosome for all transcripts
            strand = self.gene_info[gene_symbol][0]['strand']
            
            for exon in transcript_exons:
                region = GenomicRegion(
                    chromosome=chromosome,
                    start=exon['start'],
                    end=exon['end'],
                    strand=strand,
                    assembly=self.assembly,
                    feature_type='exon',
                    name=f"{gene_symbol}_exon{exon['exon_number']}"
                )
                result.append(region)
            
            return result
        
        # If no transcript_id specified, get exons for all transcripts
        for transcript_id, exons in self.exon_info[gene_symbol].items():
            # Find the gene record for this transcript
            gene_record = None
            for record in self.gene_info[gene_symbol]:
                if record['transcript_id'] == transcript_id:
                    gene_record = record
                    break
            
            if not gene_record:
                continue
            
            for exon in exons:
                region = GenomicRegion(
                    chromosome=gene_record['chromosome'],
                    start=exon['start'],
                    end=exon['end'],
                    strand=gene_record['strand'],
                    assembly=self.assembly,
                    feature_type='exon',
                    name=f"{gene_symbol}_{transcript_id}_exon{exon['exon_number']}"
                )
                result.append(region)
        
        return result
    
    def _fetch_gene_coordinates(self, gene_symbol: str) -> Optional[GenomicRegion]:
        """
        Fetch gene coordinates from online resources.
        This is a fallback if local refGene file doesn't have the information.
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            GenomicRegion object or None if not found
        """
        try:
            # Try Ensembl API - this is a simplified example and will need proper error handling
            url = f"{ENSEMBL_API_URL}lookup/symbol/homo_sapiens/{gene_symbol}?content-type=application/json"
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            
            if 'seq_region_name' in data and 'start' in data and 'end' in data:
                return GenomicRegion(
                    chromosome=data['seq_region_name'],
                    start=data['start'],
                    end=data['end'],
                    strand='+' if data['strand'] == 1 else '-',
                    assembly=self.assembly,
                    feature_type='gene',
                    name=gene_symbol
                )
        
        except Exception as e:
            print(f"Error fetching gene coordinates for {gene_symbol}: {e}")
        
        return None

def coordinate_to_gene(coordinate: GenomicCoordinate, 
                      refgene_file: Optional[str] = None,
                      distance_threshold: int = 10000) -> List[Dict[str, Any]]:
    """
    Find genes near a genomic coordinate.
    
    Args:
        coordinate: GenomicCoordinate object
        refgene_file: Path to refGene.txt file (optional)
        distance_threshold: Maximum distance to consider a gene "near"
        
    Returns:
        List of dictionaries with gene information and distances
    """
    converter = GeneCoordinateConverter(refgene_file, coordinate.assembly)
    
    result = []
    
    # Check all genes in the converter
    for gene_symbol, transcripts in converter.gene_info.items():
        for transcript in transcripts:
            if transcript['chromosome'] != coordinate.chromosome:
                continue
            
            # Create a region for this transcript
            region = GenomicRegion(
                chromosome=transcript['chromosome'],
                start=transcript['tx_start'],
                end=transcript['tx_end'],
                strand=transcript['strand'],
                assembly=coordinate.assembly,
                feature_type='gene',
                name=gene_symbol
            )
            
            # Check if coordinate is in or near the gene
            distance = 0
            position_type = 'intergenic'
            
            if region.contains(coordinate):
                distance = 0
                position_type = 'intragenic'
                
                # Check if in an exon
                for transcript_id, exons in converter.exon_info.get(gene_symbol, {}).items():
                    for exon in exons:
                        exon_region = GenomicRegion(
                            chromosome=transcript['chromosome'],
                            start=exon['start'],
                            end=exon['end'],
                            strand=transcript['strand'],
                            assembly=coordinate.assembly
                        )
                        
                        if exon_region.contains(coordinate):
                            position_type = 'exonic'
                            break
                
                # If not in an exon, it must be intronic
                if position_type == 'intragenic':
                    position_type = 'intronic'
            else:
                # Calculate distance to gene
                distance = region.distance_to(coordinate)
                if distance > distance_threshold:
                    continue
            
            result.append({
                'gene_symbol': gene_symbol,
                'transcript_id': transcript['transcript_id'],
                'distance': distance,
                'position_type': position_type,
                'region': {
                    'chromosome': region.chromosome,
                    'start': region.start,
                    'end': region.end,
                    'strand': region.strand
                }
            })
    
    # Sort by distance
    result.sort(key=lambda x: x['distance'])
    
    return result

def get_sequence_context(region: GenomicRegion, 
                         fasta_file: Optional[str] = None,
                         use_web_api: bool = False) -> Optional[str]:
    """
    Get the sequence for a genomic region.
    
    Args:
        region: GenomicRegion object
        fasta_file: Path to genome FASTA file (optional)
        use_web_api: Whether to use web API if local file not available
        
    Returns:
        DNA sequence as string or None if not found
    """
    # Try to get sequence from local file first
    if fasta_file and os.path.exists(fasta_file):
        # This is a simplified implementation and would need a proper FASTA parser
        # like pyfaidx or pysam in practice
        try:
            with open(fasta_file, 'r') as f:
                # Very simplistic FASTA parser - not efficient for large files
                current_chrom = None
                sequence = ""
                target_chrom = region.chromosome.replace('chr', '')
                
                for line in f:
                    if line.startswith('>'):
                        if current_chrom == target_chrom and sequence:
                            # We've found our chromosome and are now at the next one
                            break
                        
                        # Update current chromosome
                        header = line[1:].strip().split()[0]
                        current_chrom = header.replace('chr', '')
                        sequence = ""
                    elif current_chrom == target_chrom:
                        sequence += line.strip()
                
                if current_chrom == target_chrom and len(sequence) >= region.end:
                    # Extract the requested region (convert to 0-based index)
                    return sequence[region.start-1:region.end]
        
        except Exception as e:
            print(f"Error reading sequence from FASTA file: {e}")
    
    # If local file failed or not provided, try web API if allowed
    if use_web_api:
        try:
            # Try UCSC DAS server
            das_url = f"https://genome.ucsc.edu/cgi-bin/das/{region.assembly}/dna?segment={region.chromosome}:{region.start},{region.end}"
            response = urllib.request.urlopen(das_url)
            data = response.read().decode('utf-8')
            
            # Parse XML response to extract sequence
            match = re.search(r'<DNA.*?>(.*?)</DNA>', data, re.DOTALL)
            if match:
                sequence = match.group(1).replace('\n', '').strip()
                return sequence
        
        except Exception as e:
            print(f"Error fetching sequence from web API: {e}")
    
    return None

def generate_genome_browser_link(region: GenomicRegion, 
                               tracks: Optional[List[str]] = None,
                               highlight: bool = True) -> str:
    """
    Generate a link to a genome browser for a specific region.
    
    Args:
        region: GenomicRegion object
        tracks: List of tracks to display
        highlight: Whether to highlight the region
        
    Returns:
        URL string
    """
    position = f"{region.chromosome}:{region.start}-{region.end}"
    
    params = {
        "db": region.assembly,
        "position": position
    }
    
    if highlight:
        params["highlight"] = position
    
    if tracks:
        params["tracks"] = ",".join(tracks)
    
    query_string = urllib.parse.urlencode(params)
    return f"{UCSC_GENOME_URL}hgTracks?{query_string}"

def load_gene_database(gene_database_dir: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Load the gene database from local files.
    
    Args:
        gene_database_dir: Directory containing gene FASTA files
        
    Returns:
        Dictionary mapping gene symbols to sequence and other information
    """
    result = {}
    
    if not gene_database_dir:
        # Try to find gene_database directory relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        potential_dirs = [
            os.path.join(script_dir, '..', 'gene_database'),
            os.path.join(script_dir, 'gene_database')
        ]
        
        for directory in potential_dirs:
            if os.path.isdir(directory):
                gene_database_dir = directory
                break
    
    if not gene_database_dir or not os.path.isdir(gene_database_dir):
        print(f"Gene database directory not found")
        return result
    
    # Load all FASTA files in the directory
    for filename in os.listdir(gene_database_dir):
        if filename.endswith('.fasta') or filename.endswith('.fa'):
            gene_symbol = os.path.splitext(filename)[0].upper()
            
            try:
                with open(os.path.join(gene_database_dir, filename), 'r') as f:
                    content = f.read()
                    
                    # Parse FASTA
                    lines = content.strip().split('\n')
                    header = lines[0]
                    sequence = ''.join(lines[1:])
                    
                    # Extract information from header
                    info = {'symbol': gene_symbol, 'sequence': sequence}
                    
                    # Add additional info from header if available
                    if header.startswith('>'):
                        header_info = header[1:].strip()
                        info['header'] = header_info
                        
                        # Try to parse more structured headers
                        parts = header_info.split('|')
                        if len(parts) > 1:
                            info['id'] = parts[0].strip()
                            if len(parts) > 2:
                                info['description'] = parts[1].strip()
                    
                    result[gene_symbol] = info
            
            except Exception as e:
                print(f"Error loading gene file {filename}: {e}")
    
    return result

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Genomic Coordinate Handler')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Gene to Coordinates command
    gene_parser = subparsers.add_parser('gene2coord', help='Convert gene symbol to coordinates')
    gene_parser.add_argument('--gene', '-g', type=str, required=True, help='Gene symbol')
    gene_parser.add_argument('--refgene', '-r', type=str, help='Path to refGene.txt file')
    gene_parser.add_argument('--assembly', '-a', type=str, default=DEFAULT_GENOME, help='Genome assembly')
    gene_parser.add_argument('--format', '-f', type=str, choices=['ucsc', 'bed', 'ensembl'], default='ucsc', 
                             help='Output format')
    
    # Coordinates to Gene command
    coord_parser = subparsers.add_parser('coord2gene', help='Find genes near a coordinate')
    coord_parser.add_argument('--chrom', '-c', type=str, required=True, help='Chromosome')
    coord_parser.add_argument('--pos', '-p', type=int, required=True, help='Position')
    coord_parser.add_argument('--refgene', '-r', type=str, help='Path to refGene.txt file')
    coord_parser.add_argument('--assembly', '-a', type=str, default=DEFAULT_GENOME, help='Genome assembly')
    coord_parser.add_argument('--distance', '-d', type=int, default=10000, help='Maximum distance threshold')
    
    # Get Sequence command
    seq_parser = subparsers.add_parser('getseq', help='Get sequence for a region')
    seq_parser.add_argument('--chrom', '-c', type=str, required=True, help='Chromosome')
    seq_parser.add_argument('--start', '-s', type=int, required=True, help='Start position')
    seq_parser.add_argument('--end', '-e', type=int, required=True, help='End position')
    seq_parser.add_argument('--assembly', '-a', type=str, default=DEFAULT_GENOME, help='Genome assembly')
    seq_parser.add_argument('--fasta', '-f', type=str, help='Path to genome FASTA file')
    seq_parser.add_argument('--web', '-w', action='store_true', help='Use web API if local file not available')
    
    # Generate Browser Link command
    browser_parser = subparsers.add_parser('browser', help='Generate genome browser link')
    browser_parser.add_argument('--chrom', '-c', type=str, required=True, help='Chromosome')
    browser_parser.add_argument('--start', '-s', type=int, required=True, help='Start position')
    browser_parser.add_argument('--end', '-e', type=int, required=True, help='End position')
    browser_parser.add_argument('--assembly', '-a', type=str, default=DEFAULT_GENOME, help='Genome assembly')
    browser_parser.add_argument('--tracks', '-t', type=str, help='Comma-separated list of tracks to display')
    browser_parser.add_argument('--highlight', action='store_true', default=True, help='Highlight the region')
    
    # Load Gene Database command
    db_parser = subparsers.add_parser('loaddb', help='Load gene database')
    db_parser.add_argument('--dir', '-d', type=str, help='Gene database directory')
    
    args = parser.parse_args()
    
    if args.command == 'gene2coord':
        converter = GeneCoordinateConverter(args.refgene, args.assembly)
        region = converter.gene_to_region(args.gene)
        
        if region:
            if args.format == 'ucsc':
                print(region.to_ucsc_format())
            elif args.format == 'bed':
                print(region.to_bed_format())
            elif args.format == 'ensembl':
                # Create a simple Ensembl-like format
                chrom = region.chromosome.replace('chr', '')
                print(f"{chrom}:{region.start}-{region.end}:{region.strand}")
            
            print(f"\nUCSC Browser URL: {region.get_ucsc_browser_url()}")
        else:
            print(f"Gene {args.gene} not found")
    
    elif args.command == 'coord2gene':
        coordinate = GenomicCoordinate(args.chrom, args.pos, assembly=args.assembly)
        genes = coordinate_to_gene(coordinate, args.refgene, args.distance)
        
        if genes:
            print(f"Found {len(genes)} genes near {coordinate.to_ucsc_format()}:")
            for gene in genes:
                print(f"- {gene['gene_symbol']} ({gene['position_type']}, distance: {gene['distance']} bp)")
        else:
            print(f"No genes found within {args.distance} bp of {coordinate.to_ucsc_format()}")
    
    elif args.command == 'getseq':
        region = GenomicRegion(args.chrom, args.start, args.end, assembly=args.assembly)
        sequence = get_sequence_context(region, args.fasta, args.web)
        
        if sequence:
            print(f"Sequence for {region.to_ucsc_format()} ({len(sequence)} bp):")
            print(sequence)
        else:
            print(f"Could not retrieve sequence for {region.to_ucsc_format()}")
    
    elif args.command == 'browser':
        region = GenomicRegion(args.chrom, args.start, args.end, assembly=args.assembly)
        tracks_list = args.tracks.split(',') if args.tracks else None
        
        url = generate_genome_browser_link(region, tracks_list, args.highlight)
        print(f"UCSC Browser URL: {url}")
    
    elif args.command == 'loaddb':
        gene_db = load_gene_database(args.dir)
        
        if gene_db:
            print(f"Loaded {len(gene_db)} genes from database:")
            for symbol, info in gene_db.items():
                seq_len = len(info['sequence'])
                print(f"- {symbol} ({seq_len} bp)")
        else:
            print("No genes found in database")
    
    else:
        parser.print_help() 