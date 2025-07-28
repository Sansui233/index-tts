"""
Multi-dialog generation tab
"""

import gradio as gr

from ..components import (
    create_advanced_params_accordion,
    create_bgm_accordion,
    create_subtitle_controls,
)


def create_multi_dialog_tab(tts_manager):
    """Create the multi-dialog generation tab"""
    gr.Markdown("请为每个角色上传参考音频，然后在下方输入对话内容")

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
            with gr.Row(elem_id="anchor-multi_dialog_roles"):
                with gr.Row(elem_classes="multi_dialog-roles"):
                    speaker1_name = gr.Textbox(
                        label="角色名称",
                        value="角色1",
                        interactive=True,
                        elem_classes=["multi_dialog-role_name"],
                    )
                    speaker1_audio = gr.Audio(
                        label="参考音频",
                        key="speaker1_audio",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
                with gr.Row(elem_classes="multi_dialog-roles"):
                    speaker2_name = gr.Textbox(
                        label="角色名称",
                        value="角色2",
                        interactive=True,
                        elem_classes=["multi_dialog-role_name"],
                    )
                    speaker2_audio = gr.Audio(
                        label="参考音频",
                        key="speaker2_audio",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
            with gr.Row():
                with gr.Row(elem_classes="multi_dialog-roles"):
                    speaker3_name = gr.Textbox(
                        label="角色名称",
                        value="角色3",
                        interactive=True,
                        elem_classes=["multi_dialog-role_name"],
                    )
                    speaker3_audio = gr.Audio(
                        label="参考音频",
                        key="speaker3_audio",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
                with gr.Row(elem_classes="multi_dialog-roles"):
                    speaker4_name = gr.Textbox(
                        label="角色名称",
                        value="角色4",
                        interactive=True,
                        elem_classes=["multi_dialog-role_name"],
                    )
                    speaker4_audio = gr.Audio(
                        label="参考音频",
                        key="speaker4_audio",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
            with gr.Row():
                with gr.Row(elem_classes="multi_dialog-roles"):
                    speaker5_name = gr.Textbox(
                        label="角色名称",
                        value="角色5",
                        interactive=True,
                        elem_classes=["multi_dialog-role_name"],
                    )
                    speaker5_audio = gr.Audio(
                        label="参考音频",
                        key="speaker5_audio",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
                with gr.Row(elem_classes="multi_dialog-roles"):
                    speaker6_name = gr.Textbox(
                        label="角色名称",
                        value="角色6",
                        interactive=True,
                        elem_classes=["multi_dialog-role_name"],
                    )
                    speaker6_audio = gr.Audio(
                        label="参考音频",
                        key="speaker6_audio",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )

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
                subtitle_output_multi = gr.File(
                    label="字幕文件", visible=True, elem_id="output-subtitle"
                )
                gen_button_multi = gr.Button(
                    "生成对话",
                    key="gen_button_multi",
                    interactive=True,
                    elem_classes=["flex-auto", "bg-accent"],
                )

            gen_subtitle_multi, model_choice_multi, subtitle_lang_multi = (
                create_subtitle_controls()
            )

            bgm_upload_multi, bgm_volume_multi, bgm_loop_multi, additional_bgm_multi = (
                create_bgm_accordion()
            )

            # Add advanced parameters
            advanced_components = create_advanced_params_accordion(tts_manager)
            (
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
                sentences_preview,
            ) = advanced_components

            advanced_params = [
                do_sample,
                top_p,
                top_k,
                temperature,
                length_penalty,
                num_beams,
                repetition_penalty,
                max_mel_tokens,
            ]

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

    return {
        "inputs": {
            "speakers": {
                "speaker1_name": speaker1_name,
                "speaker1_audio": speaker1_audio,
                "speaker2_name": speaker2_name,
                "speaker2_audio": speaker2_audio,
                "speaker3_name": speaker3_name,
                "speaker3_audio": speaker3_audio,
                "speaker4_name": speaker4_name,
                "speaker4_audio": speaker4_audio,
                "speaker5_name": speaker5_name,
                "speaker5_audio": speaker5_audio,
                "speaker6_name": speaker6_name,
                "speaker6_audio": speaker6_audio,
            },
            "dialog_text": dialog_text,
            "interval": interval,
            "gen_subtitle_multi": gen_subtitle_multi,
            "model_choice_multi": model_choice_multi,
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
        "advanced_params": advanced_params,
    }
