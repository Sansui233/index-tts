"""
Preset management utilities for multi_dialog tab
"""

import json
import os
from typing import Any, Dict, List, Optional

import gradio as gr

from .server_audio_manager import server_audio_mgr


class PresetManager:
    """Manages loading, saving, and deleting presets for multi_dialog tab"""

    _instance = None  # singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, preset_dir: str = "webui2/presets/multi_dialog"):
        self.preset_dir = preset_dir
        os.makedirs(self.preset_dir, exist_ok=True)

    def get_preset_list(self) -> List[str]:
        """Get list of available preset names"""
        try:
            files = [f[:-5] for f in os.listdir(self.preset_dir) if f.endswith(".json")]
            return sorted(files)
        except Exception:
            return []

    def load_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Load preset from JSON file"""
        if not preset_name:
            return None

        preset_path = os.path.join(self.preset_dir, f"{preset_name}.json")

        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading preset {preset_name}: {e}")
            return None

    def save_preset(self, preset_name: str, preset_data: Dict[str, Any]) -> bool:
        """Save preset to JSON file"""
        if not preset_name or not preset_data:
            return False

        preset_path = os.path.join(self.preset_dir, f"{preset_name}.json")

        try:
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(preset_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving preset {preset_name}: {e}")
            gr.Error(f"Error saving preset {preset_name}: {e}")
            return False

    def delete_preset(self, preset_name: str) -> bool:
        """Delete preset file"""
        if not preset_name:
            return False

        preset_path = os.path.join(self.preset_dir, f"{preset_name}.json")

        try:
            if os.path.exists(preset_path):
                os.remove(preset_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting preset {preset_name}: {e}")
            return False

    @staticmethod
    def collect_preset_data(
        speaker_count: int,
        speakers_data: Dict,
        audio_data: Dict,
        interval: float,
        gen_subtitle: bool,
        subtitle_model: str,
        subtitle_lang: str,
        bgm_volume: float,
        bgm_loop: bool,
        advanced_params: List,
    ) -> Dict[str, Any]:
        """Collect current input parameters into preset data structure"""
        preset_data = {
            "speakers": {},
            "settings": {
                "interval": interval,
                "gen_subtitle": gen_subtitle,
                "subtitle_model": subtitle_model,
                "subtitle_lang": subtitle_lang,
                "bgm_volume": bgm_volume,
                "bgm_loop": bgm_loop,
            },
            "advanced_params": {},
        }

        # Collect speaker data (names and server audio paths if applicable)
        for i in range(1, speaker_count + 1):  # speaker1 to speaker6
            speaker_name = speakers_data.get(f"speaker{i}_name", f"角色{i}")
            preset_data["speakers"][f"speaker{i}_name"] = speaker_name

            # Check if there's audio data and if it's a server file
            if audio_data:
                audio_path = audio_data.get(f"speaker{i}_audio")
                if audio_path and server_audio_mgr.is_server_audio(audio_path):
                    relative_path = server_audio_mgr.get_relative_path(audio_path)
                    preset_data["speakers"][f"speaker{i}_audio"] = relative_path

        # Collect advanced parameters
        param_names = [
            "do_sample",
            "top_p",
            "top_k",
            "temperature",
            "length_penalty",
            "num_beams",
            "repetition_penalty",
            "max_mel_tokens",
        ]

        for i, param_name in enumerate(param_names):
            if i < len(advanced_params):
                preset_data["advanced_params"][param_name] = advanced_params[i]

        return preset_data

    @staticmethod
    def flatten_preset_config(
        preset_data: Dict[str, Any],
    ) -> tuple[Dict[str, Any], int]:
        """Convert preset data to gradio update format
        由于 gradio output 是 flat list
        返回一个展平的 dict 映射
        使用 result.get("key") 可以 return None
        以满足 json 文件可以是 optional，同时输出到 gradio output 的需要有值
        """
        flat_config = {}

        # flatten speaker names and audio paths
        speakers = preset_data.get("speakers", {})
        len_speakers = 0
        for i in range(1, 50):
            speaker_name_key = f"speaker{i}_name"
            speaker_audio_key = f"speaker{i}_audio"

            if speaker_name_key in speakers:
                flat_config[speaker_name_key] = speakers[speaker_name_key]
                len_speakers += 1
            else:
                continue

            # Handle server audio paths - use the same key for server audio dropdown
            if speaker_audio_key in speakers:
                server_audio_path = speakers[speaker_audio_key]
                if server_audio_path and os.path.exists(server_audio_path):
                    flat_config[speaker_audio_key] = server_audio_path
                else:
                    flat_config[speaker_audio_key] = None

        # flatten settings
        settings = preset_data.get("settings", {})
        settings_mapping = {
            "interval": "interval",
            "gen_subtitle": "gen_subtitle_multi",
            "subtitle_model": "subtitle_model_multi",
            "subtitle_lang": "subtitle_lang_multi",
            "bgm_volume": "bgm_volume_multi",
            "bgm_loop": "bgm_loop_multi",
        }

        for preset_key, component_key in settings_mapping.items():
            if preset_key in settings:
                flat_config[component_key] = settings[preset_key]

        # Apply advanced parameters
        advanced = preset_data.get("advanced_params", {})
        param_names = [
            "do_sample",
            "top_p",
            "top_k",
            "temperature",
            "length_penalty",
            "num_beams",
            "repetition_penalty",
            "max_mel_tokens",
        ]

        for param_name in param_names:
            if param_name in advanced:
                flat_config[param_name] = advanced[param_name]

        return flat_config, len_speakers


# Initialize preset manager
preset_mgr = PresetManager()
