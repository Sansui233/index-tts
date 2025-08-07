import json
import os
import time
import traceback
from pathlib import Path

import gradio as gr
import numpy as np
from scipy.io import wavfile

from indextts.infer import IndexTTS
from webui2.config import TEMP_DIR
from webui2.utils import mix_audio_with_bgm
from webui2.utils.subtitle_manager import SubtitleManager
from webui2.utils.tts_manager import TTSManager


def gen_audio(
    tts: IndexTTS | None,
    subtitle_manager: SubtitleManager,
    prompt,
    text,
    infer_mode,
    max_text_tokens_per_sentence=120,
    sentences_bucket_max_size=4,
    *args,
    progress=gr.Progress(),
):
    """Handle single audio generation"""
    if tts is None:
        gr.Error("TTS model is not initialized")
        return None, None
    try:
        audio_output_path = Path("outputs") / f"spk_{int(time.time())}.wav"
        tts.gr_progress = progress  # type: ignore

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
        subtitle_model = args[9] if len(args) > 9 else "base"
        subtitle_lang = args[10] if len(args) > 10 else "zh (中文)"
        bgm_path = args[11] if len(args) > 11 else None
        bgm_volume = args[12] if len(args) > 12 else 0.3
        bgm_loop = args[13] if len(args) > 13 else True
        additional_bgm = args[14] if len(args) > 14 else []

        # Generate audio
        if infer_mode == "普通推理":
            _ = tts.infer(
                prompt,
                text,
                audio_output_path,
                verbose=True,  # cmd_args.verbose
                max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
                **kwargs,
            )
        else:
            _ = tts.infer_fast(
                prompt,
                text,
                audio_output_path,
                verbose=True,  # cmd_args.verbose
                max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
                sentences_bucket_max_size=sentences_bucket_max_size,
                **kwargs,
            )

        # Generate subtitle
        subtitle_path = (
            gen_subtitle_srt(str(audio_output_path), subtitle_model, subtitle_lang)
            if gen_subtitle
            else None
        )
        audio_output_path = gen_audio_with_bgm(
            str(audio_output_path), bgm_path, additional_bgm, bgm_volume, bgm_loop
        )

        return gr.update(value=audio_output_path, visible=True), gr.update(
            value=subtitle_path, visible=bool(subtitle_path)
        )
    except Exception as e:
        gr.Error(f"生成音频时发生错误: {str(e)}")
        traceback.print_exc()
        return None, None


