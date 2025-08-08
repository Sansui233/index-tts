import os
from pathlib import Path

import gradio as gr

from webui2.utils import server_audio_manager


def create_role(
    speakers_data: list,
    i: int,
    speaker_data: tuple = (None, None),
):
    name, audioPath = speaker_data
    audio_name = Path(audioPath).name if audioPath else None
    if name is None:
        name = f"角色{i + 1}"
    with gr.Column(elem_classes="multi_dialog-roles"):
        with gr.Row(scale=1):
            gr_name = gr.Textbox(
                label="角色名称",
                key=f"speaker{i}_{name}",
                value=f"{name}",
                interactive=True,
                elem_classes=["multi_dialog-role_name"],
                scale=1,
                min_width=100,
            )
            gr_server_audio = gr.Dropdown(
                label="选择服务器音频",
                choices=server_audio_manager.get_flat_audio_choices(),
                key=f"speaker{i}_select_{audio_name}",
                value=audioPath,
                interactive=True,
                allow_custom_value=False,
                scale=2,
            )
        gr_audio = gr.Audio(
            label="参考音频",
            sources=["upload", "microphone"],
            key=f"speaker{i}_{audio_name}",
            value=audioPath,
            type="filepath",
            interactive=True,
        )

        def set_change(name, audio_path):
            """Set the speaker data when name or audio changes"""
            speakers_data[i] = (name, audio_path)

        gr_name.blur(
            fn=set_change,
            inputs=[gr_name, gr_audio],
        )

        gr_server_audio.change(
            fn=load_server_audio,
            inputs=[gr_server_audio],
            outputs=[gr_audio],
        )
        gr_audio.change(
            fn=set_change,
            inputs=[gr_name, gr_audio],
        )

    return (gr_name, gr_server_audio, gr_audio)


def load_server_audio(server_audio_path):
    """Load server audio file into the audio component"""
    if server_audio_path and os.path.exists(server_audio_path):
        print(f"[webui2] [Debug] Loading server audio: {server_audio_path}")
        return server_audio_path
    return
