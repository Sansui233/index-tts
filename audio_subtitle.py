import os
import numpy as np
import torch
from pydub import AudioSegment
from transformers import pipeline
import warnings
import traceback
from opencc import OpenCC
import subprocess

warnings.filterwarnings("ignore")

class AudioSubtitleGenerator:
    def __init__(self, root_dir=None):
        # 确定根目录
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 模型路径映射 - 使用绝对路径
        self.model_dirs = {
            "tiny": os.path.join(root_dir, "models", "whisper-tiny"),
            "base": os.path.join(root_dir, "models", "whisper-base"),
            "small": os.path.join(root_dir, "models", "whisper-small"),
            "medium": os.path.join(root_dir, "models", "whisper-medium")
        }
        self.asr_pipeline = None
        self.sample_rate = 16000
        self.current_model_size = None
        self.cc = OpenCC('t2s')  # 繁体转简体转换器
        self.ffmpeg_path = None
        
        # 设置FFmpeg路径
        self.set_ffmpeg_path()
    
    def set_ffmpeg_path(self):
        """设置FFmpeg路径并添加到系统PATH"""
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 尝试可能的FFmpeg路径
        possible_paths = [
            # 假设整合包结构：根目录/python/ffmpeg/bin
            os.path.join(os.path.dirname(current_dir), "python", "ffmpeg", "bin"),
            
            # 假设整合包结构：当前目录/python/ffmpeg/bin
            os.path.join(current_dir, "python", "ffmpeg", "bin"),
            
            # 假设FFmpeg在根目录下的ffmpeg/bin
            os.path.join(os.path.dirname(current_dir), "ffmpeg", "bin"),
            
            # 其他可能的路径
            os.path.join(current_dir, "ffmpeg", "bin"),
        ]
        
        found = False
        for path in possible_paths:
            ffmpeg_path = os.path.join(path, "ffmpeg.exe")
            ffprobe_path = os.path.join(path, "ffprobe.exe")
            
            if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
                # 设置AudioSegment的路径
                AudioSegment.converter = ffmpeg_path
                AudioSegment.ffprobe = ffprobe_path
                self.ffmpeg_path = path
                print(f"使用整合包内FFmpeg: {ffmpeg_path}")
                
                # 将FFmpeg路径添加到系统PATH
                os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
                print(f"已将FFmpeg路径添加到系统PATH: {path}")
                found = True
                break
        
        if not found:
            print("警告: 整合包内FFmpeg未找到，将使用系统环境变量中的FFmpeg")
    
    def convert_audio(self, input_path, output_path):
        """使用FFmpeg转换音频格式"""
        if not self.ffmpeg_path:
            # 如果没有找到整合包内的FFmpeg，使用系统命令
            command = f'ffmpeg -y -i "{input_path}" -ac 1 -ar {self.sample_rate} "{output_path}"'
        else:
            # 使用整合包内的FFmpeg
            ffmpeg_exe = os.path.join(self.ffmpeg_path, "ffmpeg.exe")
            command = f'"{ffmpeg_exe}" -y -i "{input_path}" -ac 1 -ar {self.sample_rate} "{output_path}"'
        
        try:
            result = subprocess.run(command, shell=True, check=True, 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg转换失败: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
    
    # 恢复 set_model 方法
    def set_model(self, model_size='base'):
        """加载指定的语音识别模型"""
        if self.current_model_size == model_size and self.asr_pipeline is not None:
            return  # 如果已经是所需的模型，则无需重新加载
        
        model_dir = self.model_dirs[model_size]
        
        # 验证模型目录是否存在
        if not os.path.exists(model_dir):
            # 尝试创建目录（如果可能）
            os.makedirs(model_dir, exist_ok=True)
            
            # 如果目录仍然不存在，提示用户下载模型
            if not os.path.exists(model_dir):
                print(f"错误: 模型目录不存在: {model_dir}")
                print("请下载模型并放置到该目录")
                print(f"模型下载地址: https://huggingface.co/openai/whisper-{model_size}")
                self.asr_pipeline = None
                return
        
        print(f"从本地加载语音识别模型: {model_dir}")
        
        try:
            # 使用更高效的 pipeline API
            self.asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=model_dir,
                device=0 if torch.cuda.is_available() else -1,
            )
            
            self.current_model_size = model_size
            print("语音识别模型加载完成")
        except Exception as e:
            print(f"加载语音识别模型失败: {str(e)}")
            traceback.print_exc()
            self.asr_pipeline = None
    
    def generate_subtitles(self, audio_path, language='zh', output_srt="subtitles.srt"):
        """从音频文件生成字幕"""
        if self.asr_pipeline is None:
            self.set_model('base')  # 默认使用base模型
        
        if self.asr_pipeline is None:
            print("无法加载语音识别模型，跳过字幕生成")
            return None
        
        try:
            # 创建临时WAV文件路径
            temp_path = "temp_audio.wav"
            
            # 使用FFmpeg转换音频格式
            if not self.convert_audio(audio_path, temp_path):
                print("音频格式转换失败，跳过字幕生成")
                return None
            
            # 生成识别结果 - 使用更高级的参数
            result = self.asr_pipeline(
                temp_path,
                return_timestamps=True,  # 获取时间戳
                generate_kwargs={
                    "task": "transcribe",
                    "language": language,  # 语言设置
                    "max_new_tokens": 450,  # 增加最大token数
                    "num_beams": 5,  # 使用更多beam提高准确性
                    "temperature": 0.1,  # 降低temperature减少随机性
                },
                chunk_length_s=30,  # 分块处理长音频
                stride_length_s=[6, 3],  # 重叠区域减少截断
                batch_size=4,  # 批处理提高效率
            )
            
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # 处理结果
            segments = result["chunks"]
            
            # 生成SRT字幕文件
            srt_content = ""
            for i, segment in enumerate(segments, start=1):
                start_time = segment["timestamp"][0]
                end_time = segment["timestamp"][1]
                text = segment["text"].strip()
                
                # 繁体转简体
                text = self.cc.convert(text)
                
                # 转换时间格式
                start_srt = self._format_time(start_time)
                end_srt = self._format_time(end_time)
                
                srt_content += f"{i}\n{start_srt} --> {end_srt}\n{text}\n\n"
            
            with open(output_srt, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            return output_srt
        except Exception as e:
            print(f"生成字幕失败: {str(e)}")
            traceback.print_exc()
            # 确保清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
    
    def _format_time(self, seconds):
        """秒数转换为SRT时间格式"""
        if seconds is None:
            return "00:00:00,000"
            
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def cleanup(self):
        """清理资源"""
        if self.asr_pipeline is not None:
            # 显式删除管道并释放显存
            del self.asr_pipeline
            self.asr_pipeline = None
            self.current_model_size = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("ASR模型已从显存卸载")