#!/usr/bin/env python3
"""
IndexTTS WebUI - Refactored modular version
Main entry point for the web interface
"""

import os
import warnings
import webbrowser
from threading import Timer

import gradio as gr

from webui2.audio import SubtitleManager, TTSManager

# Setup environment and imports
from webui2.config import (
    parse_arguments,
    set_ffmpeg_path,
    setup_directories,
    setup_python_path,
    validate_model_files,
)
from webui2.ui.components.common import create_header
from webui2.ui.handlers import (
    gen_multi_dialog_audio,
)
from webui2.ui.tabs import *
from webui2.utils import install_required_packages

# Initialize environment
set_ffmpeg_path()
setup_python_path()

# Set up warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Install required packages
install_required_packages()

# Parse arguments and validate setup
cmd_args = parse_arguments()
validate_model_files(cmd_args.model_dir)
setup_directories()

# Initialize managers
tts_manager = TTSManager(cmd_args.model_dir, os.path.join(cmd_args.model_dir, "config.yaml"))
subtitle_manager = SubtitleManager()

# read styles.css as string as it is used in the create_webui function
with open(os.path.join("webui2", "ui", "styles", "style.css"), "r", encoding="utf-8") as f:
    styles_css = f.read()


def create_webui():
    """Create the main web UI"""
    with gr.Blocks(title="IndexTTS Demo", css=styles_css) as demo:
        # Header
        create_header()

        # Single Audio Tab
        with gr.Tab("音频生成"):
            create_single_audio_tab_page(tts_manager, subtitle_manager)

        # Multi-Dialog Tab
        with gr.Tab("多人对话"):
            create_multi_dialog_tab_page(tts_manager)

        # Subtitle-Only Tab
        with gr.Tab("单独生成字幕"):
            subtitle_only_components = create_subtitle_only_tab_page()

            # Set up event handlers for subtitle-only tab
            subtitle_only_components["controls"]["gen_subtitle_button"].click(
                fn=subtitle_manager.generate_subtitle_only,
                inputs=[
                    subtitle_only_components["inputs"]["input_audio_subtitle"],
                    subtitle_only_components["inputs"]["model_choice_subtitle"],
                    subtitle_only_components["inputs"]["subtitle_lang_subtitle"],
                ],
                outputs=[
                    subtitle_only_components["outputs"]["output_subtitle"],
                    subtitle_only_components["outputs"]["status_message"],
                ],
            )

    return demo


def main():
    """Main function to run the web UI"""
    demo = create_webui()
    demo.queue(20)

    url = f"http://{cmd_args.host}:{cmd_args.port}"

    def open_browser():
        webbrowser.open(url)

    Timer(2, open_browser).start()
    demo.launch(server_name=cmd_args.host, server_port=cmd_args.port)


if __name__ == "__main__":
    main()
