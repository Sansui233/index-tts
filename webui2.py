import glob
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback


def set_ffmpeg_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    possible_paths = [
        os.path.join(os.path.dirname(current_dir), "python", "ffmpeg", "bin"),
        os.path.join(current_dir, "python", "ffmpeg", "bin"),
        os.path.join(os.path.dirname(current_dir), "ffmpeg", "bin"),
        os.path.join(current_dir, "ffmpeg", "bin"),
        "C:\\Users\\lingn\\scoop\\shims",
    ]

    found = False
    for path in possible_paths:
        ffmpeg_path = os.path.join(path, "ffmpeg.exe")
        ffprobe_path = os.path.join(path, "ffprobe.exe")

        if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
            os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
            print(f"找到并设置FFmpeg路径: {path}")
            found = True
            break

    if not found:
        print("警告: 未找到整合包内的FFmpeg，将尝试使用系统环境变量中的FFmpeg")


set_ffmpeg_path()

import warnings

import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks
from scipy.io import wavfile
from transformers.utils import logging

logging.set_verbosity_error()
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "indextts"))

import pkg_resources

from audio_subtitle import AudioSubtitleGenerator

required_packages = ["opencc", "transformers", "torch"]
for package in required_packages:
    try:
        pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        print(f"安装缺失的依赖: {package}")

        # 设置环境变量 UV_PYTHON 到 F:\miniconda3\envs\index-tts\python.exe
        # $env:UV_PYTHON = 'F:\miniconda3\envs\index-tts\python.exe'
        os.environ["UV_PYTHON"] = "F:\\miniconda3\\envs\\index-tts\\python.exe"
        os.system(f"uv pip install {package}")

from audio_subtitle import AudioSubtitleGenerator

subtitle_generator = AudioSubtitleGenerator()

import argparse

parser = argparse.ArgumentParser(description="IndexTTS WebUI")
parser.add_argument(
    "--verbose", action="store_true", default=False, help="Enable verbose mode"
)
parser.add_argument("--port", type=int, default=7860, help="Port to run the web UI on")
parser.add_argument(
    "--host", type=str, default="127.0.0.1", help="Host to run the web UI on"
)
parser.add_argument(
    "--model_dir", type=str, default="checkpoints", help="Model checkpoints directory"
)
cmd_args = parser.parse_args()

if not os.path.exists(cmd_args.model_dir):
    print(
        f"Model directory {cmd_args.model_dir} does not exist. Please download the model first."
    )
    sys.exit(1)

for file in [
    "bigvgan_generator.pth",
    "bpe.model",
    "gpt.pth",
    "config.yaml",
]:
    file_path = os.path.join(cmd_args.model_dir, file)
    if not os.path.exists(file_path):
        print(f"Required file {file_path} does not exist. Please download it.")
        sys.exit(1)

import gradio as gr

from indextts.infer import IndexTTS
from tools.i18n.i18n import I18nAuto

i18n = I18nAuto(language="zh_CN")
MODE = "local"
tts = IndexTTS(
    model_dir=cmd_args.model_dir,
    cfg_path=os.path.join(cmd_args.model_dir, "config.yaml"),
)

os.makedirs("outputs/tasks", exist_ok=True)
os.makedirs("prompts", exist_ok=True)

SAMPLES_DIR = "samples"
os.makedirs(SAMPLES_DIR, exist_ok=True)

with open("tests/cases.jsonl", "r", encoding="utf-8") as f:
    example_cases = []
    for line in f:
        line = line.strip()
        if not line:
            continue
        example = json.loads(line)
        example_cases.append(
            [
                os.path.join("tests", example.get("prompt_audio", "sample_prompt.wav")),
                example.get("text"),
                ["普通推理", "批次推理"][example.get("infer_mode", 0)],
            ]
        )


