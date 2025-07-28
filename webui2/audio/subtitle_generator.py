"""
Subtitle generation utilities
"""

import os
import shutil
import traceback

from webui2.utils.audio_subtitle import AudioSubtitleGenerator


class SubtitleManager:
    """Manages subtitle generation with different models"""

    def __init__(self):
        self.generator = AudioSubtitleGenerator()

    def generate_subtitles(
        self,
        audio_path,
        subtitle_model="base",
        subtitle_lang="zh (中文)",
        output_srt=None,
    ):
        """Generate subtitles for audio file"""
        try:
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                print("警告: 音频文件为空或不存在，跳过字幕生成")
                return None

            lang_code = subtitle_lang.split(" ")[0]

            if not output_srt:
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                output_srt = os.path.join("outputs", f"{base_name}.srt")

            self.generator.set_model(subtitle_model)

            generated_subtitle = self.generator.generate_subtitles(audio_path, language=lang_code, output_srt=output_srt)

            if generated_subtitle and os.path.exists(generated_subtitle):
                print(f"字幕文件已生成: {generated_subtitle}")
                return generated_subtitle
            else:
                print("字幕文件未生成")
                return None

        except Exception as e:
            print(f"生成字幕失败: {str(e)}")
            traceback.print_exc()
            return None
        finally:
            self.generator.cleanup()

    def generate_subtitle_only(self, audio_path, subtitle_model, subtitle_lang):
        """单独生成字幕文件"""
        try:
            if audio_path is None:
                return None, "请先上传音频文件"

            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                return None, "音频文件无效或为空"

            try:
                result = self.generate_subtitles(audio_path, subtitle_model, subtitle_lang)
                if result:
                    return result, "字幕生成成功！"
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
