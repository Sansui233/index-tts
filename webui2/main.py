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

# Setup environment and imports
from webui2.config import (
    parse_arguments,
    set_ffmpeg_path,
    setup_directories,
    setup_python_path,
    validate_model_files,
)
from webui2.ui.common import create_header
from webui2.ui.tabs import (
    create_multi_dialog_tab_page,
    create_single_audio_tab_page,
    create_subtitle_only_tab_page,
)
from webui2.utils import SubtitleManager, TTSManager

# Initialize environment
set_ffmpeg_path()
setup_python_path()

# Set up warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# Parse arguments and validate setup
cmd_args = parse_arguments()
validate_model_files(cmd_args.model_dir)
setup_directories()

# Initialize managers
tts_mgr = TTSManager(
    cmd_args.model_dir, os.path.join(cmd_args.model_dir, "config.yaml")
)
subtitle_mgr = SubtitleManager()


def create_webui():
    """Create the main web UI"""
    with gr.Blocks(
        title="IndexTTS Demo",
        css_paths=os.path.join("webui2", "ui", "styles", "style.css"),
    ) as demo:
        create_header()
        with gr.Tab("音频生成"):
            create_single_audio_tab_page(tts_mgr, subtitle_mgr)
        with gr.Tab("多人对话"):
            create_multi_dialog_tab_page(tts_mgr, subtitle_mgr)
        with gr.Tab("单独生成字幕"):
            create_subtitle_only_tab_page(subtitle_mgr)

        # Gradio 这版本有 bug，首页不渲染个 Textbox 导致后面的 Textbox 渲染不出来
        gr.Textbox(label="444", visible=True, lines=1, elem_classes="display-none")

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
