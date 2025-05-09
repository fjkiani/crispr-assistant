# CHOPCHOP Integration with CRISPResso2

This project integrates [CHOPCHOP](https://chopchop.cbu.uib.no/) with CRISPResso2 to provide a complete workflow for guide RNA design and genome editing analysis.

## Overview

The integration enables:
1. Guide RNA design using CHOPCHOP
2. Analysis of editing outcomes using CRISPResso2
3. Seamless workflows combining both tools

## Directory Structure

- `tools/chopchop/`: Contains the CHOPCHOP source code
  - `chopchop.py`: Main CHOPCHOP script
  - `chopchop_integration.py`: Integration script for CRISPResso2
  - `example_workflow.py`: Example end-to-end workflow

## Prerequisites

CHOPCHOP has additional dependencies beyond CRISPResso2. Please refer to `tools/chopchop/README.md` for detailed installation instructions.

The key requirements include:
- Python 2.7 (CHOPCHOP requirement)
- Biopython
- pandas, numpy, scipy
- Bowtie
- And other dependencies listed in the CHOPCHOP README

## Basic Usage

### 1. Design guides with CHOPCHOP:

```bash
python tools/chopchop/chopchop_integration.py --genome hg38 --target BRCA1 --output chopchop_results
```

### 2. Analyze editing with CRISPResso2:

```bash
CRISPResso --fastq_r1 sample.fastq --amplicon_seq ACTGACTGACTG...
```

### 3. Run complete workflow:

```bash
python tools/chopchop/example_workflow.py --genome hg38 --target BRCA1 --fastq_r1 sample.fastq --output workflow_results
```

## Configuration

CHOPCHOP requires configuration of genome files and other resources. See `tools/chopchop/README.md` for details on creating `config_local.json`.

## Disclaimer

This integration is provided as-is. CHOPCHOP and CRISPResso2 are separate projects with different maintainers and licenses.

## License

- CRISPResso2: See LICENSE.txt
- CHOPCHOP: Apache License 2.0 (see tools/chopchop/LICENSE) 