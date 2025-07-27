#!/usr/bin/env python3
"""
Launcher script for IndexTTS WebUI2
This script ensures proper import paths and launches the modularized webui2
"""
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import and run the main application
from webui2.main import main

if __name__ == "__main__":
    main()
