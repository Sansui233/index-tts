"""
Multi-dialog generation tab
"""

import gradio as gr

from webui2.ui.common import (
    create_advanced_params_accordion,
    create_bgm_accordion,
    create_subtitle_controls,
)
from webui2.ui.handlers.generate import (
    gen_multi_dialog_audio,
)
from webui2.utils import SubtitleManager, TTSManager

from .multi_dialog_presets import (
    create_multi_dialog_presets,
    on_delete_preset_click,
    on_load_preset_click,
    on_save_preset_click,
)
from .multi_dialog_role import create_role


def create_multi_dialog_tab_page(
    tts_manager: TTSManager, subtitle_manager: SubtitleManager
):
    """Create the multi-dialog generation tab"""
    speaker_count = gr.State(6)

    with gr.Row(elem_id="multi-dialog"):
        # navigation section
        with gr.Column(elem_id="sidebar-anchors", scale=1):
            gr.HTML('<a href="#anchor-multi_dialog_roles"><h3">🧑 角色配置<h3></a>')
            gr.HTML('<a href="#anchor-dialog_text"><h3">💬 对话<h3></a>')
            gr.HTML('<a href="#subtitle-controls"><h3">🎬 字幕<h3></a>')
            gr.HTML('<a href="#bgm-accordion""><h3">🎵 背景音乐<h3></a>')
            gr.HTML('<a href="#advanced-params""><h3">⚙️ 高级参数<h3></a>')
            gr.HTML('<a href="#anchor-examples"><h3">📝 示例<h3></a>')

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
                "### 角色配置 \n 请为每个角色上传参考音频，然后在下方输入对话内容",
                elem_id="anchor-multi_dialog_roles",
            )

            @gr.render(inputs=speaker_count)
            def render_roles(speaker_count):
                speakers = []  # length: count * 3, tuple[Textbox, Dropdown, Audio]
                for i in range(0, speaker_count, 2):
                    with gr.Row():
                        speakers.extend(create_role(i + 1))
                        if i + 1 < speaker_count:
                            speakers.extend(create_role(i + 2))
                    wrapped_load_preset_click(speakers)
                    wrapped_save_preset_click(speakers)
                    wrapped_multi_gen_click(speakers)
                    print("[webui2] [Debug] speakers len", int(len(speakers) / 3))

            # dialog part
            dialog_text = gr.TextArea(
                label="对话内容（请按参考示例格式输入）",
                elem_id="anchor-dialog_text",
                placeholder="请输入对话内容（格式示例）:\n[角色1]你在干什么？\n[角色2]我什么也没干呀。\n[角色1]那你拿刀干什么？\n[角色2]我只是想要切菜。",
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
                )
                multi_subtitle_output = gr.File(
                    label="字幕文件",
                    visible=True,
                    elem_id="output-subtitle",
                    interactive=False,
                )
                multi_gen_button = gr.Button(
                    "生成对话",
                    key="multi_gen_button",
                    elem_classes=["flex-auto", "bg-accent"],
                    interactive=True,
                )

            gen_subtitle, subtitle_model, subtitle_lang = create_subtitle_controls()

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

            # Example dialog
            example_dialog = """[角色1]你在干什么？
            [角色2]我什么也没干呀。
            [角色1]那你拿刀干什么？
            [角色2]我只是想要切菜。
            [角色3]切菜需要那么大的刀吗？
            [角色2]这只是一把普通的水果刀。
            [角色4]都别吵了，快来吃饭吧！
            [角色5]你们好吵啊！打扰我睡觉了。
            [角色6]天天睡觉，睡死你得了！"""

            gr.Examples(
                examples=[[example_dialog]],
                inputs=[dialog_text],
                label="示例对话",
                elem_id="anchor-examples",
            )

    # Bind events

    # 每次 speaker 更新都要重新绑定。因为 list 不能作为 state，state 无法通过非交互方式刷新
    # 这是 Gradio 的一个弊端，只有交互了才可能改 state，事件绑定却发生在初始的列表渲染前，导致事件绑定都得放到列表渲染内部才能正常更新
    def wrapped_load_preset_click(speaker_list: list):
        load_preset_btn.click(
            fn=on_load_preset_click,
            inputs=[preset_dropdown, speaker_count],
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
                *speaker_list,
            ],
        )

    def wrapped_save_preset_click(speaker_list: list):
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
                speaker_count,
                *speaker_list,
            ],
            outputs=[preset_dropdown],
        )

    delete_preset_btn.click(
        fn=on_delete_preset_click,
        inputs=[preset_dropdown],
        outputs=[preset_dropdown],
    )

    preset_dropdown.select(
        fn=lambda: None,  # Do nothing on select, load button handles loading
        outputs=[],
    )

    def wrapped_multi_gen_click(speaker_list: list):
        multi_gen_button.click(
            fn=lambda *args: gen_multi_dialog_audio(
                tts_manager.get_tts(), subtitle_manager, *args
            ),
            inputs=[
                speaker_count,
                dialog_text,
                interval,
                # Advanced params from the tab
                *advanced_params,
                gen_subtitle,
                subtitle_model,
                subtitle_lang,
                bgm_upload,
                bgm_volume,
                bgm_loop,
                additional_bgm,
                *speaker_list,
            ],
            outputs=[multi_output_audio, multi_subtitle_output],
        )
