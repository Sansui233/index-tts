#!/usr/bin/env python3
"""
Entry point wrapper for IndexTTS WebUI2
This ensures proper import paths before launching the main application
"""
import os
import sys

# Add current directory to Python path for webui2 imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now we can import and run the main application
if __name__ == "__main__":
    from webui2.main import main
    main()
