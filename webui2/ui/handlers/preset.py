import os
from typing import Any, Dict, List, Optional

import gradio as gr

from webui2.utils import preset_manager
from webui2.utils.server_audio import server_audio_manager


def collect_preset_data(
    speakers_data: Dict,
    interval: float,
    gen_subtitle: bool,
    subtitle_model: str,
    subtitle_lang: str,
    bgm_volume: float,
    bgm_loop: bool,
    advanced_params: List,
    audio_data: Optional[Dict] = None,
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
        "subtitle_model": "subtitle_model_multi",
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


def load_preset_handler(preset_name):
    """Handle loading a preset"""
    if not preset_name:
        return [gr.update()] * 26  # Return empty updates for all components (20 + 6 server audio dropdowns)

    preset_data = preset_manager.load_preset(preset_name)
    if not preset_data:
        return [gr.update()] * 26

    updates = apply_preset_data(preset_data)

    # Return updates in the order of components
    result = []
    # Speaker names (6)
    for i in range(1, 7):
        key = f"speaker{i}_name"
        result.append(gr.update(value=updates.get(key, f"角色{i}")))

    # Server audio dropdowns (6)
    for i in range(1, 7):
        key = f"speaker{i}_server_audio"
        result.append(gr.update(value=updates.get(key, "")))

    # Settings (6)
    result.append(gr.update(value=updates.get("interval", 0.5)))
    result.append(gr.update(value=updates.get("gen_subtitle_multi", True)))
    result.append(gr.update(value=updates.get("subtitle_model_multi", "base")))
    result.append(gr.update(value=updates.get("subtitle_lang_multi", "zh")))
    result.append(gr.update(value=updates.get("bgm_volume_multi", 0.3)))
    result.append(gr.update(value=updates.get("bgm_loop_multi", True)))

    # Advanced params (8)
    result.append(gr.update(value=updates.get("do_sample", True)))
    result.append(gr.update(value=updates.get("top_p", 0.8)))
    result.append(gr.update(value=updates.get("top_k", 30)))
    result.append(gr.update(value=updates.get("temperature", 1.0)))
    result.append(gr.update(value=updates.get("length_penalty", 0.0)))
    result.append(gr.update(value=updates.get("num_beams", 3)))
    result.append(gr.update(value=updates.get("repetition_penalty", 10.0)))
    result.append(gr.update(value=updates.get("max_mel_tokens", 600)))

    return result
