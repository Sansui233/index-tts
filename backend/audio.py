"""Audio resource index: every file the WebUI plays, downloads or references."""

import filecmp
import hashlib
import re
from pathlib import Path
from .config import AUDIO_EXTENSIONS, ROOT
from .storage import uid

SAMPLES = (ROOT / "samples").resolve()
MAX_UPLOAD = 500 * 1024 * 1024


def title(text, limit=40):
    """Display name for generated audio: no extension (it is not a file name; downloads add
    the real suffix). Drops characters Windows forbids, since it becomes the download name."""
    return re.sub(r'[\\/:*?"<>|\s]+', " ", text).strip()[:limit].strip() or "output"


def sample_id(relative):
    """Stable id for a file in samples/, so bindings survive rescans."""
    return "sample-" + hashlib.sha1(relative.encode("utf-8")).hexdigest()[:24]


class Audio:
    def __init__(self, store, tasks):
        self.store, self.tasks = store, tasks

    def new_path(self, suffix, folder="audio/files"):
        """Fresh file under data/; the default folder holds uploads."""
        path = self.store.path(f"{folder}/{uid()}{suffix.lower()}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def register(self, path, name=None):
        """Index a file already inside data/ (upload, output, take, merge)."""
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError("音频文件不存在")
        if path.suffix.lower() not in AUDIO_EXTENSIONS | {".srt"}:
            raise ValueError("不支持的文件类型")
        name = name or path.name
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
            if existing := self.same_as(path, size):
                path.unlink()
                return existing
            return self.register(path, Path(filename).name)
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def same_as(self, path, size):
        """Record of an identical file already known: an earlier upload, or a file in samples/
        (referenced in place). Uploading the same audio twice must not store it twice."""
        for record in self.store.list("audio"):
            if record.get("source") == "samples" or not record["path"].startswith("audio/files/") or record.get("size") != size:
                continue
            other = self.store.path(record["path"])
            if other != path and other.is_file() and filecmp.cmp(path, other, shallow=False):
                return record
        for other in SAMPLES.rglob("*") if SAMPLES.exists() else ():
            if other.suffix.lower() in AUDIO_EXTENSIONS and other.is_file() and other.stat().st_size == size and filecmp.cmp(path, other, shallow=False):
                return self.sample(other.resolve())
        return None

    def file(self, record):
        """Location of a record: samples are referenced in place, everything else is in data/."""
        if record.get("source") != "samples":
            return self.store.path(record["path"])
        path = (SAMPLES / record["path"]).resolve()
        if not path.is_relative_to(SAMPLES):
            raise ValueError("资源路径超出 samples 目录")
        return path

    def path(self, key):
        path = self.file(self.store.get("audio", key))
        if not path.is_file():
            raise ValueError("资源文件缺失")
        return path

    def folder(self, name):
        """Ids of the audio under samples/<name>/ (recursive), registered in place on first sight."""
        root = (SAMPLES / name).resolve()
        if not name.strip() or root == SAMPLES or not root.is_relative_to(SAMPLES) or not root.is_dir():
            return []
        ids = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            ids.append(self.sample(path)["id"])
        return ids

    def sample(self, path):
        """Record for a file in samples/, referenced in place; the id is stable per path."""
        relative = path.relative_to(SAMPLES).as_posix()
        key = sample_id(relative)
        with self.store.lock:
            try:
                return self.store.get("audio", key)
            except KeyError:
                fields = {"name": relative, "path": relative, "source": "samples", "size": path.stat().st_size}
                return self.store.create("audio", fields, key=key)

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
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            raise ValueError("不支持的音频文件")
        return self.sample(path)

    def referenced(self, exclude_session=None):
        """Ids cleanup must keep: bindings, take references, active tasks."""
        ids = set(self.tasks.active_audio_ids())
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
