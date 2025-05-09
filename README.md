[![Docker Image Version (tag)](https://img.shields.io/docker/v/pinellolab/crispresso2/latest?logo=docker&label=Docker)](https://hub.docker.com/r/pinellolab/crispresso2/tags)
[![CircleCI branch](https://img.shields.io/circleci/project/github/pinellolab/CRISPResso2/master.svg)](https://circleci.com/gh/pinellolab/CRISPResso2)
[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat)](http://bioconda.github.io/recipes/crispresso2/README.html)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://docs.crispresso.com)

# CRISPResso2

CRISPResso2 is a software pipeline designed to enable rapid and intuitive interpretation of genome editing experiments. A limited web implementation is available at: https://crispresso2.pinellolab.org/.

Briefly, CRISPResso2:

- aligns sequencing reads to a reference sequence
- quantifies insertions, mutations and deletions to determine whether a read is modified or unmodified by genome editing
- summarizes editing results in intuitive plots and datasets

Access the full documentation at <https://docs.crispresso.com>.

In addition, CRISPResso can be run as part of a larger tool suite:

- [CRISPRessoBatch](https://docs.crispresso.com/suite/batch/tool.html) - for analyzing and comparing multiple experimental conditions at the same site
- [CRISPRessoPooled](https://docs.crispresso.com/suite/pooled/tool.html) - for analyzing multiple amplicons from a pooled amplicon sequencing experiment
- [CRISPRessoWGS](https://docs.crispresso.com/suite/wgs/tool.html) - for analyzing specific sites in whole-genome sequencing samples
- [CRISPRessoCompare](https://docs.crispresso.com/suite/compare/tool.html) - for comparing editing between two samples (e.g., treated vs control)
- [CRISPRessoAggregate](https://docs.crispresso.com/suite/aggregate/tool.html) - for aggregating results from previously-run CRISPResso analyses

![CRISPResso2 Schematic](https://raw.githubusercontent.com/pinellolab/CRISPResso2/master/crispresso_schematic.png "CRISPResso2 Schematic")

## Installation

CRISPResso2 can be [installed](https://docs.crispresso.com/installation.html) in the following ways:

- [Bioconda](https://docs.crispresso.com/installation.html#bioconda)
  - [Bioconda on Apple Silicon](https://docs.crispresso.com/installation.html#bioconda-for-apple-silicon)
- [Docker](https://docs.crispresso.com/installation.html#docker)

## Examples

- [CRISPResso example runs](https://docs.crispresso.com/suite/core/examples.html)
- [CRISPRessoBatch example runs](https://docs.crispresso.com/suite/batch/examples.html)
- [CRISPRessoPooled example runs](https://docs.crispresso.com/suite/pooled/examples.html)
- [CRISPRessoWGS example runs](https://docs.crispresso.com/suite/wgs/examples.html)
- [CRISPRessoCompare example runs](https://docs.crispresso.com/suite/compare/examples.html)
- [CRISPRessoPooledWGCompare example runs](https://docs.crispresso.com/suite/pooledwgscompare/examples.html)
- [CRISPRessoAggregate example runs](https://docs.crispresso.com/suite/aggregate/examples.html)

## Troubleshooting

If you run into any issues, check out the [Troubleshooting page](https://docs.crispresso.com/troubleshooting.html) or submit a [new discussion](https://github.com/pinellolab/CRISPResso2/discussions/new?category=troubleshooting).

# AI-Powered CRISPR Research Assistant: Revolutionizing Genome Editing Workflows

[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini-blue?logo=google)](https://ai.google.dev/gemini-api)
[![CRISPR Tools](https://img.shields.io/badge/CRISPR-Tools-brightgreen)](https://github.com/pinellolab/CRISPResso2)

**Transform your CRISPR research with an intelligent assistant that seamlessly integrates cutting-edge computational tools with the power of Artificial Intelligence. This platform is designed to make sophisticated genome editing design and analysis accessible, efficient, and insightful for researchers at all levels of computational expertise.**

## 🧬 The Challenge: Navigating the Complexities of CRISPR Workflows

CRISPR-Cas9 and related technologies have revolutionized genome editing. However, designing effective experiments and analyzing their outcomes can be a significant hurdle:

*   **Steep Learning Curve:** Tools like CHOPCHOP for guide RNA design and CRISPResso2 for analyzing editing outcomes are powerful but require considerable bioinformatics knowledge to use effectively. Parameter selection can be daunting for non-experts.
*   **Time-Consuming Processes:** Manually configuring software, executing command-line scripts, sifting through raw output files, and interpreting dense datasets can consume days, diverting valuable researcher time from experimental work.
*   **Tool Compatibility & Setup:** Ensuring correct installation and compatibility of bioinformatics tools and their dependencies (like Bowtie for CHOPCHOP) across different operating systems (especially problematic on newer systems like Apple Silicon) can be a major roadblock.
*   **Data Interpretation Bottleneck:** Raw outputs from analysis tools are often complex tables and metrics. Translating this data into biologically meaningful insights (e.g., "What is my actual editing efficiency?", "What are the predominant repair outcomes?") requires expertise and can be error-prone.
*   **Risk of Suboptimal Design:** Incorrect guide selection or analysis parameter choices can lead to inefficient editing, ambiguous results, and costly failed experiments.

**Our AI Research Assistant directly addresses these challenges, acting as an expert computational biologist by your side.**

## 💡 Our Solution: The AI CRISPR Research Assistant

This platform streamlines your entire CRISPR workflow, from initial guide RNA design to the final interpretation of editing results. It achieves this by:

1.  **Intelligent Guide RNA Design:** Leverages CHOPCHOP for comprehensive guide searching, enhanced by AI-driven parameter suggestions and a robust fallback mechanism (`simple_guide_finder.py`) for common genes or when CHOPCHOP encounters system compatibility issues.
2.  **Automated Editing Analysis:** Integrates CRISPResso2 for in-depth analysis of high-throughput sequencing data from editing experiments, with AI simplifying the setup and command execution.
3.  **AI-Powered Interpretation & Guidance:** Employs Large Language Models (LLMs like Google's Gemini) to explain complex configurations, guide choices, and analysis results in clear, natural language. It can answer your questions about the data and provide contextual insights.
4.  **User-Friendly Interfaces:** Offers both a conversational Command-Line Interface (CLI) (`ai_research_assistant.py`) for quick interactions and a rich Streamlit web application (`streamlit_app.py`) for a more visual and guided experience.

## 🔬 Transforming Your Research: Scientific & Business Value

By bridging the gap between wet-lab biology and complex bioinformatics, our AI Assistant delivers significant advantages:

### Overcoming Hurdles & Empowering Researchers
*   **Democratizes Advanced CRISPR Tools:** Makes sophisticated computational methods accessible to all researchers, regardless of their bioinformatics background. The AI acts as a knowledgeable guide, explaining parameters and interpreting outputs.
*   **Drastically Reduces Time to Insight:** Automates laborious tasks like command generation, data parsing, and initial result summarization. What might take days of manual effort can be achieved much faster, accelerating the research cycle.
*   **Minimizes Errors & Improves Reproducibility:** AI-assisted parameter selection for both guide design and analysis reduces the chance of human error. Standardized workflows enhance the reproducibility of computational analyses.
*   **Solves Compatibility Frustrations:** The integrated `simple_guide_finder.py` and intelligent handling of CHOPCHOP execution provide a more robust experience, especially for common gene targets or on systems where CHOPCHOP dependencies are problematic.

### Tangible Benefits for Labs and Organizations
*   **Accelerates Discovery Timelines:** Faster, more efficient design and analysis cycles directly translate to quicker project completion, publication, and potential for therapeutic or biotechnological breakthroughs.
*   **Lowers Training Overhead:** New lab members or those unfamiliar with bioinformatics can become productive with CRISPR computational analysis more rapidly, freeing up senior researchers' time.
*   **Reduces Costs from Failed Experiments:** Improved guide RNA design and more accurate interpretation of preliminary results can lead to higher success rates in editing experiments, saving valuable reagents, time, and resources.
*   **Fosters Cross-Disciplinary Collaboration:** Enables biologists with limited coding experience to fully leverage powerful computational tools, fostering a more integrated approach to genome editing research.
*   **Enhances Grant Competitiveness:** Demonstrating use of cutting-edge, efficient, and AI-augmented methodologies can strengthen research proposals.

## 🧪 Deep Dive: CRISPR Capabilities & AI Integration

Our assistant leverages the strengths of established CRISPR tools, augmenting them with AI for an enhanced user experience and deeper insights.

### Guide RNA Design (CHOPCHOP Integration & Custom Fallback)
*   **Comprehensive Genome Support:** Can be configured for virtually any organism with available genome data (e.g., `.2bit` sequence files, Bowtie indices, gene annotation files). Pre-configured for human (hg38) for ease of use.
*   **Flexible Target Input:**
    *   **Gene Symbols:** Simply provide a gene name (e.g., TP53, BRCA1).
    *   **DNA Sequences:** Input your specific DNA sequence directly.
    *   **Genomic Coordinates:** Target precise regions using chromosome, start, and end positions.
*   **Diverse Enzyme Compatibility:** Primarily supports **Cas9** (default PAM: NGG) and **Cpf1/Cas12a** (PAM: TTTV), with flexibility to specify custom PAM sequences.
*   **Robust `simple_guide_finder.py`:**
    *   **Benefit:** For commonly studied genes (e.g., TP53), this script provides immediate guide candidates from a built-in sequence database, bypassing CHOPCHOP's external dependencies and potential system-specific issues (e.g., on Apple Silicon with `twoBitToFa`). This ensures reliability and speed for high-interest targets.
    *   It is also used as an intelligent fallback if the main `chopchop_integration.py` script fails.
*   **Sophisticated Guide Scoring & Selection (via CHOPCHOP):**
    *   Evaluates guides based on multiple criteria: predicted on-target efficiency, GC content, self-complementarity, off-target potential (if enabled and Bowtie is functional), and location within the gene (exonic, intronic).
    *   **AI Enhancement:** The LLM can explain *why* certain guides are ranked higher, demystifying the scoring metrics and aiding in informed decision-making.
*   **`tools/chopchop/chopchop_integration.py`:**
    *   **Benefit:** This script acts as a smart wrapper around CHOPCHOP's core `chopchop.py`. It handles input validation, dynamically constructs the CHOPCHOP command with appropriate parameters (including those for sequence inputs vs. gene symbols), executes CHOPCHOP, and standardizes the output (e.g., `top_guides.json`). It also incorporates the logic to switch to `simple_guide_finder.py` when beneficial.

### CRISPR Editing Analysis (CRISPResso2 Integration)
*   **Gold-Standard Analysis:** Utilizes CRISPResso2 to meticulously analyze FASTQ sequencing reads from CRISPR experiments.
*   **Key Quantification Metrics:**
    *   **Overall Editing Efficiency:** Percentage of reads modified by CRISPR activity.
    *   **Allele Frequencies:** Identifies and quantifies all unique DNA sequences (alleles) present at the target site, including unmodified, NHEJ-repaired, and HDR-repaired alleles.
    *   **Indel Analysis:** Detailed characterization of insertions and deletions (size, location, frequency).
    *   **Frameshift vs. In-Frame Mutations:** Crucial for understanding the functional impact of edits, especially for gene knockout experiments.
    *   **NHEJ vs. HDR Outcomes:** If an HDR template is provided, CRISPResso2 quantifies the efficiency of precise repair via Homology-Directed Repair versus error-prone Non-Homologous End Joining.
*   **Support for Advanced Editing Modalities:**
    *   **Base Editing:** Can analyze outcomes of base editors (e.g., C-to-T or A-to-G conversions) when relevant parameters are specified.
    *   **Multiplex Editing:** Can process experiments where multiple guides target different sites simultaneously (requires appropriate CRISPResso2 setup).
*   **`tools/result_parser.py`:**
    *   **Benefit:** This crucial script ingests the numerous output files generated by CRISPResso2 (e.g., `CRISPResso_info.json`, `Alleles_frequency_table.txt`, `Frameshift_analysis.txt`) and structures the complex data into an accessible format. This parsed data is then used by the AI for summarization and Q&A.
*   **AI-Guided Parameterization & Interpretation:**
    *   **Setup:** The AI can help you choose appropriate CRISPResso2 parameters (e.g., quantification window size, minimum read quality, HDR settings) based on your experimental design, reducing potential errors.
    *   **Summarization:** The LLM generates a human-readable summary of the key findings from the CRISPResso2 analysis, highlighting important metrics like overall editing efficiency, top alleles, and frameshift rates. This saves researchers from manually piecing together this information.
    *   **Q&A:** Users can ask specific questions about their results (e.g., "What was the rate of +1 insertions?", "Show me the HDR efficiency for my experiment.") and receive AI-generated answers based on the parsed data.

## 💻 Technical Architecture & AI Integration

Our system is built upon a modular set of Python scripts, orchestrated by either a command-line or a web-based interface, with AI woven throughout the workflow.

### Core Scripts & Their Roles
*   **`streamlit_app.py`:** Provides a rich, interactive web application for a guided user experience. Ideal for users who prefer graphical interfaces and visual feedback.
    *   **Benefit:** Lowers the barrier to entry, makes complex configurations intuitive through forms and buttons, and displays results (tables, LLM summaries) in an organized manner.
*   **`ai_research_assistant.py`:** Offers a conversational command-line interface (CLI). Suitable for users comfortable with terminal environments or for scripting automated workflows.
    *   **Benefit:** Enables rapid interaction, easy integration into existing bioinformatic pipelines, and efficient operation for power users.
*   **`tools/chopchop/chopchop_integration.py`:** A sophisticated wrapper that simplifies and robustifies the execution of the CHOPCHOP guide RNA design tool. It handles various input types (gene name, sequence, coordinates), manages CHOPCHOP's specific command-line arguments, and intelligently calls `simple_guide_finder.py` as a fallback.
    *   **Benefit:** Abstracts away the complexities of direct CHOPCHOP usage, provides error handling, and ensures a more consistent output format.
*   **`tools/simple_guide_finder.py`:** A lightweight, standalone script to find guide RNA candidates directly from a DNA sequence (including a library of common gene sequences like TP53). It's used as a primary tool for known genes or as a fallback.
    *   **Benefit:** Guarantees guide design capabilities even if CHOPCHOP or its dependencies are not fully functional on the user's system, ensuring greater reliability and speed for common targets.
*   **`tools/result_parser.py`:** Parses the extensive output files generated by CRISPResso2, extracting key metrics and structuring them into a format easily usable by the AI for summarization and Q&A.
    *   **Benefit:** Transforms raw, complex data into organized, machine-readable information, which is essential for the AI to provide meaningful interpretations.
*   **`tools/llm_api.py`:** The gateway to Large Language Model capabilities (e.g., Google's Gemini). This script handles API calls to the LLM, sending prompts and receiving generated text.
    *   **Benefit:** This is the "brain" of the AI assistance, enabling natural language understanding, conversational interaction, dynamic question generation, and intelligent summarization of results.

### The AI's Role: More Than Just Automation
The AI, powered by LLMs, is not just a passive script runner; it's an active participant in your research process:
*   **Conversational Guidance:** Instead of static help menus, the AI asks clarifying questions to gather necessary parameters, explains options, and confirms choices in a natural, interactive way.
*   **Contextual Explanations:** When presenting CHOPCHOP guides, it can explain the rationale behind scoring. For CRISPResso2 results, it puts numbers into biological context (e.g., explaining what a high frameshift rate implies for a knockout experiment).
*   **Dynamic Summarization:** It doesn't just display tables; it synthesizes information from multiple CRISPResso2 output files into a coherent narrative summary of the editing outcomes.
*   **Interactive Q&A:** You can ask follow-up questions about your results (e.g., "Which allele is the most common NHEJ product?", "What percentage of reads were perfectly repaired by HDR?"), and the AI will query the parsed data to provide answers.
*   **Intelligent Troubleshooting (Future Enhancement):** The AI can be trained to recognize common error patterns from tool outputs and suggest potential causes and solutions.

### Data Flow: An AI-Augmented Journey
1.  **Input & Configuration Phase:**
    *   User specifies their target (gene, sequence, or coordinates) and desired editing outcomes.
    *   **AI Assistant:** Asks clarifying questions, suggests appropriate parameters (e.g., enzyme, guide length for CHOPCHOP; FASTQ files, amplicon/guide sequences, analysis options for CRISPResso2), and confirms user inputs.
    *   **Benefit:** Reduces setup errors, ensures optimal parameter selection, and makes configuration more intuitive.
2.  **Guide Design Phase (CHOPCHOP / `simple_guide_finder`):**
    *   The system, via `chopchop_integration.py` or `simple_guide_finder.py`, generates a ranked list of potential guide RNAs.
    *   **AI Assistant:** Presents the top guides, can explain the scoring criteria (efficiency, specificity considerations), and helps the user select the best candidates.
    *   **Benefit:** Empowers informed decision-making by making guide selection criteria transparent.
3.  **Analysis Execution Phase (CRISPResso2):**
    *   User provides FASTQ files from their sequencing experiment.
    *   The system constructs and executes the appropriate CRISPResso2 command.
    *   **AI Assistant:** Manages the command execution, monitors progress (in Streamlit), and handles the output directory.
    *   **Benefit:** Automates the complex command-line interaction with CRISPResso2 and shields the user from execution details.
4.  **Results Parsing & Interpretation Phase:**
    *   `result_parser.py` processes the raw CRISPResso2 output.
    *   **AI Assistant:** Generates a natural language summary of key findings (editing efficiency, top alleles, frameshift rates, HDR/NHEJ breakdown). Facilitates a Q&A session where the user can interrogate their data.
    *   **Benefit:** Transforms raw, dense data into actionable knowledge and biological insights, dramatically speeding up the interpretation process.

## 🚀 Getting Started

### Prerequisites
*   Python 3.7+
*   Conda (recommended for managing CRISPResso2 and CHOPCHOP environments)
*   Access to an LLM API (e.g., Google Gemini API key)

### Installation
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-repo/crispr-ai-assistant.git # Replace with your actual repo URL
    cd crispr-ai-assistant
    ```
2.  **Set Up Python Environment & Dependencies:**
    ```bash
    # It's highly recommended to use a virtual environment
    python -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  **Configure API Keys:**
    *   Copy the example environment file: `cp .env.example .env`
    *   Edit the `.env` file and add your `GEMINI_API_KEY` and any other required API keys.
4.  **Install CHOPCHOP & CRISPResso2:**
    *   Follow the official installation instructions for [CHOPCHOP](https://chopchop.cbu.uib.no/) (especially for its dependencies like Bowtie) and [CRISPResso2](https://docs.crispresso.com/installation.html) (Bioconda is recommended).
    *   Ensure `CRISPResso` is in your PATH or in a known Conda environment. The assistant can run CRISPResso2 within a specified Conda environment.
    *   For CHOPCHOP, ensure the paths in `tools/chopchop/config_local.json` (or that you generate one via the assistant) point to your local genome resource files (e.g., `.2bit` files, Bowtie indices).

### Running the AI Research Assistant

*   **Streamlit Web Application (Recommended for interactive use):**
    ```bash
    streamlit run streamlit_app.py
    ```
    Open your web browser to the URL provided by Streamlit (usually `http://localhost:8501`).

*   **Command-Line Interface (For quick tasks or scripting):**
    ```bash
    python ai_research_assistant.py
    ```
    Follow the conversational prompts.

## 📊 Example Output: TP53 Guide Design

When designing guides for the TP53 gene, the assistant (leveraging `simple_guide_finder.py` or CHOPCHOP) might present results like:

```
Found 42 guide RNAs for TP53
1. TGAAGCTCCCAGAATGCCAGAGG - Score: 1.0
2. GCAGTCACAGCACATGACGGAGG - Score: 1.0
3. AGCACATGACGGAGGTTGTGAGG - Score: 1.0
4. TCCTCAGCATCTTATCCGAGTGG - Score: 1.0
5. AGTGGAAGGAAATTTGCGTGTGG - Score: 1.0
... (other guides) ...
```
The AI can then help you understand these scores and choose the best guide for your experiment.

## 📚 Learn More & Cite
*   **CHOPCHOP:** [Website](https://chopchop.cbu.uib.no/), [Publication](https://academic.oup.com/nar/article/47/W1/W232/5470081)
*   **CRISPResso2:** [Documentation](https://docs.crispresso.com), [Publication](https://www.nature.com/articles/s41587-019-0237-2)
*   **Principles of CRISPR Genome Editing:** A good review, e.g., [Nature Reviews Genetics](https://www.nature.com/articles/nrg.2017.116)

## 📞 Support & Contribution
For questions, bug reports, or feature requests, please [open an issue](https://github.com/your-repo/crispr-ai-assistant/issues) on our GitHub repository. Contributions to enhance the assistant are welcome!

---

*This AI Research Assistant is developed by a dedicated team aiming to fuse the power of AI with cutting-edge bioinformatics to accelerate breakthroughs in genome editing.*
