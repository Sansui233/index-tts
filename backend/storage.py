"""Atomic JSON records; callers hold the shared lock across read/modify/write."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid4().hex


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("资源路径超出 data 目录")
        return path

    def record_path(self, kind, key):
        if kind not in {"roles", "presets", "projects", "sessions", "audio", "tasks"}:
            raise ValueError("未知资源类型")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", key):
            raise ValueError("无效资源 ID")
        return self.path(f"{kind}/{key}.json")

    def get(self, kind, key):
        with self.lock:
            path = self.record_path(kind, key)
            if not path.exists():
                raise KeyError(f"{kind}/{key} 不存在")
            return json.loads(path.read_text(encoding="utf-8"))

    def list(self, kind):
        with self.lock:
            return [
                json.loads(p.read_text(encoding="utf-8"))
                for p in self.path(kind).glob("*.json")
            ]

    def write_json(self, path, data):
        path = self.path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + f".{uid()}.tmp")
        try:
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def save(self, kind, record):
        with self.lock:
            record["updated_at"] = now()
            self.write_json(self.record_path(kind, record["id"]), record)
            return record

    def create(self, kind, fields, key=None):
        with self.lock:
            record = {
                **fields,
                "id": key or uid(),
                "schema_version": 1,
                "created_at": now(),
                "updated_at": now(),
            }
            if self.record_path(kind, record["id"]).exists():
                raise ValueError("资源已存在")
            return self.save(kind, record)

    def delete(self, kind, key):
        with self.lock:
            self.get(kind, key)
            self.record_path(kind, key).unlink()
