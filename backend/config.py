import os
from pathlib import Path

# Repository root: checkpoints/, samples/, outputs/ and data/ live here.
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WEBUI3_DATA", ROOT / "data")).resolve()
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
