"""
TTS Engine wrapper and management
"""

import json
import os

from indextts.infer import IndexTTS
from tools.i18n.i18n import I18nAuto


class TTSManager:
    """TTS Engine manager with caching and configuration"""

    def __init__(self, model_dir, cfg_path):
        self.model_dir = model_dir
        self.cfg_path = cfg_path
        self.tts = None
        self.i18n = I18nAuto(language="zh_CN")
        self.example_cases = []
        self._load_tts()
        self._load_examples()

    def _load_tts(self):
        """Initialize TTS engine"""
        self.tts = IndexTTS(
            model_dir=self.model_dir,
            cfg_path=self.cfg_path,
        )

    def _load_examples(self):
        """Load example cases from file"""
        try:
            with open("tests/cases.jsonl", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    example = json.loads(line)
                    self.example_cases.append(
                        [
                            os.path.join(
                                "tests",
                                example.get("prompt_audio", "sample_prompt.wav"),
                            ),
                            example.get("text"),
                            ["普通推理", "批次推理"][example.get("infer_mode", 0)],
                        ]
                    )
        except FileNotFoundError:
            print("Warning: tests/cases.jsonl not found, no examples loaded")

    def get_tts(self):
        """Get TTS instance"""
        return self.tts

    def get_examples(self):
        """Get example cases"""
        return self.example_cases
