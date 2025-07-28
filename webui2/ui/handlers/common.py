"""
Event handlers for UI interactions
"""

import os
import time

import gradio as gr
import numpy as np
from scipy.io import wavfile

from ...audio import mix_audio_with_bgm


def gen_audio(
    tts,
    subtitle_manager,
    prompt,
    text,
    infer_mode,
    max_text_tokens_per_sentence=120,
    sentences_bucket_max_size=4,
    *args,
    progress=gr.Progress(),
):
    """Handle single audio generation"""
    output_path = os.path.join("outputs", f"spk_{int(time.time())}.wav")
    tts.gr_progress = progress

    (
        do_sample,
        top_p,
        top_k,
        temperature,
        length_penalty,
        num_beams,
        repetition_penalty,
        max_mel_tokens,
    ) = args[:8]

    kwargs = {
        "do_sample": bool(do_sample),
        "top_p": float(top_p),
        "top_k": int(top_k) if int(top_k) > 0 else None,
        "temperature": float(temperature),
        "length_penalty": float(length_penalty),
        "num_beams": num_beams,
        "repetition_penalty": float(repetition_penalty),
        "max_mel_tokens": int(max_mel_tokens),
    }

    gen_subtitle = args[8] if len(args) > 8 else True
    model_choice = args[9] if len(args) > 9 else "base"
    subtitle_lang = args[10] if len(args) > 10 else "zh (中文)"
    bgm_path = args[11] if len(args) > 11 else None
    bgm_volume = args[12] if len(args) > 12 else 0.3
    bgm_loop = args[13] if len(args) > 13 else True
    additional_bgm = args[14] if len(args) > 14 else []

    # Generate audio
    if infer_mode == "普通推理":
        output = tts.infer(
            prompt,
            text,
            output_path,
            verbose=True,  # cmd_args.verbose
            max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
            **kwargs,
        )
    else:
        output = tts.infer_fast(
            prompt,
            text,
            output_path,
            verbose=True,  # cmd_args.verbose
            max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
            sentences_bucket_max_size=sentences_bucket_max_size,
            **kwargs,
        )

    # Generate subtitle
    subtitle_path = None
    if gen_subtitle:
        subtitle_path = subtitle_manager.generate_subtitles(output_path, model_choice, subtitle_lang)

    # Mix with background music
    bgm_paths = []
    if bgm_path:
        bgm_paths.append(bgm_path)
    if additional_bgm is not None:
        for file in additional_bgm:
            bgm_paths.append(file.name)

    if bgm_paths:
        mixed_output_path = mix_audio_with_bgm(output_path, bgm_paths, volume=bgm_volume, loop=bgm_loop)
        output_path = mixed_output_path

    return gr.update(value=output_path, visible=True), gr.update(value=subtitle_path, visible=bool(subtitle_path))


