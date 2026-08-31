# -*- coding: utf-8 -*-
"""
config.py
=========
Central configuration for Recallis.

All tuneable constants live here so they can be changed in one place
without hunting through multiple files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
ROOT_DIR = Path(__file__).parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# API Keys (loaded from environment — never hardcoded)
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# LLM Settings
# ---------------------------------------------------------------------------
GROQ_MODEL = "qwen/qwen3.8-27b"
GROQ_TEMPERATURE = 0          # Always 0 for structured output
GROQ_MAX_TOKENS = 1024

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
WORKFLOWS_FILE = ROOT_DIR / "data" / "workflows.json"

# ---------------------------------------------------------------------------
# Teach settings
# ---------------------------------------------------------------------------
TEACH_MAX_RETRIES = 2         # How many times to retry invalid LLM output
