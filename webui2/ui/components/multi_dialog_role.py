import os

import gradio as gr

from ...utils import server_audio_manager


def load_server_audio(server_audio_path):
    """Load server audio file into the audio component"""
    if server_audio_path and os.path.exists(server_audio_path):
        return gr.update(value=server_audio_path)
    return gr.update()


def create_role(default_name: str = "角色1") -> tuple:
    with gr.Row(elem_classes="multi_dialog-roles"):
        gr_name = gr.Textbox(
            label="角色名称",
            value=default_name,
            interactive=True,
            elem_classes=["multi_dialog-role_name"],
        )
        gr_server_audio = gr.Dropdown(
            label="选择服务器音频",
            choices=server_audio_manager.get_flat_audio_choices(),
            value="",
            interactive=True,
            allow_custom_value=False,
        )
        gr_audio = gr.Audio(
            label="参考音频",
            key=default_name + "_audio",
            sources=["upload", "microphone"],
            type="filepath",
        )
    gr_server_audio.change(
        fn=load_server_audio, inputs=[gr_server_audio], outputs=[gr_audio]
    )
    return (gr_name, gr_server_audio, gr_audio)
