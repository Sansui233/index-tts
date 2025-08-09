"""
Server audio file management utilities
"""

import os
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple


class ServerAudioManager:
    """Manages server-side audio files for multi-dialog tab"""

    def __init__(self, base_audio_dirs: Optional[List[str]] = None):
        if base_audio_dirs is None:
            base_audio_dirs = [
                "samples",
                "prompts",
            ]

        # 增加一级子目录
        audio_dirs = []
        for base_dir in base_audio_dirs:
            audio_dirs.append(base_dir)  # 先加上自己
            try:
                for name in os.listdir(base_dir):
                    full_path = os.path.join(base_dir, name)
                    if os.path.isdir(full_path):
                        audio_dirs.append(full_path)
            except FileNotFoundError:
                print(f"目录不存在: {base_dir}")
                continue

        self.base_audio_dirs = audio_dirs
        self.supported_formats = [".wav", ".mp3", ".flac", ".m4a", ".ogg"]

    def get_server_audio_list(self) -> Dict[str, List[str]]:
        """Get categorized list of server audio files\n
        return: Dict<category_name, display_files>\n
        - category_name: dirname\n
        - display_files: (filename, full_path)
        """
        audio_files = {}

        for base_dir in self.base_audio_dirs:
            if not os.path.exists(base_dir):
                continue

            category_name = os.path.basename(base_dir)
            if category_name == "":
                category_name = "根目录"

            # Get all audio files in this directory
            files = []
            for file in Path(base_dir).glob("*"):
                if file.is_file() and file.suffix.lower() in self.supported_formats:
                    files.append(str(file.as_posix()))

            # Convert files to list of tuples (filename, full_path)
            audio_files[category_name] = [
                (os.path.basename(file_path), file_path) for file_path in sorted(files)
            ]

        return audio_files

    def get_flat_audio_choices(self) -> List[Tuple[str, str]]:
        """Get flattened list of audio choices for dropdown\n
        return List of tuples (display_name, file_path)
        """
        choices = []
        audio_files = self.get_server_audio_list()

        for category, files in audio_files.items():
            for filename, filepath in files:
                if len(filename) > 23:
                    filename = filename[:20] + "..."
                display_name = f"[{category}] {filename}"
                choices.append((display_name, filepath))

        # print("[webui2] [Debug] Flattened audio choices:", len(choices), "items")
        return choices

    def is_server_audio(self, file_path: str | None) -> bool:
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
            return str(PurePosixPath(Path(file_path).relative_to(Path.cwd())))
        except ValueError:
            return file_path


# Global instance
server_audio_mgr = ServerAudioManager()
