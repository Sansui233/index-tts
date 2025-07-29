"""
Audio mixing utilities
"""

import os
import traceback

from pydub import AudioSegment


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
