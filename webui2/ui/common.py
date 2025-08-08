"""
Reusable UI components
"""

import gradio as gr


def create_advanced_params_accordion(tts):
    """Create advanced parameters accordion"""
    with gr.Accordion(open=False, label="⚙️ 高级参数", elem_id="advanced-params"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(
                    "**GPT2 采样设置** _参数会影响音频多样性和生成速度详见[Generation strategies](https://huggingface.co/docs/transformers/main/en/generation_strategies)_"
                )
                with gr.Row():
                    do_sample = gr.Checkbox(
                        label="do_sample",
                        value=True,
                        info="是否进行采样",
                        interactive=True,
                    )
                    temperature = gr.Slider(
                        label="temperature",
                        minimum=0.1,
                        maximum=2.0,
                        value=1.0,
                        step=0.1,
                        interactive=True,
                    )
                with gr.Row():
                    top_p = gr.Slider(
                        label="top_p",
                        minimum=0.0,
                        maximum=1.0,
                        value=0.8,
                        step=0.01,
                        interactive=True,
                    )
                    top_k = gr.Slider(
                        label="top_k",
                        minimum=0,
                        maximum=100,
                        value=30,
                        step=1,
                        interactive=True,
                    )
                    num_beams = gr.Slider(
                        label="num_beams",
                        value=3,
                        minimum=1,
                        maximum=10,
                        step=1,
                        interactive=True,
                    )
                with gr.Row():
                    repetition_penalty = gr.Number(
                        label="repetition_penalty",
                        precision=None,
                        value=10.0,
                        minimum=0.1,
                        maximum=20.0,
                        step=0.1,
                        interactive=True,
                    )
                    length_penalty = gr.Number(
                        label="length_penalty",
                        precision=None,
                        value=0.0,
                        minimum=-2.0,
                        maximum=2.0,
                        step=0.1,
                        interactive=True,
                    )
                max_mel_tokens = gr.Slider(
                    label="max_mel_tokens",
                    value=600,
                    minimum=50,
                    maximum=tts.get_tts().cfg.gpt.max_mel_tokens,
                    step=10,
                    info="生成Token最大数量，过小导致音频被截断",
                    key="max_mel_tokens",
                    interactive=True,
                )
            with gr.Column(scale=2):
                gr.Markdown("**分句设置** _参数会影响音频质量和生成速度_")
                with gr.Row():
                    max_text_tokens_per_sentence = gr.Slider(
                        label="分句最大Token数",
                        value=120,
                        minimum=20,
                        maximum=tts.get_tts().cfg.gpt.max_text_tokens,
                        step=2,
                        key="max_text_tokens_per_sentence",
                        info="建议80~200之间，值越大，分句越长；值越小，分句越碎；过小过大都可能导致音频质量不高",
                        interactive=True,
                    )
                    sentences_bucket_max_size = gr.Slider(
                        label="分句分桶的最大容量（批次推理生效）",
                        value=4,
                        minimum=1,
                        maximum=16,
                        step=1,
                        key="sentences_bucket_max_size",
                        info="建议2-8之间，值越大，一批次推理包含的分句数越多，过大可能导致内存溢出",
                        interactive=True,
                    )
                with gr.Accordion("预览分句结果", open=True):
                    sentences_preview = gr.Dataframe(
                        headers=["序号", "分句内容", "Token数"],
                        key="sentences_preview",
                        wrap=True,
                    )

    return (
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
    )


def create_bgm_accordion():
    """Create background music settings accordion"""
    with gr.Accordion("🎵 背景音乐设置", open=False, elem_id="bgm-accordion"):
        bgm_upload = gr.Audio(
            label="背景音乐", sources=["upload"], type="filepath", interactive=True
        )
        bgm_volume = gr.Slider(
            label="背景音乐音量",
            minimum=0.0,
            maximum=1.0,
            value=0.3,
            step=0.01,
            interactive=True,
        )
        bgm_loop = gr.Checkbox(label="循环背景音乐", value=True, interactive=True)
        additional_bgm = gr.Files(
            label="额外背景音乐（用于拼接）", file_count="multiple", interactive=True
        )

    return bgm_upload, bgm_volume, bgm_loop, additional_bgm


def create_subtitle_controls():
    """Create subtitle generation controls"""
    with gr.Row(elem_id="subtitle-controls"):
        gen_subtitle = gr.Checkbox(label="🎬 生成字幕文件", value=False)
        subtitle_model = gr.Dropdown(
            choices=["tiny", "base", "small", "medium"],
            value="base",
            label="字幕模型",
            interactive=True,
        )
        subtitle_lang = gr.Dropdown(
            choices=["zh", "en", "ja", "ko"],
            value="zh",
            label="字幕语言",
            interactive=True,
        )

    return gen_subtitle, subtitle_model, subtitle_lang


def create_header():
    return gr.HTML("""
<header class="header-container">
    <h1 class="main-title">IndexTTS
        <span class="arxiv-link">
            <a href='https://arxiv.org/abs/2502.05512' aria-label="View on ArXiv">
                <img src='https://img.shields.io/badge/ArXiv-2502.05512-red' alt='ArXiv:2502.05512'>
            </a>
        </span>
    </h1>
    <p>
      An Industrial-Level Controllable and Efficient Zero-Shot Text-To-Speech System
    </p>
    <p class="subtitle">
      一款工业级可控且高效的零样本文本转语音系统
    </p>
</header>""")
