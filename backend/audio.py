"""Audio resource index: every file the WebUI plays, downloads or references."""

import shutil
from pathlib import Path
from .config import AUDIO_EXTENSIONS, ROOT
from .storage import uid

SAMPLES = (ROOT / "samples").resolve()
MAX_UPLOAD = 500 * 1024 * 1024


def display_name(path):
    """Original file name; samples keep their folder, e.g. 胡桃/1.wav."""
    path = Path(path).resolve()
    return path.relative_to(SAMPLES).as_posix() if path.is_relative_to(SAMPLES) else path.name


class Audio:
    def __init__(self, store, tasks):
        self.store, self.tasks = store, tasks

    def new_path(self, suffix, folder="audio/files"):
        path = self.store.path(f"{folder}/{uid()}{suffix.lower()}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def register(self, path, name=None, copy=False):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError("音频文件不存在")
        if path.suffix.lower() not in AUDIO_EXTENSIONS | {".srt"}:
            raise ValueError("不支持的文件类型")
        name = name or display_name(path)
        if copy:
            target = self.new_path(path.suffix)
            shutil.copy2(path, target)
            path = target
        if not path.is_relative_to(self.store.root):
            raise ValueError("资源必须位于 data 目录")
        return self.store.create(
            "audio",
            {
                "name": name,
                "path": self.store.relative(path),
                "size": path.stat().st_size,
            },
        )

    def upload(self, stream, filename):
        suffix = Path(filename).suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            raise ValueError("不支持的音频类型")
        path = self.new_path(suffix)
        try:
            size = 0
            with path.open("wb") as target:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise ValueError("音频不能超过 500 MB")
                    target.write(chunk)
            if not size:
                raise ValueError("空文件")
            return self.register(path, Path(filename).name)
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def path(self, key):
        path = self.store.path(self.store.get("audio", key)["path"])
        if not path.is_file():
            raise ValueError("资源文件缺失")
        return path

    def sources(self):
        if not SAMPLES.exists():
            return []
        names = (
            p.relative_to(SAMPLES).as_posix()
            for p in SAMPLES.rglob("*")
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
        )
        return [{"name": name, "path": name} for name in names]

    def import_source(self, relative):
        path = (SAMPLES / relative).resolve()
        if not path.is_relative_to(SAMPLES):
            raise ValueError("仅支持 samples 内的音频")
        return self.register(path, copy=True)

    def referenced(self, exclude_session=None):
        """Ids cleanup must keep: role audio, bindings, take references, active tasks."""
        ids = set(self.tasks.active_audio_ids())
        for role in self.store.list("roles"):
            ids.update(role["audio_ids"])
        for entry in self.store.list("presets") + self.store.list("sessions"):
            if entry["id"] == exclude_session:
                continue
            ids.update(b.get("audio_id") for b in entry["bindings"])
            for line in entry.get("lines", []):
                for take in line["takes"]:
                    ids.add(take.get("snapshot", {}).get("audio_id"))
                    if take["id"] == line["current_take_id"]:
                        ids.add(take.get("audio_id"))
        ids.discard(None)
        return ids
