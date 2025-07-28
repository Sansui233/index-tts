import os

import gradio as gr

from webui2.utils import server_audio_manager


def create_role(i=1):
    with gr.Column(elem_classes="multi_dialog-roles"):
        with gr.Row(scale=1):
            gr_name = gr.Textbox(
                label="角色名称",
                key=f"speaker{i}_name",
                value=f"角色{i}",
                interactive=True,
                elem_classes=["multi_dialog-role_name"],
                scale=1,
            )
            gr_server_audio = gr.Dropdown(
                label="选择服务器音频",
                key=f"speaker{i + 1}_server_audio",
                choices=server_audio_manager.get_flat_audio_choices(),
                value="",
                interactive=True,
                allow_custom_value=False,
                scale=2,
            )
        gr_audio = gr.Audio(
            label="参考音频",
            key=f"speaker{i}_name_audio",
            sources=["upload", "microphone"],
            type="filepath",
        )

    gr_server_audio.change(
        fn=load_server_audio, inputs=[gr_server_audio], outputs=[gr_audio]
    )

    return (gr_name, gr_server_audio, gr_audio)


def load_server_audio(server_audio_path):
    """Load server audio file into the audio component"""
    if server_audio_path and os.path.exists(server_audio_path):
        print(f"[webui2] [Debug] Loading server audio: {server_audio_path}")
        return gr.update(value=server_audio_path)
    return gr.update()
