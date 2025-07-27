"""
UI module
"""
from .components import create_header
from .handlers import (
    gen_single, gen_multi_dialog, on_input_text_change, update_prompt_audio
)
from .tabs import create_single_audio_tab, create_multi_dialog_tab, create_subtitle_only_tab