# 前面带类型标注的是需要自定义的参数
# 后面 gradio 的组件
# 使用时需要 lambda 函数来传递前面的参数，只留组件接口
def gen_multi_dialog_audio(
    tts: IndexTTS | None,
    subtitle_manager,
    speaker_count,  # 指定 *args 中的 speaker 数量
    dialog_text,
    interval=0.5,
    session="default_session",
    *args,  # 包含advanced parameters 和 speaker 列表(名字、音频)
    progress=gr.Progress(),
):
    try:
        output_dir = str(TEMP_DIR / f"{session}")
        os.makedirs(output_dir, exist_ok=True)

        if tts is None:
            gr.Error("TTS model is not initialized")
            return
        tts.gr_progress = progress  # type: ignore

        # Get advanced parameters
        if len(args) >= 8 + speaker_count * 3:
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

        print(f"[webui2][Info] 参考角色数量: {speaker_count}")
        # Parse speaker inputs into Dict<name, audio_name, audio_blob>
        gr_speakers = (
            args[-speaker_count * 3 :] if len(args) >= speaker_count * 3 else []
        )
        speaker_pairs = np.array(gr_speakers).reshape(-1, 3)
        speakers = {name: audio for [name, audio, _] in speaker_pairs}

        # Parse dialog text
        dialog_lines = parse_dialogs(dialog_text, speakers, progress)

        # Generate audio for each dialog line
        audio_segments = []
        temp_files: list[tuple[str, str]] = []  # list of (text, audio_path)
        sample_rate = None

        # TODO batch 合成
        for i, line in enumerate(dialog_lines):
            speaker = line["speaker"]
            text = line["text"]

            progress(
                0.3 + 0.6 * i / len(dialog_lines),
                f"生成 '{speaker}' 的对话 ({i + 1}/{len(dialog_lines)}): {text[:20]}...",
            )
            print(f"[webui2][Info] No.{i}\t正在生成 '{speaker}' 的对话: {text[:20]}...")

            audio_output_path = os.path.join(
                output_dir, f"{i}_{speaker}_{int(time.time())}.wav"
            )
            tts.infer(
                speakers[speaker], text, audio_output_path, verbose=False, **kwargs
            )

            sample_rate, audio_data = wavfile.read(audio_output_path)

            audio_segments.append(audio_data)

            if i < len(dialog_lines) - 1:
                silence = np.zeros(int(interval * sample_rate), dtype=audio_data.dtype)
                audio_segments.append(silence)
            temp_files.append((f"[{speaker}] {text}", audio_output_path))

        # Combine all audio segments
        progress(0.9, "正在合并对话音频...")
        dialog_audio = np.concatenate(audio_segments)

        audio_output_path = os.path.join("outputs", f"dialog_{int(time.time())}.wav")
        wavfile.write(audio_output_path, sample_rate, dialog_audio)

        # Handle additional parameters
        gen_subtitle = args[8] if len(args) > 8 else True
        subtitle_model = args[9] if len(args) > 9 else "base"
        subtitle_lang = args[10] if len(args) > 10 else "zh"
        bgm_path = args[11] if len(args) > 11 else None
        bgm_volume = args[12] if len(args) > 12 else 0.3
        bgm_loop = args[13] if len(args) > 13 else True
        additional_bgm = args[14] if len(args) > 14 else []

        # Generate subtitle
        subtitle_path = (
            gen_subtitle_srt(audio_output_path, subtitle_model, subtitle_lang)
            if gen_subtitle
            else None
        )

        # Mix with background music
        audio_output_path = gen_audio_with_bgm(
            audio_output_path, bgm_path, additional_bgm, bgm_volume, bgm_loop
        )

        print(f"Converstion dialog saved to : {audio_output_path}")

        # save temp_list.json to session directory
        index_file = TEMP_DIR / session / "temp_list.json"
        print(f"[webui2][Info] Saving index files to {index_file}")
        if not index_file.parent.exists():
            index_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"text": text, "audio_path": audio_path} for text, audio_path in temp_files
        ]
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return (
            gr.update(value=audio_output_path, visible=True),
            gr.update(value=subtitle_path, visible=bool(subtitle_path)),
            temp_files,
        )
    except Exception as e:
        gr.Error(f"Error occured: {str(e)}")
        traceback.print_exc()
        return None


def gen_subtitle_srt(
    audio_output_path: str, subtitle_model, subtitle_lang
) -> str | None:
    """
    Return subtitle file path
    """
    subtitle_mgr = SubtitleManager().get_instance()
    return subtitle_mgr.generate_subtitles(
        audio_output_path, subtitle_model, subtitle_lang
    )


def gen_audio_with_bgm(
    audio_output_path: str,
    bgm_path: str | None,
    additional_bgm: list | None,
    bgm_volume: float,
    bgm_loop: bool,
) -> str:
    """
    Return audio path with background music mixed.
    if both bgm_path and additional_bgm are None, return audio_output_path.
    """
    bgm_paths = []
    if bgm_path:
        bgm_paths.append(bgm_path)
    if additional_bgm is not None:
        for file in additional_bgm:
            bgm_paths.append(file.name)
    return mix_audio_with_bgm(
        str(audio_output_path), bgm_paths, volume=bgm_volume, loop=bgm_loop
    )


