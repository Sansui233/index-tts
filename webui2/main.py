#!/usr/bin/env python3
"""
IndexTTS WebUI - Refactored modular version
Main entry point for the web interface
"""

import os
import threading
import warnings
import webbrowser
from threading import Timer

import gradio as gr
import numpy as np

from webui2.audio import SubtitleManager, TTSManager

# Setup environment and imports
from webui2.config import (
    parse_arguments,
    set_ffmpeg_path,
    setup_directories,
    setup_python_path,
    validate_model_files,
)
from webui2.ui import (
    create_header,
    create_multi_dialog_tab,
    create_single_audio_tab,
    create_subtitle_only_tab,
    gen_multi_dialog,
    gen_single,
    on_input_text_change,
    update_prompt_audio,
)
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
tts_manager = TTSManager(
    cmd_args.model_dir, os.path.join(cmd_args.model_dir, "config.yaml")
)
subtitle_manager = SubtitleManager()


def create_webui():
    """Create the main web UI"""
    with gr.Blocks(title="IndexTTS Demo") as demo:
        mutex = threading.Lock()

        # Header
        create_header()

        # Single Audio Tab
        with gr.Tab("音频生成"):
            single_audio_components = create_single_audio_tab(tts_manager)

            # Set up event handlers for single audio tab
            single_audio_components["controls"]["gen_button"].click(
                fn=lambda *args: gen_single(
                    tts_manager.get_tts(), subtitle_manager, *args
                ),
                inputs=[
                    single_audio_components["inputs"]["prompt_audio"],
                    single_audio_components["inputs"]["input_text_single"],
                    single_audio_components["inputs"]["infer_mode"],
                    single_audio_components["inputs"]["max_text_tokens_per_sentence"],
                    single_audio_components["inputs"]["sentences_bucket_max_size"],
                    *single_audio_components["advanced_params"],
                    single_audio_components["inputs"]["gen_subtitle"],
                    single_audio_components["inputs"]["model_choice"],
                    single_audio_components["inputs"]["subtitle_lang"],
                    single_audio_components["inputs"]["bgm_upload"],
                    single_audio_components["inputs"]["bgm_volume"],
                    single_audio_components["inputs"]["bgm_loop"],
                    single_audio_components["inputs"]["additional_bgm"],
                ],
                outputs=[
                    single_audio_components["outputs"]["output_audio"],
                    single_audio_components["outputs"]["subtitle_output"],
                ],
            )

            # Text change handler for sentence preview
            single_audio_components["inputs"]["input_text_single"].change(
                lambda text, max_tokens: on_input_text_change(
                    tts_manager.get_tts(), text, max_tokens
                ),
                inputs=[
                    single_audio_components["inputs"]["input_text_single"],
                    single_audio_components["inputs"]["max_text_tokens_per_sentence"],
                ],
                outputs=[single_audio_components["sentences_preview"]],
            )

            single_audio_components["inputs"]["max_text_tokens_per_sentence"].change(
                lambda text, max_tokens: on_input_text_change(
                    tts_manager.get_tts(), text, max_tokens
                ),
                inputs=[
                    single_audio_components["inputs"]["input_text_single"],
                    single_audio_components["inputs"]["max_text_tokens_per_sentence"],
                ],
                outputs=[single_audio_components["sentences_preview"]],
            )

            single_audio_components["inputs"]["prompt_audio"].upload(
                update_prompt_audio,
                inputs=[],
                outputs=[single_audio_components["controls"]["gen_button"]],
            )

        # Multi-Dialog Tab
        with gr.Tab("多人对话(读小说也行)"):
            multi_dialog_components = create_multi_dialog_tab(tts_manager)

            # Set up event handlers for multi-dialog tab
            multi_dialog_components["controls"]["gen_button_multi"].click(
                fn=lambda *args: gen_multi_dialog(
                    tts_manager.get_tts(), subtitle_manager, *args
                ),
                inputs=[
                    multi_dialog_components["inputs"]["speakers"]["speaker1_name"],
                    multi_dialog_components["inputs"]["speakers"]["speaker1_audio"],
                    multi_dialog_components["inputs"]["speakers"]["speaker2_name"],
                    multi_dialog_components["inputs"]["speakers"]["speaker2_audio"],
                    multi_dialog_components["inputs"]["speakers"]["speaker3_name"],
                    multi_dialog_components["inputs"]["speakers"]["speaker3_audio"],
                    multi_dialog_components["inputs"]["speakers"]["speaker4_name"],
                    multi_dialog_components["inputs"]["speakers"]["speaker4_audio"],
                    multi_dialog_components["inputs"]["speakers"]["speaker5_name"],
                    multi_dialog_components["inputs"]["speakers"]["speaker5_audio"],
                    multi_dialog_components["inputs"]["speakers"]["speaker6_name"],
                    multi_dialog_components["inputs"]["speakers"]["speaker6_audio"],
                    multi_dialog_components["inputs"]["dialog_text"],
                    multi_dialog_components["inputs"]["interval"],
                    # Advanced params from the tab
                    *multi_dialog_components["advanced_params"],
                    multi_dialog_components["inputs"]["gen_subtitle_multi"],
                    multi_dialog_components["inputs"]["model_choice_multi"],
                    multi_dialog_components["inputs"]["subtitle_lang_multi"],
                    multi_dialog_components["inputs"]["bgm_upload_multi"],
                    multi_dialog_components["inputs"]["bgm_volume_multi"],
                    multi_dialog_components["inputs"]["bgm_loop_multi"],
                    multi_dialog_components["inputs"]["additional_bgm_multi"],
                ],
                outputs=[
                    multi_dialog_components["outputs"]["output_audio_multi"],
                    multi_dialog_components["outputs"]["subtitle_output_multi"],
                ],
            )

        # Subtitle-Only Tab
        with gr.Tab("单独生成字幕"):
            subtitle_only_components = create_subtitle_only_tab()

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
