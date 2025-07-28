"""
Multi-dialog generation tab
"""

import os

import gradio as gr

from webui2.ui.components.multi_dialog_presets import (
    create_multi_dialog_presets,
    on_delete_preset_click,
    on_refresh_preset_list,
    on_save_preset_click,
)
from webui2.utils import preset_manager

from ..components.common import (
    create_advanced_params_accordion,
    create_bgm_accordion,
    create_subtitle_controls,
)
from ..components.multi_dialog_role import create_role
from ..handlers.generate import (
    gen_multi_dialog_audio,
)
from ..handlers.preset import load_preset_handler


def create_multi_dialog_tab_page(tts_manager):
    """Create the multi-dialog generation tab"""

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
            gr.Markdown("请为每个角色上传参考音频，然后在下方输入对话内容")
            (
                preset_dropdown,
                load_preset_btn,
                refresh_preset_btn,
                preset_name_input,
                save_preset_btn,
                delete_preset_btn,
                preset_status,
            ) = create_multi_dialog_presets()

            # Status message for preset operations
            with gr.Row(elem_id="anchor-multi_dialog_roles"):
                (speaker1_name, speaker1_server_audio, speaker1_audio) = create_role(default_name="角色1")
                (speaker2_name, speaker2_server_audio, speaker2_audio) = create_role(default_name="角色2")
            with gr.Row():
                (speaker3_name, speaker3_server_audio, speaker3_audio) = create_role(default_name="角色3")
                (speaker4_name, speaker4_server_audio, speaker4_audio) = create_role(default_name="角色4")
            with gr.Row():
                (speaker5_name, speaker5_server_audio, speaker5_audio) = create_role(default_name="角色5")
                (speaker6_name, speaker6_server_audio, speaker6_audio) = create_role(default_name="角色6")

            dialog_text = gr.TextArea(
                label="对话内容（请按参考示例格式输入）",
                placeholder="请输入对话内容（格式示例）:\n[角色1]你在干什么？\n[角色2]我什么也没干呀。\n[角色1]那你拿刀干什么？\n[角色2]我只是想要切菜。",
                lines=8,
                elem_id="anchor-dialog_text",
            )

            interval = gr.Slider(
                label="对话间隔(秒)",
                minimum=0.1,
                maximum=2.0,
                value=0.5,
                step=0.1,
                info="不同角色之间的间隔时间",
            )

            with gr.Row(elem_id="multi-dialog-output"):
                gr.Markdown("### 生成结果", elem_classes=["flex-auto"])
                output_audio_multi = gr.Audio(
                    label="对话生成结果",
                    visible=True,
                    key="output_audio_multi",
                    elem_id="output-audio",
                )
                subtitle_output_multi = gr.File(label="字幕文件", visible=True, elem_id="output-subtitle")
                gen_button_multi = gr.Button(
                    "生成对话",
                    key="gen_button_multi",
                    interactive=True,
                    elem_classes=["flex-auto", "bg-accent"],
                )

            gen_subtitle_multi, subtitle_model_multi, subtitle_lang_multi = create_subtitle_controls()

            bgm_upload_multi, bgm_volume_multi, bgm_loop_multi, additional_bgm_multi = create_bgm_accordion()

            advanced_components = create_advanced_params_accordion(tts_manager)
            (
                do_sample, top_p, top_k, temperature, length_penalty, num_beams, repetition_penalty, max_mel_tokens,
                max_text_tokens_per_sentence,sentences_bucket_max_size,sentences_preview,
            ) = advanced_components  # fmt: skip

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
    # Load preset
    load_preset_btn.click(
        fn=load_preset_handler,
        inputs=[preset_dropdown],
        outputs=[
            # Speaker names
            speaker1_name,
            speaker2_name,
            speaker3_name,
            speaker4_name,
            speaker5_name,
            speaker6_name,
            # Server audio dropdowns
            speaker1_server_audio,
            speaker2_server_audio,
            speaker3_server_audio,
            speaker4_server_audio,
            speaker5_server_audio,
            speaker6_server_audio,
            # Settings
            interval,
            gen_subtitle_multi,
            subtitle_model_multi,
            subtitle_lang_multi,
            bgm_volume_multi,
            bgm_loop_multi,
            # Advanced params
            do_sample,
            top_p,
            top_k,
            temperature,
            length_penalty,
            num_beams,
            repetition_penalty,
            max_mel_tokens,
        ],
    )

    # Save preset
    save_preset_btn.click(
        fn=on_save_preset_click,
        inputs=[
            preset_name_input,
            # Speaker names
            speaker1_name,
            speaker2_name,
            speaker3_name,
            speaker4_name,
            speaker5_name,
            speaker6_name,
            # Server audio paths
            speaker1_server_audio,
            speaker2_server_audio,
            speaker3_server_audio,
            speaker4_server_audio,
            speaker5_server_audio,
            speaker6_server_audio,
            # Uploaded audio files (we pass these but don't save the paths)
            speaker1_audio,
            speaker2_audio,
            speaker3_audio,
            speaker4_audio,
            speaker5_audio,
            speaker6_audio,
            # Settings
            interval,
            gen_subtitle_multi,
            subtitle_model_multi,
            subtitle_lang_multi,
            bgm_volume_multi,
            bgm_loop_multi,
            # Advanced params
            do_sample,
            top_p,
            top_k,
            temperature,
            length_penalty,
            num_beams,
            repetition_penalty,
            max_mel_tokens,
        ],
        outputs=[preset_status, preset_dropdown],
    )

    # Delete preset
    delete_preset_btn.click(
        fn=on_delete_preset_click,
        inputs=[preset_dropdown],
        outputs=[preset_status, preset_dropdown],
    )

    preset_dropdown.select(
        fn=lambda: None,  # Do nothing on select, load button handles loading
        outputs=[],
    )

    gen_button_multi.click(
        fn=lambda *args: gen_multi_dialog_audio(tts_manager.get_tts(), *args),
        inputs=[
            speaker1_name,
            speaker1_audio,
            speaker2_name,
            speaker2_audio,
            speaker3_name,
            speaker3_audio,
            speaker4_name,
            speaker4_audio,
            speaker5_name,
            speaker5_audio,
            speaker6_name,
            speaker6_audio,
            dialog_text,
            interval,
            # Advanced params from the tab
            *advanced_params,
            do_sample,
            top_p,
            top_k,
            temperature,
            length_penalty,
            num_beams,
            repetition_penalty,
            max_mel_tokens,
            gen_subtitle_multi,
            subtitle_model_multi,
            subtitle_lang_multi,
            bgm_upload_multi,
            bgm_volume_multi,
            bgm_loop_multi,
            additional_bgm_multi,
        ],
    )

    return {
        "inputs": {
            "speakers": {
                "speaker1_name": speaker1_name,
                "speaker1_audio": speaker1_audio,
                "speaker1_server_audio": speaker1_server_audio,
                "speaker2_name": speaker2_name,
                "speaker2_audio": speaker2_audio,
                "speaker2_server_audio": speaker2_server_audio,
                "speaker3_name": speaker3_name,
                "speaker3_audio": speaker3_audio,
                "speaker3_server_audio": speaker3_server_audio,
                "speaker4_name": speaker4_name,
                "speaker4_audio": speaker4_audio,
                "speaker4_server_audio": speaker4_server_audio,
                "speaker5_name": speaker5_name,
                "speaker5_audio": speaker5_audio,
                "speaker5_server_audio": speaker5_server_audio,
                "speaker6_name": speaker6_name,
                "speaker6_audio": speaker6_audio,
                "speaker6_server_audio": speaker6_server_audio,
            },
            "dialog_text": dialog_text,
            "interval": interval,
            "gen_subtitle_multi": gen_subtitle_multi,
            "subtitle_model_multi": subtitle_model_multi,
            "subtitle_lang_multi": subtitle_lang_multi,
            "bgm_upload_multi": bgm_upload_multi,
            "bgm_volume_multi": bgm_volume_multi,
            "bgm_loop_multi": bgm_loop_multi,
            "additional_bgm_multi": additional_bgm_multi,
        },
        "outputs": {
            "output_audio_multi": output_audio_multi,
            "subtitle_output_multi": subtitle_output_multi,
        },
        "controls": {
            "gen_button_multi": gen_button_multi,
        },
        "presets": {
            "preset_dropdown": preset_dropdown,
            "load_preset_btn": load_preset_btn,
            "refresh_preset_btn": refresh_preset_btn,
            "preset_name_input": preset_name_input,
            "save_preset_btn": save_preset_btn,
            "delete_preset_btn": delete_preset_btn,
            "preset_status": preset_status,
        },
        "advanced_params": advanced_params,
        "init_presets": on_refresh_preset_list,
    }
