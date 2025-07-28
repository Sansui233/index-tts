"""
Server audio file management utilities
"""

import glob
import os
from typing import Dict, List, Optional, Tuple


class ServerAudioManager:
    """Manages server-side audio files for multi-dialog tab"""

    def __init__(self, base_audio_dirs: Optional[List[str]] = None):
        if base_audio_dirs is None:
            base_audio_dirs = [
                "samples",
                "samples/语音样本",
                "samples/卡维",
                "samples/流浪者",
                "samples/艾尔海森",
                "prompts",
            ]
        self.base_audio_dirs = base_audio_dirs
        self.supported_formats = [".wav", ".WAV", ".mp3", ".flac", ".m4a"]

    def get_server_audio_list(self) -> Dict[str, List[str]]:
        """Get categorized list of server audio files"""
        audio_files = {}

        for base_dir in self.base_audio_dirs:
            if not os.path.exists(base_dir):
                continue

            category_name = (
                os.path.basename(base_dir) if base_dir != "samples" else "通用样本"
            )
            if category_name == "":
                category_name = "根目录"

            files = []

            # Get all audio files in this directory
            for ext in self.supported_formats:
                pattern = os.path.join(base_dir, f"*{ext}")
                found_files = glob.glob(pattern)
                files.extend(found_files)

            if files:
                # Convert to relative paths for display, but keep full paths for loading
                display_files = []
                for file_path in sorted(files):
                    filename = os.path.basename(file_path)
                    display_files.append((filename, file_path))

                audio_files[category_name] = display_files

        return audio_files

    def get_flat_audio_choices(self) -> List[Tuple[str, str]]:
        """Get flattened list of audio choices for dropdown"""
        choices = [("选择服务器音频文件...", "")]
        audio_files = self.get_server_audio_list()

        for category, files in audio_files.items():
            for filename, filepath in files:
                display_name = f"[{category}] {filename}"
                choices.append((display_name, filepath))

        return choices

    def is_server_audio(self, file_path: str) -> bool:
        """Check if a file path is a server audio file"""
        if not file_path:
            return False

        # Check if the file path starts with any of our base directories
        for base_dir in self.base_audio_dirs:
            if file_path.startswith(base_dir) or file_path.startswith(
                os.path.abspath(base_dir)
            ):
                return True
        return False

    def get_relative_path(self, file_path: str) -> str:
        """Get relative path for server audio files"""
        if not self.is_server_audio(file_path):
            return file_path

        # Try to make it relative to the current working directory
        try:
            return os.path.relpath(file_path)
        except ValueError:
            return file_path


# Global instance
server_audio_manager = ServerAudioManager()
