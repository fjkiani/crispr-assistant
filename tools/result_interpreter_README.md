# Enhanced CRISPR Results Interpreter

The `result_interpreter.py` module provides advanced analysis and context-aware interpretation of CRISPR genome editing results, building on CRISPResso2 outputs with specialized visualizations and comparative metrics.

## Features

- **Advanced Metrics Extraction**: Extracts detailed metrics beyond the standard CRISPResso2 output
- **Context-Aware Interpretation**: Tailors analysis to specific experiment types (knockout, knock-in, base editing)
- **Enhanced Visualizations**: Creates intuitive visualizations for complex editing outcomes
- **Comparative Analysis**: Compares actual results with expected outcomes for experiment success evaluation
- **Specialized Interpretation**: Provides different analytical approaches for NHEJ, HDR, and base editing experiments
- **LLM-Powered Summaries**: Generates clear, scientific summaries with actionable recommendations

## Installation Requirements

This module requires the following Python packages:
- matplotlib
- numpy
- pandas

Install them using:
```
pip install matplotlib numpy pandas
```

## Basic Usage

```bash
python result_interpreter.py --results /path/to/crispresso_output --experiment knockout --output /path/to/save/results
```

### Command Line Arguments

- `--results`, `-r`: Path to CRISPResso2 results directory (required)
- `--experiment`, `-e`: Type of experiment - `knockout`, `knockin`, or `base_editing` (required)
- `--output`, `-o`: Output directory for reports and visualizations (optional)
- `--advanced`, `-a`: Generate advanced metrics and visualizations (optional)
- `--compare`, `-c`: Path to expected outcomes or reference results for comparison (optional)

## Programmatic Usage

```python
from result_interpreter import EnhancedResultParser

# Initialize the parser with the CRISPResso2 results directory
parser = EnhancedResultParser('/path/to/crispresso_output', 'knockout')

# Get editing efficiency metrics
efficiency = parser.get_editing_efficiency()

# Get evaluation of experiment success
evaluation = parser.evaluate_experiment_success()

# Generate visualizations
visualizations = parser.generate_visualizations('/path/to/save/visualizations')

# Get an enhanced summary of the results
summary = parser.generate_enhanced_summary()

# Compare with expected outcomes
comparison = parser.compare_with_expected()
```

## Visualization Types

The module generates the following visualizations:

1. **Editing Efficiency Plot**: Shows key efficiency metrics based on experiment type
2. **Allele Frequency Plot**: Displays distribution of top alleles from editing
3. **Nucleotide Percentage Plot**: For base editing, shows changes in nucleotide composition at each position
4. **Indel Size Distribution**: Shows the distribution of insertion and deletion sizes

## Example Output

When run on a CRISPResso2 result directory, the module produces:

```
Loading results from /path/to/crispresso_output...

Editing Efficiency Metrics:
  Overall Modification Rate: 65.42%
  Frameshift Rate: 72.18%

Experiment Evaluation: Good - Successfully created indels with high efficiency (65.4%) and good frameshift rate (72.2%).
Recommendations:
  - Proceed with single-cell cloning to isolate knockout clones
  - Validate protein loss by Western blot
  - Perform functional assays to confirm knockout phenotype

Generating visualizations in /path/to/save/results...
Generated 3 visualizations:
  - editing_efficiency: /path/to/save/results/efficiency_plot.png
  - allele_frequency: /path/to/save/results/allele_plot.png
  - indel_size: /path/to/save/results/indel_size_plot.png

Comparison with Expected Outcomes: Meets expectations
  Indel Frequency: 65.4% vs >60% - Above Target
  Frameshift Frequency: 72.2% vs >70% - Above Target

Generating enhanced summary...

=== Enhanced Result Summary ===
[LLM-generated summary appears here]

Comprehensive report saved to /path/to/save/results/enhanced_report.json
Summary saved to /path/to/save/results/enhanced_summary.txt
```

## Integration with Other Modules

This module can be integrated with:

- `guide_interpreter.py` for end-to-end guide design and result analysis
- `experiment_advisor.py` for experiment design based on results
- `next_steps.py` for determining follow-up experiments

## Specialized Analysis by Experiment Type

### Knockout Analysis
- Focuses on indel frequency and frameshift rate
- Evaluates likelihood of functional protein disruption
- Suggests validation based on editing patterns

### Knock-in Analysis
- Focuses on HDR efficiency and precision of insertions
- Analyzes integration junctions for accuracy
- Suggests validation strategies specific to knock-in experiments

### Base Editing Analysis
- Analyzes target base conversion efficiency
- Evaluates bystander editing in the activity window
- Compares patterns to expected outcomes for the specific base editor 