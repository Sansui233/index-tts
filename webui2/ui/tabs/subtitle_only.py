"""
Subtitle-only generation tab
"""

import glob
import os

import gradio as gr

from ...config import SAMPLES_DIR


def create_subtitle_only_tab_page():
    """Create the subtitle-only generation tab"""
    gr.Markdown("上传音频文件，然后选择模型和语言来生成字幕文件。")

    # Get sample files for examples
    sample_files = []
    for ext in [".wav", ".mp3", ".flac"]:
        sample_files.extend(glob.glob(os.path.join(SAMPLES_DIR, f"*{ext}")))

    sample_examples = []
    for file in sample_files[:1]:
        sample_examples.append([file, "base", "zh (中文)"])

    with gr.Row():
        with gr.Column():
            input_audio_subtitle = gr.Audio(
                label="上传音频文件",
                type="filepath",
                sources=["upload", "microphone"],
            )

            with gr.Row():
                model_choice_subtitle = gr.Dropdown(
                    choices=["tiny", "base", "small", "medium"],
                    value="base",
                    label="字幕模型",
                )
                subtitle_lang_subtitle = gr.Dropdown(
                    choices=["zh (中文)", "en (英文)", "ja (日语)", "ko (韩语)"],
                    value="zh (中文)",
                    label="字幕语言",
                )

            gen_subtitle_button = gr.Button("生成字幕", variant="primary")
            status_message = gr.Textbox(label="状态", interactive=False)

        with gr.Column():
            output_subtitle = gr.File(
                label="生成的字幕文件", visible=True, interactive=False
            )

    # Add examples if available
    if sample_examples:
        gr.Examples(
            examples=sample_examples,
            inputs=[
                input_audio_subtitle,
                model_choice_subtitle,
                subtitle_lang_subtitle,
            ],
            label="示例文件",
        )
    else:
        gr.Markdown("> 提示：您可以在 `samples` 目录中添加音频文件作为示例")

    return {
        "inputs": {
            "input_audio_subtitle": input_audio_subtitle,
            "model_choice_subtitle": model_choice_subtitle,
            "subtitle_lang_subtitle": subtitle_lang_subtitle,
        },
        "outputs": {
            "output_subtitle": output_subtitle,
            "status_message": status_message,
        },
        "controls": {
            "gen_subtitle_button": gen_subtitle_button,
        },
    }
