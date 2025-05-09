# AI Research Assistant for CRISPR Tools

This AI Research Assistant helps users interact with CRISPR gene editing tools like CHOPCHOP and CRISPResso2. It uses Google's Gemini API to provide intelligent, conversational assistance.

## Setup Instructions

### 1. Install Dependencies

Make sure you have Python 3.7+ installed, then install the required packages:

```bash
pip install python-dotenv google-generativeai langchain openai
```

### 2. Get a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an account if you don't have one
3. Generate an API key

### 3. Configure the API Key

1. Open the `.env` file in the project root
2. Replace the placeholder with your actual Gemini API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

### 4. Test the Gemini API

Run the test script to verify your API key works:

```bash
python tools/test_gemini.py
```

You should see a list of available models and a test response from Gemini.

### 5. Run the AI Research Assistant

Start the assistant with:

```bash
python ai_research_assistant.py
```

## Using the AI Research Assistant

The assistant can help with:

1. **Configure CHOPCHOP**: Set up the local configuration for CHOPCHOP
   - Example command: "configure chopchop"

2. **Design Guides**: Design guide RNAs with CHOPCHOP
   - Example command: "design guides" or "run chopchop"

3. **Analyze CRISPResso Data**: Run CRISPResso2 analysis on FASTQ files
   - Example command: "analyze crispresso" or "run crispresso"

4. **Interpret CRISPResso Results**: Understand the results of your CRISPResso2 analysis
   - Example command: "interpret crispresso results"

5. **General Help**: Get assistance with CRISPR concepts and tools
   - Ask any question about CRISPR, CHOPCHOP, or CRISPResso2

## Troubleshooting

- **API Key Issues**: Make sure your Gemini API key is correctly entered in the `.env` file
- **Import Errors**: Ensure all required packages are installed
- **Path Issues**: If you see path-related errors, check that the project directory structure is correct

## Directory Structure

```
CRISPResso2-master/
├── ai_research_assistant.py   # Main assistant script
├── .env                       # Environment variables (API keys)
├── tools/
│   ├── llm_api.py             # LLM API interface
│   ├── test_gemini.py         # Test script for Gemini API
│   └── chopchop/              # CHOPCHOP tool directory
├── chopchop_output/           # Output directory for CHOPCHOP results
└── README_AI_ASSISTANT.md     # This README
``` 