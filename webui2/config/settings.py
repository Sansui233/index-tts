"""
Configuration and settings for IndexTTS WebUI
"""

import argparse
import os
import sys


def set_ffmpeg_path():
    """Set FFmpeg path in environment variables"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))

    possible_paths = [
        os.path.join(os.path.dirname(root_dir), "python", "ffmpeg", "bin"),
        os.path.join(root_dir, "python", "ffmpeg", "bin"),
        os.path.join(os.path.dirname(root_dir), "ffmpeg", "bin"),
        os.path.join(root_dir, "ffmpeg", "bin"),
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


def setup_python_path():
    """Setup Python path for imports"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))

    sys.path.append(root_dir)
    sys.path.append(os.path.join(root_dir, "indextts"))
    sys.path.append("F:\\miniconda3\\envs\\index-tts")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="IndexTTS WebUI")
    parser.add_argument(
        "--verbose", action="store_true", default=False, help="Enable verbose mode"
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Port to run the web UI on"
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to run the web UI on"
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        default="checkpoints",
        help="Model checkpoints directory",
    )
    return parser.parse_args()


def validate_model_files(model_dir):
    """Validate required model files exist"""
    if not os.path.exists(model_dir):
        print(
            f"Model directory {model_dir} does not exist. Please download the model first."
        )
        sys.exit(1)

    required_files = [
        "bigvgan_generator.pth",
        "bpe.model",
        "gpt.pth",
        "config.yaml",
    ]

    for file in required_files:
        file_path = os.path.join(model_dir, file)
        if not os.path.exists(file_path):
            print(f"Required file {file_path} does not exist. Please download it.")
            sys.exit(1)


def setup_directories():
    """Create necessary directories"""
    directories = ["outputs/tasks", "prompts", "samples"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Constants
SAMPLES_DIR = "samples"