def merge_from_temp_files(
    temp_files: list[tuple[str, str]],  # list of (text, audio_path), from gr.Component
    gen_subtitle=False,
    subtitle_model="base",
    subtitle_lang="zh",
    bgm_path=None,
    bgm_volume=0.3,
    bgm_loop=True,
    additional_bgm=[],
    interval=0.5,
    progress=gr.Progress(),
):
    import subprocess

    tts = TTSManager.get_instance().get_tts()
    tts.gr_progress = progress  # type: ignore

    audio_files = [audio_path for _, audio_path in temp_files]
    audio_output_path = Path("outputs") / f"dialog_{int(time.time())}.wav"

    ffmpeg = SubtitleManager.get_instance().generator.ffmpeg_path
    if ffmpeg:
        # Use ffmpeg and subprocess to concatenate audio files with silence intervals
        import tempfile

        if not audio_files:
            return None

        # Get sample rate from the first audio file
        from scipy.io import wavfile

        sr, _ = wavfile.read(audio_files[0])
        silence_duration = interval
        silence_samples = int(sr * silence_duration)

        # Generate a temporary silence wav file
        import numpy as np

        silence_wav_path = None
        if silence_samples > 0 and len(audio_files) > 1:
            silence_data = np.zeros(silence_samples, dtype=np.int16)
            silence_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            wavfile.write(silence_wav.name, sr, silence_data)
            silence_wav_path = silence_wav.name

        # Create a temporary file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as f:
            for idx, audio_file in enumerate(audio_files):
                f.write(f"file '{os.path.abspath(audio_file)}'\n")
                # Add silence between segments, except after the last one
                if silence_wav_path and idx < len(audio_files) - 1:
                    f.write(f"file '{os.path.abspath(silence_wav_path)}'\n")
            filelist_path = f.name

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            filelist_path,
            str(audio_output_path),  # 这边没指定统一的转码 码率不知道有没有问题
        ]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"[mix_from_temp_files][Error] ffmpeg concat failed: {e}")
            return None
        finally:
            try:
                os.remove(filelist_path)  # remove temporary file
            except Exception:
                pass
            if silence_wav_path:
                try:
                    os.remove(silence_wav_path)
                except Exception:
                    pass
            gr.Success("Audio files have been successfully merged")
            print(f"Audio files have been successfully merged to: {audio_output_path}")
        return str(audio_output_path)
    else:
        # Use wavfile library to concatenate audio files with silence intervals
        if not audio_files:
            return None
        import numpy as np
        from scipy.io import wavfile

        sample_rate = None
        audio_datas = []
        for idx, audio_file in enumerate(audio_files):
            sr, data = wavfile.read(audio_file)
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                raise ValueError(
                    f"Sample rate mismatch: {audio_file} has {sr}, expected {sample_rate}"
                )
            audio_datas.append(data)
            # Add silence between segments, except after the last one
            if idx < len(audio_files) - 1 and interval > 0:
                silence = np.zeros(int(interval * sample_rate), dtype=data.dtype)
                audio_datas.append(silence)
        # TODO Mix with background music
        if not audio_datas:
            return None
        mixed_audio = np.concatenate(audio_datas)
        wavfile.write(str(audio_output_path), sample_rate, mixed_audio)
        gr.Success(f"合并音频已保存至 {audio_output_path}")
        print(f"[generate][Info] merged wav file saved to {audio_output_path}")

        return str(audio_output_path)


