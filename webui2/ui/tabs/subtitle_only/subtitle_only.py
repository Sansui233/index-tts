"""
Subtitle-only generation tab
"""

import glob
import os

import gradio as gr

from webui2.utils import SubtitleManager

from ....config import SAMPLES_DIR


def create_subtitle_only_tab_page():
    subtitle_manager = SubtitleManager.get_instance()
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
            audio = gr.Audio(
                label="上传音频文件",
                type="filepath",
                sources=["upload", "microphone"],
            )

            with gr.Row():
                subtitle_model = gr.Dropdown(
                    choices=["tiny", "base", "small", "medium"],
                    value="base",
                    label="字幕模型",
                )
                lang = gr.Dropdown(
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
                audio,
                subtitle_model,
                lang,
            ],
            label="示例文件",
        )
    else:
        gr.Markdown("> 提示：您可以在 `samples` 目录中添加音频文件作为示例")

    gen_subtitle_button.click(
        fn=subtitle_manager.generate_subtitle_only,
        inputs=[
            audio,
            subtitle_model,
            lang,
        ],
        outputs=[
            output_subtitle,
            status_message,
        ],
    )

    return
