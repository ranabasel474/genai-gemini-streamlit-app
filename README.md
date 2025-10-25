# genai-gemini-streamlit-app

A compact Streamlit demo that shows how to integrate GenAI (e.g., Google Gemini / Vertex AI) models into an interactive Python app.

## Overview
- Language: Python (100%)
- Purpose: Rapid prototyping of LLM-powered UIs and simple chat flows
- Minimal, easy-to-extend example for local experimentation

## Features
- Streamlit UI for sending prompts and viewing responses
- Simple in-memory conversation state for quick testing
- Configurable model via environment variables

## Quickstart
1. Clone the repo
   git clone https://github.com/ranabasel474/genai-gemini-streamlit-app.git
   cd genai-gemini-streamlit-app

2. Create and activate a virtual environment
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1

3. Install dependencies
   pip install -r requirements.txt

4. Configure credentials and model (examples)
   - GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   - GEMINI_MODEL="gemini-pro"

5. Run
   streamlit run app.py
   Open http://localhost:8501

## Configuration notes
- Keep API keys out of source control. Use a .env or secret manager.
- Change GEMINI_MODEL to try different model variants.

## Project layout (typical)
- app.py — Streamlit entrypoint
- requirements.txt — Python dependencies
