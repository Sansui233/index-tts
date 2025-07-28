"""
Preset management utilities for multi_dialog tab
"""

import json
import os
from typing import Any, Dict, List, Optional


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


# Initialize preset manager
preset_manager = PresetManager()
