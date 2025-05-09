# CHOPCHOP Integration with CRISPResso2

This directory contains the CHOPCHOP tool, cloned from https://bitbucket.org/valenlab/chopchop.git and integrated with CRISPResso2.

## About CHOPCHOP

CHOPCHOP is a Python script that allows quick and customizable design of guide RNA. It supports selecting target sites for CRISPR/Cas9, CRISPR/Cpf1, TALEN, and NICKASE with a wide range of customization options. It also supports Cas13 for isoform targeting.

## Integration with CRISPResso2

CHOPCHOP can be used as a complementary tool to CRISPResso2:

1. **Guide Design**: Use CHOPCHOP to design optimal guide RNAs for your experiment
2. **Sequence Analysis**: After experiments, use CRISPResso2 to analyze editing outcomes

## Basic Usage

To use CHOPCHOP, you can run it from this directory:

```
python tools/chopchop/chopchop.py -G [genome] -o [output_dir] -Target [target_sequence_or_gene]
```

For more details, see the main README.md file in this directory or visit the CHOPCHOP website at https://chopchop.cbu.uib.no/

## Prerequisites

CHOPCHOP has several dependencies. Please refer to the main README.md file for installation instructions.

## License

CHOPCHOP is open-sourced under the Apache License 2.0. 