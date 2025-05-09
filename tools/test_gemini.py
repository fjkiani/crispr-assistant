#!/usr/bin/env python
"""
Test script to verify that the Gemini API is working correctly.
"""
import os
import sys
from dotenv import load_dotenv

try:
    # Try to load environment variables from .env file
    load_dotenv()
    print("Loaded .env file")
    
    # Check if GEMINI_API_KEY is set
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("WARNING: GEMINI_API_KEY is not set or has default value.")
        print("Please set a valid API key in the .env file.")
        sys.exit(1)
    
    # Import Google Generative AI
    import google.generativeai as genai
    
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    
    # Get available models
    print("Available models:")
    for m in genai.list_models():
        print(f"- {m.name}")
    
    # Test a simple query with Gemini Pro
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("Say hello and explain what CRISPR is in one sentence.")
    
    print("\nTest response from Gemini:")
    print(response.text)
    print("\nGemini API is working correctly!")
    
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Make sure you've installed the necessary packages:")
    print("pip install python-dotenv google-generativeai")
    sys.exit(1)
except Exception as e:
    print(f"Error testing Gemini API: {e}")
    sys.exit(1) 