"""
Single audio generation tab
"""

import os

import gradio as gr

from webui2.audio.subtitle_generator import SubtitleManager
from webui2.audio.tts_engine import TTSManager
from webui2.ui.components.common import (
    create_advanced_params_accordion,
    create_bgm_accordion,
    create_subtitle_controls,
)
from webui2.ui.handlers import gen_audio, on_input_text_change, update_prompt_audio


def create_single_audio_tab_page(tts_manager: TTSManager, subtitle_manager: SubtitleManager):
    """Create the single audio generation tab"""
    with gr.Row(elem_id="single-audio"):
        # navigation section
        with gr.Column(elem_id="sidebar-anchors", scale=1):
            gr.HTML('<a href="#single-audio-config-basic"><h3">🧑 基本配置<h3></a>')
            gr.HTML('<a href="#subtitle-controls"><h3">🎬 字幕<h3></a>')
            gr.HTML('<a href="#bgm-accordion""><h3">🎵 背景音乐<h3></a>')
            gr.HTML('<a href="#advanced-params""><h3">⚙️ 高级参数<h3></a>')
            gr.HTML('<a href="#anchor-examples"><h3">📝 示例<h3></a>')

        with gr.Column(scale=9):
            with gr.Row(elem_id="single-audio-config-basic"):
                os.makedirs("prompts", exist_ok=True)
                prompt_audio = gr.Audio(
                    label="参考音频",
                    key="prompt_audio",
                    sources=["upload", "microphone"],
                    type="filepath",
                )

                with gr.Column():
                    input_text_single = gr.TextArea(
                        label="文本",
                        key="input_text_single",
                        placeholder="请输入目标文本",
                        info="当前模型版本{}".format(getattr(tts_manager.get_tts(), "model_version", "1.0")),
                    )
                    infer_mode = gr.Radio(
                        choices=["普通推理", "批次推理"],
                        label="推理模式",
                        info="批次推理：更适合长句，性能翻倍",
                        value="普通推理",
                    )

            with gr.Row(elem_id="single-audio-output"):
                gr.Markdown("### 生成结果", elem_classes=["flex-auto"])
                output_audio = gr.Audio(
                    label="语音",
                    visible=True,
                    key="output_audio",
                    elem_id="output-audio",
                )
                subtitle_output = gr.File(label="字幕", visible=True, elem_id="output-subtitle")
                gen_button = gr.Button(
                    "生成语音",
                    key="gen_button",
                    interactive=True,
                    elem_classes=["flex-auto", "bg-accent"],
                )

            gen_subtitle, subtitle_model, subtitle_lang = create_subtitle_controls()

            bgm_upload, bgm_volume, bgm_loop, additional_bgm = create_bgm_accordion()

            advanced_components = create_advanced_params_accordion(tts_manager)

            # Extract components for return
            ( do_sample, top_p, top_k, temperature, length_penalty, num_beams,
             repetition_penalty, max_mel_tokens, max_text_tokens_per_sentence,
             sentences_bucket_max_size, sentences_preview,
            ) = advanced_components  # fmt: skip

            advanced_params = [
                do_sample,top_p,top_k,temperature,length_penalty,
                num_beams,repetition_penalty,max_mel_tokens
            ]  # fmt: skip

            # Add examples if available
            examples = tts_manager.get_examples()
            if examples:
                gr.Examples(
                    examples=examples,
                    inputs=[prompt_audio, input_text_single, infer_mode],
                    elem_id="anchor-examples",
                )

    # bind events
    gen_button.click(
        fn=lambda *args: gen_audio(tts_manager.get_tts(), subtitle_manager, *args),
        inputs=[
            prompt_audio,
            input_text_single,
            infer_mode,
            max_text_tokens_per_sentence,
            sentences_bucket_max_size,
            *advanced_params,
            gen_subtitle,
            subtitle_model,
            subtitle_lang,
            bgm_upload,
            bgm_volume,
            bgm_loop,
            additional_bgm,
        ],
        outputs=[output_audio, subtitle_output],
    )
    max_text_tokens_per_sentence.change(
        fn=lambda text, max_tokens: on_input_text_change(tts_manager.get_tts(), text, max_tokens),
        inputs=[input_text_single, max_text_tokens_per_sentence],
        outputs=[sentences_preview],
    )
    prompt_audio.upload(
        fn=update_prompt_audio,
        inputs=[],
        outputs=[gen_button],
    )

    return {
        "inputs": {
            "prompt_audio": prompt_audio,
            "input_text_single": input_text_single,
            "infer_mode": infer_mode,
            "max_text_tokens_per_sentence": max_text_tokens_per_sentence,
            "sentences_bucket_max_size": sentences_bucket_max_size,
            "gen_subtitle": gen_subtitle,
            "model_choice": subtitle_model,
            "subtitle_lang": subtitle_lang,
            "bgm_upload": bgm_upload,
            "bgm_volume": bgm_volume,
            "bgm_loop": bgm_loop,
            "additional_bgm": additional_bgm,
        },
        "outputs": {
            "output_audio": output_audio,
            "subtitle_output": subtitle_output,
        },
        "controls": {
            "gen_button": gen_button,
        },
        "advanced_params": advanced_params,
        "sentences_preview": sentences_preview,
    }
