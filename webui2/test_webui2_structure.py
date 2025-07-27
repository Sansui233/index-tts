#!/usr/bin/env python3
"""
Test script to validate the refactored webui2 structure
"""

import importlib.util
import os
import sys


def test_module_structure():
    """Test if all modules can be imported"""
    modules_to_test = [
        "webui2.config.settings",
        "webui2.utils.helpers",
        "webui2.ui.components",
        "webui2.ui.tabs.single_audio",
        "webui2.ui.tabs.multi_dialog",
        "webui2.ui.tabs.subtitle_only",
    ]

    print("Testing module structure...")

    for module_name in modules_to_test:
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                print(f"✓ {module_name} - Found")
            else:
                print(f"✗ {module_name} - Not found")
        except Exception as e:
            print(f"✗ {module_name} - Error: {e}")

    # Test directory structure
    print("\nTesting directory structure...")
    directories = [
        "../webui2",
        "../webui2/config",
        "../webui2/audio",
        "../webui2/ui",
        "../webui2/ui/tabs",
        "../webui2/utils",
    ]

    for directory in directories:
        if os.path.exists(directory):
            print(f"✓ {directory}/ - Exists")
        else:
            print(f"✗ {directory}/ - Missing")

    # Test key files
    print("\nTesting key files...")
    files = [
        "../webui2/__init__.py",
        "../webui2/main.py",
        "../webui2/config/__init__.py",
        "../webui2/config/settings.py",
        "../webui2/audio/__init__.py",
        "../webui2/ui/__init__.py",
        "../webui2/ui/components.py",
        "../webui2/ui/handlers.py",
        "../webui2/utils/__init__.py",
    ]

    for file_path in files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} - Exists")
        else:
            print(f"✗ {file_path} - Missing")


if __name__ == "__main__":
    test_module_structure()