def mix_audio_with_bgm(voice_path, bgm_paths, volume=0.3, loop=True):
    """混合语音和背景音乐"""
    try:
        voice = AudioSegment.from_file(voice_path)

        combined_bgm = None
        for bgm_path in bgm_paths:
            if os.path.exists(bgm_path):
                bgm = AudioSegment.from_file(bgm_path)
                if combined_bgm is None:
                    combined_bgm = bgm
                else:
                    combined_bgm += bgm

        if combined_bgm is None:
            return voice_path

        if len(combined_bgm) < len(voice) and loop:
            repeat_count = int(len(voice) / len(combined_bgm)) + 1
            combined_bgm = combined_bgm * repeat_count
            combined_bgm = combined_bgm[: len(voice)]
        else:
            combined_bgm = combined_bgm[: len(voice)]

        combined_bgm = combined_bgm - (20 * (1 - volume))

        mixed = voice.overlay(combined_bgm)

        base_name = os.path.splitext(os.path.basename(voice_path))[0]
        mixed_path = os.path.join("outputs", f"{base_name}_mixed.wav")
        mixed.export(mixed_path, format="wav")

        return mixed_path
    except Exception as e:
        print(f"音频混合失败: {str(e)}")
        traceback.print_exc()
        return voice_path


def gen_single(
    prompt,
    text,
    infer_mode,
    max_text_tokens_per_sentence=120,
    sentences_bucket_max_size=4,
    *args,
    progress=gr.Progress(),
):
    output_path = None
    if not output_path:
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

    if infer_mode == "普通推理":
        output = tts.infer(
            prompt,
            text,
            output_path,
            verbose=cmd_args.verbose,
            max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
            **kwargs,
        )
    else:
        output = tts.infer_fast(
            prompt,
            text,
            output_path,
            verbose=cmd_args.verbose,
            max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
            sentences_bucket_max_size=(sentences_bucket_max_size),
            **kwargs,
        )

    subtitle_path = None

    # 修改点1：gen_single 函数中的字幕生成部分
    if gen_subtitle:
        try:
            if os.path.exists(output_path):
                # 添加音频有效性检查
                if os.path.getsize(output_path) == 0:
                    print("警告: 音频文件为空，跳过字幕生成")
                    subtitle_path = None
                else:
                    lang_code = subtitle_lang.split(" ")[0]
                    model_size = model_choice

                    base_name = os.path.splitext(os.path.basename(output_path))[0]
                    subtitle_path = os.path.join("outputs", f"{base_name}.srt")

                    subtitle_generator.set_model(model_size)

                    generated_subtitle = subtitle_generator.generate_subtitles(
                        output_path, language=lang_code, output_srt=subtitle_path
                    )

                    if generated_subtitle and os.path.exists(generated_subtitle):
                        print(f"字幕文件已生成: {generated_subtitle}")
                        subtitle_path = generated_subtitle
                    else:
                        print(f"字幕文件未生成")
                        subtitle_path = None
        except Exception as e:
            print(f"生成字幕失败: {str(e)}")
            traceback.print_exc()
            subtitle_path = None
        finally:
            subtitle_generator.cleanup()

    bgm_paths = []
    if bgm_path:
        bgm_paths.append(bgm_path)

    if additional_bgm is not None:
        for file in additional_bgm:
            bgm_paths.append(file.name)

    if bgm_paths:
        mixed_output_path = mix_audio_with_bgm(
            output_path, bgm_paths, volume=bgm_volume, loop=bgm_loop
        )
        output_path = mixed_output_path

    return gr.update(value=output_path, visible=True), gr.update(
        value=subtitle_path, visible=bool(subtitle_path)
    )


