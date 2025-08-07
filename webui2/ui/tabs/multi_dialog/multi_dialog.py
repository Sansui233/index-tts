"""
Multi-dialog generation tab
"""

import os
import webbrowser

import gradio as gr

from webui2.ui.common import (
    create_advanced_params_accordion,
    create_bgm_accordion,
    create_subtitle_controls,
)
from webui2.ui.handlers.generate import (
    gen_multi_dialog_audio,
)
from webui2.ui.js.notify import notify_done
from webui2.ui.tabs.multi_dialog.multi_dialog_templist import create_temp_list
from webui2.utils import SubtitleManager, TTSManager

from .multi_dialog_presets import (
    create_multi_dialog_presets,
    on_delete_preset_click,
    on_load_preset_click,
    on_save_preset_click,
)
from .multi_dialog_role import create_role


def create_multi_dialog_tab_page(session: gr.State):
    tts_manager = TTSManager.get_instance()
    subtitle_manager = SubtitleManager.get_instance()

    """Create the multi-dialog generation tab"""

    with gr.Row(elem_id="multi-dialog"):
        # navigation section
        with gr.Column(elem_id="sidebar-anchors", scale=1):
            gr.HTML('<a href="#anchor-multi_dialog_roles"><h3">🗣️ 角色配置<h3></a>')
            gr.HTML('<a href="#anchor-dialog_text"><h3">💬 对话<h3></a>')
            gr.HTML('<a href="#subtitle-controls"><h3">🎬 字幕<h3></a>')
            gr.HTML('<a href="#bgm-accordion""><h3">🎵 背景音乐<h3></a>')
            gr.HTML('<a href="#advanced-params""><h3">⚙️ 高级参数<h3></a>')
            gr.HTML('<a href="#anchor-temp-list"><h3">🗂️ 对话列表 <h3></a>')

        # Speaker configuration rows
        with gr.Column(scale=9):
            # preset part
            gr.Markdown("### 预设", elem_id="anchor-multi_dialog_presets")
            (
                preset_dropdown,
                load_preset_btn,
                preset_name_input,
                save_preset_btn,
                delete_preset_btn,
            ) = create_multi_dialog_presets()

            # roles part
            gr.Markdown(
                "### 🗣️ 角色配置（必填） \n 为每个角色选择或上传音频，然后在下方填写对话内容。",
                elem_id="anchor-multi_dialog_roles",
            )

            # speaker_count 其实必须和 speaker_data 同步
            # save_preset_btn 和 multi_gen_button 都单独需要 speaker_data
            st_speaker_count = gr.State(2)
            st_speakers_data = gr.State(
                [("角色1", None), ("角色2", None)]
            )  # List of (Name, AudioPathOnServer)

            @gr.render(inputs=(st_speakers_data))
            def render_roles(speakers_data: list[tuple]):
                gr_speakers = []  # length: count * 3, tuple[Textbox, Dropdown, Audio]

                with gr.Row():
                    for i in range(0, len(speakers_data)):
                        gr_speakers.extend(
                            create_role(speakers_data, i + 1, speakers_data[i])
                        )

                bind_save_preset_click(gr_speakers)
                bind_multi_gen_click(gr_speakers)

            # Add and Remove Role Buttons
            with gr.Row():
                add_role_btn = gr.Button("添加角色", elem_id="add-role-btn")
                remove_role_btn = gr.Button("删除角色", elem_id="remove-role-btn")

            # dialog part
            gr.Markdown("### 💬 对话内容（必填）", elem_id="anchor-dialog_text")
            dialog_text = gr.TextArea(
                label="对话内容",
                placeholder="（使用以下对话格式）:\n[角色1]你在干什么？\n[角色2]我什么也没干呀。\n[角色1]那你拿刀干什么？\n[角色2]我只是想要切菜。",
                lines=8,
                interactive=True,
            )

            interval = gr.Slider(
                label="对话间隔(秒)",
                minimum=0.1,
                maximum=2.0,
                value=0.5,
                step=0.1,
                info="不同角色之间的间隔时间",
                interactive=True,
            )

            # output part
            with gr.Row(elem_id="multi-dialog-output"):
                gr.Markdown("### 生成结果", elem_classes=["flex-auto"])
                multi_output_audio = gr.Audio(
                    label="对话生成结果",
                    visible=True,
                    key="multi_output_audio",
                    elem_id="output-audio",
                    interactive=False,
                    scale=2,
                )
                multi_subtitle_output = gr.File(
                    label="字幕文件",
                    visible=True,
                    elem_id="output-subtitle",
                    interactive=False,
                    scale=2,
                )
                multi_gen_button = gr.Button(
                    "生成对话",
                    key="multi_gen_button",
                    elem_classes=["flex-auto", "bg-accent"],
                    interactive=True,
                )
                open_output_folder = gr.Button(
                    "打开输出目录",
                    key="open_output_folder",
                    elem_classes=["flex-auto"],
                    interactive=True,
                )
            example_dialog = """[角色1]你听说过那个一动不动的鸭子吗？
[角色2]没听说过，它怎么了？
[角色1]它一点也不呱噪，叫“哑”子。
[角色3]哈哈，这笑话真冷，适合冬天讲。
[角色4]你确定不是适合放冰箱里？
[角色2]不行，我笑出鹅叫了。
[角色1]那是你隔壁那只真鹅。"""

            gr.Examples(
                examples=[[example_dialog]],
                inputs=[dialog_text],
                label="示例对话",
                elem_id="anchor-examples",
            )

            gen_subtitle, subtitle_model, subtitle_lang = create_subtitle_controls()
            # Example dialog

            # Advanced parameters
            bgm_upload, bgm_volume, bgm_loop, additional_bgm = create_bgm_accordion()

            (
                do_sample, top_p, top_k, temperature, length_penalty, num_beams, repetition_penalty, max_mel_tokens,
                max_text_tokens_per_sentence,sentences_bucket_max_size,sentences_preview,
            ) = create_advanced_params_accordion(tts_manager)  # fmt: skip

            advanced_params = [
                do_sample, top_p, top_k,
                temperature, length_penalty, num_beams,
                repetition_penalty, max_mel_tokens,
            ]  # fmt: skip

            gr.Markdown(value="\n\n---")
            # Solve dynamic params passing problem with proxy state + hidden button + js click
            pick_args_proxy = gr.State([])
            with gr.Row():
                md_session = gr.Markdown(value=f"当前为初始 Session {session.value}")
                collect_btn = gr.Button(
                    value="同步对话参数",
                    visible=True,
                    elem_id="collect-btn",
                )

                collect_btn.click(
                    fn=collect_pick_args,
                    inputs=[
                        st_speakers_data,
                        gr.State("普通推理"),
                        do_sample,
                        top_p,
                        top_k,
                        temperature,
                        length_penalty,
                        num_beams,
                        repetition_penalty,
                        max_mel_tokens,
                        max_text_tokens_per_sentence,
                        sentences_bucket_max_size,
                    ],
                    outputs=pick_args_proxy,
                )
            st_speakers_data.change(
                None,
                None,
                None,
                js='() => { console.log("click arg proxy"); document.getElementById("collect-btn").click(); return true;}',
            )

            # Create a temporary list for generated items
            st_temp_list = create_temp_list(
                pick_args_proxy, multi_output_audio, interval, session, md_session
            )

    # Bind events
    load_preset_btn.click(
        fn=on_load_preset_click,
        inputs=[preset_dropdown],
        outputs=[
            # Speaker names
            # Settings
            interval,
            gen_subtitle,
            subtitle_model,
            subtitle_lang,
            bgm_volume,
            bgm_loop,
            # Advanced params
            do_sample,
            top_p,
            top_k,
            temperature,
            length_penalty,
            num_beams,
            repetition_penalty,
            max_mel_tokens,
            # Speaker Count State
            st_speaker_count,
            st_speakers_data,
        ],
    )

    def bind_save_preset_click(gr_speakers: list[gr.Component]):
        save_preset_btn.click(
            fn=on_save_preset_click,
            inputs=[
                preset_name_input,
                # Settings
                interval,
                gen_subtitle,
                subtitle_model,
                subtitle_lang,
                bgm_volume,
                bgm_loop,
                # Advanced params
                do_sample,
                top_p,
                top_k,
                temperature,
                length_penalty,
                num_beams,
                repetition_penalty,
                max_mel_tokens,
                # Speaker names and audios
                st_speaker_count,
                *gr_speakers,
            ],
            outputs=[preset_dropdown],
        )

    delete_preset_btn.click(
        fn=on_delete_preset_click,
        inputs=[preset_dropdown],
        outputs=[preset_dropdown],
    )

    def bind_multi_gen_click(gr_speakers: list[gr.Component]):
        multi_gen_button.click(
            fn=lambda *args: gen_multi_dialog_audio(
                tts_manager.get_tts(), subtitle_manager, *args
            ),
            inputs=[
                st_speaker_count,
                dialog_text,
                interval,
                session,
                # Advanced params from the tab
                *advanced_params,
                gen_subtitle,
                subtitle_model,
                subtitle_lang,
                bgm_upload,
                bgm_volume,
                bgm_loop,
                additional_bgm,
                *gr_speakers,
            ],
            outputs=[multi_output_audio, multi_subtitle_output, st_temp_list],
        )

    multi_output_audio.change(None, [], [], js=notify_done)
    open_output_folder.click(
        on_open_output_folder_click,
        inputs=[],
        outputs=[],
    )

    add_role_btn.click(
        fn=add_role,
        inputs=[st_speakers_data, st_speaker_count],
        outputs=[st_speakers_data, st_speaker_count],
    )

    remove_role_btn.click(
        fn=remove_role,
        inputs=[st_speakers_data, st_speaker_count],
        outputs=[st_speakers_data, st_speaker_count],
    )


def on_open_output_folder_click():
    """Open the output folder in the file explorer based on current working directory"""
    output_dir = os.path.join(os.getcwd(), "outputs")
    if os.path.exists(output_dir):
        print(f"Open {output_dir}")
        if os.name == "nt":
            os.startfile(output_dir)
        elif os.name == "posix":
            import subprocess

            subprocess.Popen(["xdg-open", output_dir])
        else:
            webbrowser.open(f"file://{output_dir}")
    else:
        print(f"Output directory {output_dir} does not exist.")


def add_role(speakers_data, speaker_count):
    speaker_count += 1
    speakers_data.append((f"角色{speaker_count}", None))
    return speakers_data, speaker_count


def remove_role(speakers_data, speaker_count):
    if len(speakers_data) > 1:
        speakers_data = speakers_data[:-1]
        speaker_count -= 1
    return speakers_data, speaker_count


def collect_pick_args(*args):
    gr.Success("已更新对话列表参数")
    return [*args]
