import os
from pathlib import Path

import gradio as gr

from webui2.utils import server_audio_mgr


class RoleSessionState:
    _path_state = []  # key: i, value: audio_server_path: str | None

    def use_path_state(self, i: int, audio_server_path: str | None):
        is_server = server_audio_mgr.is_server_audio(audio_server_path)

        if i < len(self._path_state):
            if is_server:
                self._path_state[i] = audio_server_path
                # print(f"[webui2] [Debug] 用户更新音频 {i}")
                return audio_server_path
            else:
                # return existing state
                # print(f"[webui2] [Debug] 被 gr.render 刷新了 {i}")
                return self._path_state[i]
        else:
            # add new state, 因为调用总是 1 到 i，直接 append 不会有顺序问题
            if is_server:
                # print(f"[webui2] [Debug] 添加缓存 {i} path")
                self._path_state.append(audio_server_path)
                return audio_server_path
            else:
                # print(f"[webui2] [Debug] 添加缓存 {i} None")
                self._path_state.append(None)
                return None

    def truncate_path_state(self, length: int):
        if length < len(self._path_state):
            del self._path_state[length:]


def create_role(
    speakers_data: list,
    i: int,
    speaker_data: tuple,
    role_session_state: gr.State,
):
    name, audioPath = speaker_data
    audio_name = Path(audioPath).name if audioPath else None

    # 需要 server_audio 的 value 不被动态渲染覆盖成不存在的选项
    role_st_server_audio = role_session_state.value.use_path_state(i, audioPath)

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
                choices=server_audio_mgr.get_flat_audio_choices(),
                key=f"speaker{i}_select_{role_st_server_audio}",
                value=role_st_server_audio,
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

        def load_server_audio(server_audio_path):
            """Load server audio file into the audio component"""
            if server_audio_path and os.path.exists(server_audio_path):
                print(f"[webui2] [Debug] Loading server audio: {server_audio_path}")
                role_session_state.value.use_path_state(
                    i, server_audio_path
                )  # 更新缓存
                return server_audio_path
            return

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
