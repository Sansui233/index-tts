#!/usr/bin/env python3
"""
IndexTTS WebUI - Refactored modular version
Main entry point for the web interface
"""

import os
import warnings
import webbrowser
from pathlib import Path
from threading import Timer
from time import time

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
    create_help,
    create_multi_dialog_tab_page,
    create_single_audio_tab_page,
    create_subtitle_only_tab_page,
)
from webui2.ui.tabs.multi_dialog.role import RoleSessionState
from webui2.utils import TTSManager

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

# Singleton managers is automatically initialized
# But args must be set before creating the instance
TTSManager.set_initialize_args(
    cmd_args.model_dir, os.path.join(cmd_args.model_dir, "config.yaml")
)


def create_webui():
    with gr.Blocks(
        title="IndexTTS WebUI2",
        css_paths=os.path.join("webui2", "ui", "styles", "style.css"),
    ) as demo:
        session = gr.State("")
        role_session_state = gr.State(RoleSessionState())

        create_header()
        with gr.Tab("音频生成"):
            create_single_audio_tab_page(session)
        with gr.Tab("多人对话"):
            create_multi_dialog_tab_page(session, role_session_state)
        with gr.Tab("单独生成字幕"):
            create_subtitle_only_tab_page(session)
        with gr.Tab("使用说明"):
            create_help()

        # Gradio 这版本有 bug，首页不渲染个 Textbox 导致后面的 Textbox 渲染不出来
        gr.Textbox(label="444", visible=True, lines=1, elem_classes="display-none")

        demo.load(fn=lambda: str(time()), inputs=None, outputs=session)

    return demo


def main():
    """Main function to run the web UI"""
    gr.set_static_paths(Path.cwd().absolute() / "webui2" / "assets")
    demo = create_webui()
    demo.queue(20)

    url = f"http://{cmd_args.host}:{cmd_args.port}"

    def open_browser():
        webbrowser.open(url)

    Timer(2, open_browser).start()
    demo.launch(server_name=cmd_args.host, server_port=cmd_args.port)


if __name__ == "__main__":
    main()
