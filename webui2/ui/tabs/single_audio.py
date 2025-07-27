"""
Single audio generation tab
"""

import os

import gradio as gr

from ..components import (
    create_advanced_params_accordion,
    create_bgm_accordion,
    create_subtitle_controls,
)


def create_single_audio_tab(tts_manager):
    """Create the single audio generation tab"""
    with gr.Row():
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
                info="当前模型版本{}".format(
                    tts_manager.get_tts().model_version or "1.0"
                ),
            )
            infer_mode = gr.Radio(
                choices=["普通推理", "批次推理"],
                label="推理模式",
                info="批次推理：更适合长句，性能翻倍",
                value="普通推理",
            )
            gen_button = gr.Button("生成语音", key="gen_button", interactive=True)

        output_audio = gr.Audio(label="生成结果", visible=True, key="output_audio")

    gen_subtitle, model_choice, subtitle_lang = create_subtitle_controls()
    subtitle_output = gr.File(label="字幕文件", visible=True)

    bgm_upload, bgm_volume, bgm_loop, additional_bgm = create_bgm_accordion()

    advanced_components = create_advanced_params_accordion(tts_manager)

    # Extract components for return
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

    # Add examples if available
    examples = tts_manager.get_examples()
    if examples:
        gr.Examples(
            examples=examples,
            inputs=[prompt_audio, input_text_single, infer_mode],
        )

    return {
        "inputs": {
            "prompt_audio": prompt_audio,
            "input_text_single": input_text_single,
            "infer_mode": infer_mode,
            "max_text_tokens_per_sentence": max_text_tokens_per_sentence,
            "sentences_bucket_max_size": sentences_bucket_max_size,
            "gen_subtitle": gen_subtitle,
            "model_choice": model_choice,
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
