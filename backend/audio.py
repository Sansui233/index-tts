import shutil
from pathlib import Path
from .config import AUDIO_EXTENSIONS, ROOT
from .storage import uid


class Audio:
    def __init__(self, store):
        self.store = store

    def register(self, path, name=None, copy=False):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError("音频文件不存在")
        if path.suffix.lower() not in AUDIO_EXTENSIONS | {".srt"}:
            raise ValueError("不支持的文件类型")
        if copy:
            target = self.store.path(f"audio/files/{uid()}{path.suffix.lower()}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            path = target
        if not path.is_relative_to(self.store.root):
            raise ValueError("资源必须位于 WebUI3 data 目录")
        return self.store.create(
            "audio",
            {
                "name": name or path.name,
                "path": path.relative_to(self.store.root).as_posix(),
                "size": path.stat().st_size,
            },
        )

    def path(self, key):
        path = self.store.path(self.store.get("audio", key)["path"])
        if not path.is_file():
            raise ValueError("资源文件缺失")
        return path

    def sources(self):
        base = (ROOT / "samples").resolve()
        if not base.exists():
            return []
        return [
            {
                "name": p.relative_to(base).as_posix(),
                "path": p.relative_to(base).as_posix(),
            }
            for p in base.rglob("*")
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
        ]

    def import_source(self, relative):
        base = (ROOT / "samples").resolve()
        path = (base / relative).resolve()
        if not path.is_relative_to(base):
            raise ValueError("仅支持 samples 内的音频")
        return self.register(path, copy=True)

    def referenced(self, exclude_session=None):
        ids = set()
        for role in self.store.list("roles"):
            ids.update(role["audio_ids"])
        for entry in self.store.list("presets") + self.store.list("sessions"):
            if entry["id"] == exclude_session:
                continue
            ids.update(b["audio_id"] for b in entry["bindings"] if b.get("audio_id"))
            for line in entry.get("lines", []):
                for take in line["takes"]:
                    if take.get("snapshot", {}).get("audio_id"):
                        ids.add(take["snapshot"]["audio_id"])
                    if take["id"] == line["current_take_id"] and take.get("audio_id"):
                        ids.add(take["audio_id"])
        for task in self.store.list("tasks"):
            if task["status"] in {"queued", "running"}:
                ids.update(task.get("audio_ids", []))
        return ids