def gen_dialog(
    prompt_audio_A,
    prompt_audio_B,
    text_A,
    text_B,
    interval=0.5,
    *args,
    progress=gr.Progress(),
):
    temp_dir = "temp_dialog"
    os.makedirs(temp_dir, exist_ok=True)

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

    progress(0.2, "正在生成说话人A的音频...")
    output_A = os.path.join(temp_dir, f"speaker_A_{int(time.time())}.wav")
    tts.infer(prompt_audio_A, text_A, output_A, verbose=cmd_args.verbose, **kwargs)

    progress(0.6, "正在生成说话人B的音频...")
    output_B = os.path.join(temp_dir, f"speaker_B_{int(time.time())}.wav")
    tts.infer(prompt_audio_B, text_B, output_B, verbose=cmd_args.verbose, **kwargs)

    progress(0.8, "正在合并对话音频...")

    sr_A, audio_A = wavfile.read(output_A)
    sr_B, audio_B = wavfile.read(output_B)

    if sr_A != sr_B:
        from scipy.signal import resample

        audio_B = resample(audio_B, int(len(audio_B) * sr_A / sr_B))
        sr_B = sr_A

    silence = np.zeros(int(interval * sr_A), dtype=audio_A.dtype)

    dialog_audio = np.concatenate([audio_A, silence, audio_B])

    output_path = os.path.join("outputs", f"dialog_{int(time.time())}.wav")
    wavfile.write(output_path, sr_A, dialog_audio)

    for file in [output_A, output_B]:
        if os.path.exists(file):
            os.remove(file)

    bgm_path = args[8] if len(args) > 8 else None
    bgm_volume = args[9] if len(args) > 9 else 0.3
    bgm_loop = args[10] if len(args) > 10 else True
    additional_bgm = args[11] if len(args) > 11 else []

    bgm_paths = []
    if bgm_path:
        bgm_paths.append(bgm_path)
    for file in additional_bgm:
        bgm_paths.append(file.name)

    if bgm_paths:
        mixed_output_path = mix_audio_with_bgm(
            output_path, bgm_paths, volume=bgm_volume, loop=bgm_loop
        )
        output_path = mixed_output_path

    return gr.update(value=output_path, visible=True)