def regenerate_single(
    # from button
    text: str,  # gr.Component
    original_audio: str,  # gr.Component
    temp_list: list[tuple[str, str]],  # list of (text, audio_path)
    session,  # gr.State
    # from multi_dialog
    speakers_data,  # gr.State
    infer_mode: str,  # gr.Component
    do_sample,  # gr.Component
    top_p,  # gr.Component
    top_k,  # gr.Component
    temperature,  # gr.Component
    length_penalty,  # gr.Component
    num_beams,  # gr.Component
    repetition_penalty,  # gr.Component
    max_mel_tokens,  # gr.Component
    max_text_tokens_per_sentence: int = 120,  # gr.Component
    sentences_bucket_max_size: int = 4,  # gr.Component
    # internal
    progress=gr.Progress(),
):
    """
    Return audio file only
    """
    try:
        tts = TTSManager.get_instance().get_tts()
        if tts is None:
            gr.Error("TTS model is not initialized")
            raise ValueError("TTS model is not initialized")
            return

        # new audio_output_path is like "outputs/temp_dialog/spk_1234567890.wav"
        # replace the timestamp with the current time
        print(f"[webui2][Info] Regenerating audio for: {text}")
        parts = Path(original_audio).name.split("_")
        parts[-1] = f"{int(time.time())}.wav"
        output_wav_path: Path = TEMP_DIR / session / "_".join(parts)
        print(f"[webui2][Debug] original audio_path: {original_audio}")
        print(f"[webui2][Debug] output_wav_path: {output_wav_path}")

        tts.gr_progress = progress  # type: ignore

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

        progress(0.1, "正在解析对话文本...")
        speaker, text = extract_speaker_and_text(text)
        if speaker == "":
            gr.Error("对话文本中没有指定角色，请使用 [角色名] 文本 的格式")
            print("[webui2][Error] 对话文本中没有指定角色，请使用 [角色名] 文本 的格式")
            return

        # speakers_data: list of (speaker, audio_path)
        speakers = {name: audio for (name, audio) in speakers_data}

        progress(0.3, "正在生成...")
        # Regenerate audio
        if infer_mode == "普通推理":
            _ = tts.infer(
                speakers[speaker],
                text,
                output_wav_path,
                verbose=False,  # cmd_args.verbose
                max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
                **kwargs,
            )
        else:
            _ = tts.infer_fast(
                speakers[speaker],
                text,
                output_wav_path,
                verbose=False,  # cmd_args.verbose
                max_text_tokens_per_sentence=int(max_text_tokens_per_sentence),
                sentences_bucket_max_size=sentences_bucket_max_size,
                **kwargs,
            )

        # update temp_list with new audio path
        # audio 在加载后的 Path 是系统的临时目录，只有音频名字是一样的
        # 现在是名字匹配，序号匹配是最好的，但我不想再包一层，要的参数也太多了
        update_success = False
        for i, (last_text, last_audio) in enumerate(temp_list):
            orginal_audio_name = Path(original_audio).name
            last_audio_name = Path(last_audio).name
            if last_audio_name == orginal_audio_name:
                print(f"[webui2][Debug] 对话列表状态更新: {i + 1} {last_audio}")
                temp_list[i] = (last_text, str(output_wav_path))
                update_success = True
                break
        if not update_success:
            gr.Warning("未找到匹配的音频文件，无法更新对话列表")
            print("[webui2][Warn] 未找到匹配的音频文件，无法更新对话列表")

        return str(output_wav_path)

    except Exception as e:
        gr.Error(f"生成音频时发生错误: {str(e)}")
        traceback.print_exc()
        return


def parse_dialogs(
    dialog_text: str, gr_speakers, progress: gr.Progress
) -> list[dict[str, str]]:
    progress(0.1, "正在解析对话文本...")
    dialog_lines: list[dict[str, str]] = []

    for line in dialog_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("[") and "]" in line:
            speaker, text = extract_speaker_and_text(line)
            if dialog_lines and dialog_lines[-1]["speaker"] == speaker:
                dialog_lines[-1]["text"] += " " + text
            else:
                dialog_lines.append({"speaker": speaker, "text": text})
        else:
            _, text = extract_speaker_and_text(line)
            if text:
                if dialog_lines:
                    dialog_lines[-1]["text"] += " " + text
                else:
                    print(f"[webui2][Debug] 忽略行：无角色: {text}")

    if not dialog_lines:
        progress(1.0, "未识别到有效对话")
        raise ValueError("未识别到有效对话")

    text_speakers = list(set([line["speaker"] for line in dialog_lines]))
    progress(0.2, f"识别到 {len(text_speakers)} 个角色: {', '.join(text_speakers)}")
    print(f"[webui2][Info] 识别到 {len(text_speakers)} 个角色: {', '.join(text_speakers)}")  # fmt:skip

    for speaker in text_speakers:
        if speaker not in gr_speakers:
            progress(1.0, f"错误: 角色 '{speaker}' 没有对应的参考音频")
            raise ValueError(f"角色 '{speaker}' 没有对应的参考音频")

    return dialog_lines


def extract_speaker_and_text(line: str) -> tuple[str, str]:
    """Extract speaker and text from a dialog line"""
    if "[" in line and "]" in line:
        start_index = line.index("[") + 1
        end_index = line.index("]")
        speaker = line[start_index:end_index].strip()
        text = line[end_index + 1 :].strip()
        return speaker, text
    return "", line.strip()
