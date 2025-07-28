"""
Preset management utilities for multi_dialog tab
"""

import json
import os
from typing import Any, Dict, List, Optional


class PresetManager:
    """Manages loading, saving, and deleting presets for multi_dialog tab"""

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


def collect_preset_data(
    speakers_data: Dict,
    interval: float,
    gen_subtitle: bool,
    model_choice: str,
    subtitle_lang: str,
    bgm_volume: float,
    bgm_loop: bool,
    advanced_params: List,
    audio_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Collect current input parameters into preset data structure"""
    from .server_audio import server_audio_manager

    preset_data = {
        "speakers": {},
        "settings": {
            "interval": interval,
            "gen_subtitle": gen_subtitle,
            "model_choice": model_choice,
            "subtitle_lang": subtitle_lang,
            "bgm_volume": bgm_volume,
            "bgm_loop": bgm_loop,
        },
        "advanced_params": {},
    }

    # Collect speaker data (names and server audio paths if applicable)
    for i in range(1, 7):  # speaker1 to speaker6
        speaker_name = speakers_data.get(f"speaker{i}_name", f"角色{i}")
        preset_data["speakers"][f"speaker{i}_name"] = speaker_name

        # Check if there's audio data and if it's a server file
        if audio_data:
            audio_path = audio_data.get(f"speaker{i}_audio")
            if audio_path and server_audio_manager.is_server_audio(audio_path):
                relative_path = server_audio_manager.get_relative_path(audio_path)
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


def apply_preset_data(preset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert preset data to gradio update format"""
    updates = {}

    if not preset_data:
        return updates

    # Apply speaker names and audio paths
    speakers = preset_data.get("speakers", {})
    for i in range(1, 7):
        speaker_name_key = f"speaker{i}_name"
        speaker_audio_key = f"speaker{i}_audio"

        if speaker_name_key in speakers:
            updates[speaker_name_key] = speakers[speaker_name_key]

        # Handle server audio paths - use the same key for server audio dropdown
        if speaker_audio_key in speakers:
            server_audio_path = speakers[speaker_audio_key]
            if server_audio_path and os.path.exists(server_audio_path):
                # Update the server audio dropdown with the path
                updates[f"speaker{i}_server_audio"] = server_audio_path
                # Also set the audio component to the server file
                updates[speaker_audio_key] = server_audio_path

    # Apply settings
    settings = preset_data.get("settings", {})
    settings_mapping = {
        "interval": "interval",
        "gen_subtitle": "gen_subtitle_multi",
        "model_choice": "model_choice_multi",
        "subtitle_lang": "subtitle_lang_multi",
        "bgm_volume": "bgm_volume_multi",
        "bgm_loop": "bgm_loop_multi",
    }

    for preset_key, component_key in settings_mapping.items():
        if preset_key in settings:
            updates[component_key] = settings[preset_key]

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
            updates[param_name] = advanced[param_name]

    return updates