def gen_multi_dialog_audio(
    tts,
    subtitle_manager,
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
    interval=0.5,
    *args,
    progress=gr.Progress(),
):
    """Handle multi-dialog generation"""
    temp_dir = "temp_dialog"
    os.makedirs(temp_dir, exist_ok=True)

    tts.gr_progress = progress

    # Get advanced parameters
    if len(args) >= 8:
        (
            do_sample,
            top_p,
            top_k,
            temperature,
            length_penalty,
            num_beams,
            repetition_penalty,
            max_mel_tokens,
        ) = args[:8]
    else:
        progress(0.1, "警告：未接收到完整的高级参数，使用默认值")
        do_sample = True
        top_p = 0.8
        top_k = 30
        temperature = 1.0
        length_penalty = 0.0
        num_beams = 3
        repetition_penalty = 10.0
        max_mel_tokens = 600

    kwargs = {
        "do_sample": bool(do_sample),
        "top_p": float(top_p),
        "top_k": int(top_k) if int(top_k) > 0 else None,
        "temperature": float(temperature),
        "length_penalty": float(length_penalty),
        "num_beams": num_beams,
        "repetition_penalty": float(repetition_penalty),
        "max_mel_tokens": int(max_mel_tokens),
    }

    # Build speakers dictionary
    speakers = {}
    if speaker1_name and speaker1_audio:
        speakers[speaker1_name] = speaker1_audio
    if speaker2_name and speaker2_audio:
        speakers[speaker2_name] = speaker2_audio
    if speaker3_name and speaker3_audio:
        speakers[speaker3_name] = speaker3_audio
    if speaker4_name and speaker4_audio:
        speakers[speaker4_name] = speaker4_audio
    if speaker5_name and speaker5_audio:
        speakers[speaker5_name] = speaker5_audio
    if speaker6_name and speaker6_audio:
        speakers[speaker6_name] = speaker6_audio

    # Parse dialog text
    progress(0.1, "正在解析对话文本...")
    dialog_lines = []
    current_speaker = None
    current_text = []

    for line in dialog_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("[") and "]" in line:
            if current_speaker and current_text:
                dialog_lines.append({"speaker": current_speaker, "text": " ".join(current_text)})
                current_text = []

            end_index = line.index("]")
            current_speaker = line[1:end_index].strip()
            remaining_text = line[end_index + 1 :].strip()

            if remaining_text:
                current_text.append(remaining_text)
        elif current_speaker:
            current_text.append(line)

    if current_speaker and current_text:
        dialog_lines.append({"speaker": current_speaker, "text": " ".join(current_text)})

    if not dialog_lines:
        progress(1.0, "未识别到有效对话")
        return gr.update(value=None, visible=True), gr.update(visible=False)

    all_speakers = list(set([line["speaker"] for line in dialog_lines]))
    progress(0.2, f"识别到 {len(all_speakers)} 个角色: {', '.join(all_speakers)}")

    for speaker in all_speakers:
        if speaker not in speakers:
            progress(1.0, f"错误: 角色 '{speaker}' 没有对应的参考音频")
            return gr.update(value=None, visible=True), gr.update(visible=False)

    # Generate audio for each dialog line
    audio_segments = []
    sr = None

    for i, line in enumerate(dialog_lines):
        speaker = line["speaker"]
        text = line["text"]

        progress(
            0.3 + 0.6 * i / len(dialog_lines),
            f"生成 '{speaker}' 的对话 ({i + 1}/{len(dialog_lines)}): {text[:20]}...",
        )

        output_path = os.path.join(temp_dir, f"{speaker}_{i}_{int(time.time())}.wav")
        tts.infer(speakers[speaker], text, output_path, verbose=True, **kwargs)

        sample_rate, audio_data = wavfile.read(output_path)
        sr = sample_rate

        audio_segments.append(audio_data)

        if i < len(dialog_lines) - 1:
            silence = np.zeros(int(interval * sr), dtype=audio_data.dtype)
            audio_segments.append(silence)

    # Combine all audio segments
    progress(0.9, "正在合并对话音频...")
    dialog_audio = np.concatenate(audio_segments)

    output_path = os.path.join("outputs", f"dialog_{int(time.time())}.wav")
    wavfile.write(output_path, sr, dialog_audio)

    # Clean up temporary files
    for file in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # Handle additional parameters
    gen_subtitle = args[8] if len(args) > 8 else True
    model_choice = args[9] if len(args) > 9 else "base"
    subtitle_lang = args[10] if len(args) > 10 else "zh (中文)"
    bgm_path = args[11] if len(args) > 11 else None
    bgm_volume = args[12] if len(args) > 12 else 0.3
    bgm_loop = args[13] if len(args) > 13 else True
    additional_bgm = args[14] if len(args) > 14 else []

    # Generate subtitle
    subtitle_path = None
    if gen_subtitle:
        subtitle_path = subtitle_manager.generate_subtitles(output_path, model_choice, subtitle_lang)

    # Mix with background music
    bgm_paths = []
    if bgm_path:
        bgm_paths.append(bgm_path)
    if additional_bgm is not None:
        for file in additional_bgm:
            bgm_paths.append(file.name)

    if bgm_paths:
        mixed_output_path = mix_audio_with_bgm(output_path, bgm_paths, volume=bgm_volume, loop=bgm_loop)
        output_path = mixed_output_path

    return gr.update(value=output_path, visible=True), gr.update(value=subtitle_path, visible=bool(subtitle_path))