def gen_multi_dialog(
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
    temp_dir = "temp_dialog"
    os.makedirs(temp_dir, exist_ok=True)

    tts.gr_progress = progress

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
                dialog_lines.append(
                    {"speaker": current_speaker, "text": " ".join(current_text)}
                )
                current_text = []

            end_index = line.index("]")
            current_speaker = line[1:end_index].strip()
            remaining_text = line[end_index + 1 :].strip()

            if remaining_text:
                current_text.append(remaining_text)
        elif current_speaker:
            current_text.append(line)

    if current_speaker and current_text:
        dialog_lines.append(
            {"speaker": current_speaker, "text": " ".join(current_text)}
        )

    if not dialog_lines:
        progress(1.0, "未识别到有效对话")
        return gr.update(value=None, visible=True), gr.update(visible=False)

    all_speakers = list(set([line["speaker"] for line in dialog_lines]))
    progress(0.2, f"识别到 {len(all_speakers)} 个角色: {', '.join(all_speakers)}")

    for speaker in all_speakers:
        if speaker not in speakers:
            progress(1.0, f"错误: 角色 '{speaker}' 没有对应的参考音频")
            return gr.update(value=None, visible=True), gr.update(visible=False)

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
        tts.infer(
            speakers[speaker], text, output_path, verbose=cmd_args.verbose, **kwargs
        )

        sample_rate, audio_data = wavfile.read(output_path)
        sr = sample_rate

        audio_segments.append(audio_data)

        if i < len(dialog_lines) - 1:
            silence = np.zeros(int(interval * sr), dtype=audio_data.dtype)
            audio_segments.append(silence)

    progress(0.9, "正在合并对话音频...")
    dialog_audio = np.concatenate(audio_segments)

    output_path = os.path.join("outputs", f"dialog_{int(time.time())}.wav")
    wavfile.write(output_path, sr, dialog_audio)

    # 保存原始音频路径（不带背景音乐）
    original_audio_path = output_path

    for file in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    gen_subtitle = args[8] if len(args) > 8 else True
    model_choice = args[9] if len(args) > 9 else "base"
    subtitle_lang = args[10] if len(args) > 10 else "zh (中文)"

    bgm_path = args[11] if len(args) > 11 else None
    bgm_volume = args[12] if len(args) > 12 else 0.3
    bgm_loop = args[13] if len(args) > 13 else True
    additional_bgm = args[14] if len(args) > 14 else []

    bgm_paths = []
    if bgm_path:
        bgm_paths.append(bgm_path)

    if additional_bgm is not None:
        for file in additional_bgm:
            bgm_paths.append(file.name)

    if bgm_paths:
        mixed_output_path = mix_audio_with_bgm(
            output_path, bgm_paths, volume=bgm_volume, loop=bgm_loop
        )
        output_path = mixed_output_path

    subtitle_path = None
    if gen_subtitle:
        try:
            if os.path.exists(original_audio_path):
                # 检查音频有效性
                if os.path.getsize(original_audio_path) == 0:
                    print("警告: 音频文件为空，跳过字幕生成")
                    subtitle_path = None
                else:
                    lang_code = subtitle_lang.split(" ")[0]
                    base_name = os.path.splitext(os.path.basename(original_audio_path))[
                        0
                    ]
                    subtitle_path = os.path.join("outputs", f"{base_name}.srt")

                    subtitle_generator.set_model(model_choice)
                    temp_subtitle = subtitle_generator.generate_subtitles(
                        original_audio_path,  # 使用原始语音
                        language=lang_code,
                    )

                    if temp_subtitle and os.path.exists(temp_subtitle):
                        shutil.move(temp_subtitle, subtitle_path)
                    else:
                        print(f"字幕生成失败，临时文件不存在: {temp_subtitle}")
                        subtitle_path = None
        except Exception as e:
            print(f"生成字幕失败: {str(e)}")
            traceback.print_exc()
            subtitle_path = None
        finally:
            subtitle_generator.cleanup()

    # 混合背景音乐（如果有）
    final_audio_path = original_audio_path
    if bgm_paths:
        mixed_output_path = mix_audio_with_bgm(
            original_audio_path,  # 使用原始语音
            bgm_paths,
            volume=bgm_volume,
            loop=bgm_loop,
        )
        final_audio_path = mixed_output_path

    return gr.update(value=final_audio_path, visible=True), gr.update(
        value=subtitle_path, visible=bool(subtitle_path)
    )


def generate_subtitle_only(audio_path, model_choice, subtitle_lang):
    """单独生成字幕文件"""
    try:
        if audio_path is None:
            return None, "请先上传音频文件"

        # 检查音频文件是否存在且有效
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            return None, "音频文件无效或为空"

        try:
            subtitle_generator.set_model(model_choice)

            lang_code = subtitle_lang.split(" ")[0]

            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            subtitle_path = os.path.join("outputs", f"{base_name}.srt")

            # 添加异常处理
            generated_subtitle = subtitle_generator.generate_subtitles(
                audio_path, language=lang_code, output_srt=subtitle_path
            )

            if generated_subtitle and os.path.exists(generated_subtitle):
                return generated_subtitle, "字幕生成成功！"
            else:
                return None, "字幕生成失败，请检查日志"
        except IndexError as e:
            print(f"Whisper模型处理错误: {str(e)}")
            traceback.print_exc()
            return None, "音频处理失败：音频可能过短或格式不支持"
        except Exception as e:
            print(f"单独生成字幕失败: {str(e)}")
            traceback.print_exc()
            return None, f"生成字幕时出错: {str(e)}"
    except Exception as e:
        print(f"单独生成字幕失败: {str(e)}")
        traceback.print_exc()
        return None, f"生成字幕时出错: {str(e)}"
    finally:
        subtitle_generator.cleanup()


def update_prompt_audio():
    update_button = gr.update(interactive=True)
    return update_button


with gr.Blocks(title="IndexTTS Demo") as demo:
    mutex = threading.Lock()
    gr.HTML("""
    <h2><center>IndexTTS: An Industrial-Level Controllable and Efficient Zero-Shot Text-To-Speech System</h2>
    <h2><center>(一款工业级可控且高效的零样本文本转语音系统)</h2>
    <h3 style="text-align: center; font-size: 22px; margin-top: 15px; margin-bottom: 15px;">
        哔哩哔哩@不吃鸟的虫子  
        <a href="https://b23.tv/7Y2BJkn" target="_blank" style="color: #00a1d6; text-decoration: underline;">
            https://b23.tv/7Y2BJkn
        </a>
    </h3>
<p align="center">
<a href='https://arxiv.org/abs/2502.05512'><img src='https://img.shields.io/badge/ArXiv-2502.05512-red'></a>
</p>
    """)
    with gr.Tab("音频生成"):
        with gr.Row():
            os.makedirs("prompts", exist_ok=True)
            prompt_audio = gr.Audio(
                label="参考音频",
                key="prompt_audio",
                sources=["upload", "microphone"],
                type="filepath",
            )
            prompt_list = os.listdir("prompts")
            default = ""
            if prompt_list:
                default = prompt_list[0]
            with gr.Column():
                input_text_single = gr.TextArea(
                    label="文本",
                    key="input_text_single",
                    placeholder="请输入目标文本",
                    info="当前模型版本{}".format(tts.model_version or "1.0"),
                )
                infer_mode = gr.Radio(
                    choices=["普通推理", "批次推理"],
                    label="推理模式",
                    info="批次推理：更适合长句，性能翻倍",
                    value="普通推理",
                )
                gen_button = gr.Button("生成语音", key="gen_button", interactive=True)
            output_audio = gr.Audio(label="生成结果", visible=True, key="output_audio")

            with gr.Row():
                gen_subtitle = gr.Checkbox(label="生成字幕文件", value=True)
                model_choice = gr.Dropdown(
                    choices=["tiny", "base", "small", "medium"],
                    value="base",
                    label="字幕模型",
                )
                subtitle_lang = gr.Dropdown(
                    choices=["zh (中文)", "en (英文)", "ja (日语)", "ko (韩语)"],
                    value="zh (中文)",
                    label="字幕语言",
                )

            subtitle_output = gr.File(label="字幕文件", visible=True)

        with gr.Accordion("背景音乐设置", open=False):
            bgm_upload = gr.Audio(label="背景音乐", sources=["upload"], type="filepath")
            bgm_volume = gr.Slider(
                label="背景音乐音量", minimum=0.0, maximum=1.0, value=0.3, step=0.01
            )
            bgm_loop = gr.Checkbox(label="循环背景音乐", value=True)
            additional_bgm = gr.Files(
                label="额外背景音乐（用于拼接）", file_count="multiple"
            )

        with gr.Accordion("高级生成参数设置", open=False):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(
                        "**GPT2 采样设置** _参数会影响音频多样性和生成速度详见[Generation strategies](https://huggingface.co/docs/transformers/main/en/generation_strategies)_"
                    )
                    with gr.Row():
                        do_sample = gr.Checkbox(
                            label="do_sample", value=True, info="是否进行采样"
                        )
                        temperature = gr.Slider(
                            label="temperature",
                            minimum=0.1,
                            maximum=2.0,
                            value=1.0,
                            step=0.1,
                        )
                    with gr.Row():
                        top_p = gr.Slider(
                            label="top_p",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.8,
                            step=0.01,
                        )
                        top_k = gr.Slider(
                            label="top_k", minimum=0, maximum=100, value=30, step=1
                        )
                        num_beams = gr.Slider(
                            label="num_beams", value=3, minimum=1, maximum=10, step=1
                        )
                    with gr.Row():
                        repetition_penalty = gr.Number(
                            label="repetition_penalty",
                            precision=None,
                            value=10.0,
                            minimum=0.1,
                            maximum=20.0,
                            step=0.1,
                        )
                        length_penalty = gr.Number(
                            label="length_penalty",
                            precision=None,
                            value=0.0,
                            minimum=-2.0,
                            maximum=2.0,
                            step=0.1,
                        )
                    max_mel_tokens = gr.Slider(
                        label="max_mel_tokens",
                        value=600,
                        minimum=50,
                        maximum=tts.cfg.gpt.max_mel_tokens,
                        step=10,
                        info="生成Token最大数量，过小导致音频被截断",
                        key="max_mel_tokens",
                    )
                with gr.Column(scale=2):
                    gr.Markdown("**分句设置** _参数会影响音频质量和生成速度_")
                    with gr.Row():
                        max_text_tokens_per_sentence = gr.Slider(
                            label="分句最大Token数",
                            value=120,
                            minimum=20,
                            maximum=tts.cfg.gpt.max_text_tokens,
                            step=2,
                            key="max_text_tokens_per_sentence",
                            info="建议80~200之间，值越大，分句越长；值越小，分句越碎；过小过大都可能导致音频质量不高",
                        )
                        sentences_bucket_max_size = gr.Slider(
                            label="分句分桶的最大容量（批次推理生效）",
                            value=4,
                            minimum=1,
                            maximum=16,
                            step=1,
                            key="sentences_bucket_max_size",
                            info="建议2-8之间，值越大，一批次推理包含的分句数越多，过大可能导致内存溢出",
                        )
                    with gr.Accordion("预览分句结果", open=True) as sentences_settings:
                        sentences_preview = gr.Dataframe(
                            headers=["序号", "分句内容", "Token数"],
                            key="sentences_preview",
                            wrap=True,
                        )
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

        if len(example_cases) > 0:
            gr.Examples(
                examples=example_cases,
                inputs=[prompt_audio, input_text_single, infer_mode],
            )

    with gr.Tab("多人对话(读小说也行)"):
        gr.Markdown("### 多人对话生成")
        gr.Markdown("请为每个角色上传参考音频，然后在下方输入对话内容")

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### 角色1")
                speaker1_name = gr.Textbox(
                    label="角色名称", value="角色1", interactive=True
                )
                speaker1_audio = gr.Audio(
                    label="参考音频",
                    key="speaker1_audio",
                    sources=["upload", "microphone"],
                    type="filepath",
                )
            with gr.Column():
                gr.Markdown("#### 角色2")
                speaker2_name = gr.Textbox(
                    label="角色名称", value="角色2", interactive=True
                )
                speaker2_audio = gr.Audio(
                    label="参考音频",
                    key="speaker2_audio",
                    sources=["upload", "microphone"],
                    type="filepath",
                )
            with gr.Column():
                gr.Markdown("#### 角色3")
                speaker3_name = gr.Textbox(
                    label="角色名称", value="角色3", interactive=True
                )
                speaker3_audio = gr.Audio(
                    label="参考音频",
                    key="speaker3_audio",
                    sources=["upload", "microphone"],
                    type="filepath",
                )

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### 角色4")
                speaker4_name = gr.Textbox(
                    label="角色名称", value="角色4", interactive=True
                )
                speaker4_audio = gr.Audio(
                    label="参考音频",
                    key="speaker4_audio",
                    sources=["upload", "microphone"],
                    type="filepath",
                )
            with gr.Column():
                gr.Markdown("#### 角色5")
                speaker5_name = gr.Textbox(
                    label="角色名称", value="角色5", interactive=True
                )
                speaker5_audio = gr.Audio(
                    label="参考音频",
                    key="speaker5_audio",
                    sources=["upload", "microphone"],
                    type="filepath",
                )
            with gr.Column():
                gr.Markdown("#### 角色6")
                speaker6_name = gr.Textbox(
                    label="角色名称", value="角色6", interactive=True
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
        )
        with gr.Row():
            interval = gr.Slider(
                label="对话间隔(秒)",
                minimum=0.1,
                maximum=2.0,
                value=0.5,
                step=0.1,
                info="不同角色之间的间隔时间",
            )
            gen_button_multi = gr.Button(
                "生成对话", key="gen_button_multi", interactive=True
            )

        output_audio_multi = gr.Audio(
            label="对话生成结果", visible=True, key="output_audio_multi"
        )

        with gr.Row():
            gen_subtitle_multi = gr.Checkbox(label="生成字幕文件", value=True)
            model_choice_multi = gr.Dropdown(
                choices=["tiny", "base", "small", "medium"],
                value="base",
                label="字幕模型",
            )
            subtitle_lang_multi = gr.Dropdown(
                choices=["zh (中文)", "en (英文)", "ja (日语)", "ko (韩语)"],
                value="zh (中文)",
                label="字幕语言",
            )

        subtitle_output_multi = gr.File(label="字幕文件", visible=True)

        with gr.Accordion("背景音乐设置", open=False):
            bgm_upload_multi = gr.Audio(
                label="背景音乐", sources=["upload"], type="filepath"
            )
            bgm_volume_multi = gr.Slider(
                label="背景音乐音量", minimum=0.0, maximum=1.0, value=0.3, step=0.01
            )
            bgm_loop_multi = gr.Checkbox(label="循环背景音乐", value=True)
            additional_bgm_multi = gr.Files(
                label="额外背景音乐（用于拼接）", file_count="multiple"
            )

        example_dialog = """[角色1]你在干什么？
[角色2]我什么也没干呀。
[角色1]那你拿刀干什么？
[角色2]我只是想要切菜。
[角色3]切菜需要那么大的刀吗？
[角色2]这只是一把普通的水果刀。
[角色4]都别吵了，快来吃饭吧！
[角色5]你们好吵啊！打扰我睡觉了。
[角色6]天天睡觉，睡死你得了！"""

        gr.Examples(examples=[[example_dialog]], inputs=[dialog_text], label="示例对话")

    with gr.Tab("单独生成字幕"):
        gr.Markdown("## 单独生成字幕")
        gr.Markdown("上传音频文件，然后选择模型和语言来生成字幕文件。")

        sample_files = []
        for ext in [".wav", ".mp3", ".flac"]:
            sample_files.extend(glob.glob(os.path.join(SAMPLES_DIR, f"*{ext}")))

        sample_examples = []
        for file in sample_files[:1]:
            sample_examples.append([file, "base", "zh (中文)"])

        with gr.Row():
            with gr.Column():
                input_audio_subtitle = gr.Audio(
                    label="上传音频文件",
                    type="filepath",
                    sources=["upload", "microphone"],
                )

                with gr.Row():
                    model_choice_subtitle = gr.Dropdown(
                        choices=["tiny", "base", "small", "medium"],
                        value="base",
                        label="字幕模型",
                    )
                    subtitle_lang_subtitle = gr.Dropdown(
                        choices=["zh (中文)", "en (英文)", "ja (日语)", "ko (韩语)"],
                        value="zh (中文)",
                        label="字幕语言",
                    )

                gen_subtitle_button = gr.Button("生成字幕", variant="primary")

                status_message = gr.Textbox(label="状态", interactive=False)

            with gr.Column():
                output_subtitle = gr.File(
                    label="生成的字幕文件", visible=True, interactive=False
                )

        if sample_examples:
            gr.Examples(
                examples=sample_examples,
                inputs=[
                    input_audio_subtitle,
                    model_choice_subtitle,
                    subtitle_lang_subtitle,
                ],
                label="示例文件",
            )
        else:
            gr.Markdown("> 提示：您可以在 `samples` 目录中添加音频文件作为示例")

        gen_subtitle_button.click(
            fn=generate_subtitle_only,
            inputs=[
                input_audio_subtitle,
                model_choice_subtitle,
                subtitle_lang_subtitle,
            ],
            outputs=[output_subtitle, status_message],
        )

    gen_button_multi.click(
        fn=gen_multi_dialog,
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
            *advanced_params,
            gen_subtitle_multi,
            model_choice_multi,
            subtitle_lang_multi,
            bgm_upload_multi,
            bgm_volume_multi,
            bgm_loop_multi,
            additional_bgm_multi,
        ],
        outputs=[output_audio_multi, subtitle_output_multi],
    )

    def on_input_text_change(text, max_tokens_per_sentence):
        if text and len(text) > 0:
            text_tokens_list = tts.tokenizer.tokenize(text)

            sentences = tts.tokenizer.split_sentences(
                text_tokens_list, max_tokens_per_sentence=int(max_tokens_per_sentence)
            )
            data = []
            for i, s in enumerate(sentences):
                sentence_str = "".join(s)
                tokens_count = len(s)
                data.append([i, sentence_str, tokens_count])

            return {
                sentences_preview: gr.update(value=data, visible=True, type="array"),
            }
        else:
            return {sentences_preview: gr.update(value=[])}

    input_text_single.change(
        on_input_text_change,
        inputs=[input_text_single, max_text_tokens_per_sentence],
        outputs=[sentences_preview],
    )
    max_text_tokens_per_sentence.change(
        on_input_text_change,
        inputs=[input_text_single, max_text_tokens_per_sentence],
        outputs=[sentences_preview],
    )
    prompt_audio.upload(update_prompt_audio, inputs=[], outputs=[gen_button])

    gen_button.click(
        gen_single,
        inputs=[
            prompt_audio,
            input_text_single,
            infer_mode,
            max_text_tokens_per_sentence,
            sentences_bucket_max_size,
            *advanced_params,
            gen_subtitle,
            model_choice,
            subtitle_lang,
            bgm_upload,
            bgm_volume,
            bgm_loop,
            additional_bgm,
        ],
        outputs=[output_audio, subtitle_output],
    )

if __name__ == "__main__":
    demo.queue(20)

    import webbrowser
    from threading import Timer

    url = f"http://{cmd_args.host}:{cmd_args.port}"

    def open_browser():
        webbrowser.open(url)

    Timer(2, open_browser).start()

    demo.launch(server_name=cmd_args.host, server_port=cmd_args.port)
