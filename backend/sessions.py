"""Projects, sessions, lines and the Take lifecycle. Mutations hold the store lock."""

import shutil
from copy import deepcopy
from .dialogue import parse_dialogue
from .storage import now, uid

SORTS = {"name", "updated_at", "created_at"}


def folder(project_id, session_id):
    return f"projects/{project_id}/sessions/{session_id}"


def find_line(session, key):
    for line in session["lines"]:
        if line["id"] == key:
            return line
    raise KeyError("句子不存在")


def current_take(line):
    return next((t for t in line["takes"] if t["id"] == line["current_take_id"]), None)


class Sessions:
    def __init__(self, store, tasks, audio, library):
        self.store, self.tasks, self.audio, self.library = store, tasks, audio, library

    # Persistence

    def save(self, session):
        session["text"] = "\n".join(f"[{l['speaker']}] {l['text']}" for l in session["lines"])
        saved = self.store.save("sessions", session)
        # Mirror beside the generated files; the top-level record is used for listing.
        self.store.write_json(f"{folder(saved['project_id'], saved['id'])}/index.json", saved)
        return saved

    def edit(self, key, change, idle=True):
        """Load, apply `change(session)` and save under the lock."""
        with self.store.lock:
            if idle:
                self.tasks.ensure_idle([key])
            session = self.store.get("sessions", key)
            change(session)
            return self.save(session)

    def of_project(self, project_id):
        return [s for s in self.store.list("sessions") if s["project_id"] == project_id]

    def summaries(self, project_id=None, sort="updated_at"):
        if sort not in SORTS:
            raise ValueError("不支持的排序")
        records = self.of_project(project_id) if project_id else self.store.list("sessions")
        items = [
            {k: v for k, v in s.items() if k not in {"lines", "text"}} | {"line_count": len(s["lines"])}
            for s in records
        ]
        return sorted(items, key=lambda s: s[sort], reverse=sort != "name")

    # Sessions and projects

    def create(self, fields):
        with self.store.lock:
            self.store.get("projects", fields["project_id"])
            record = self.store.create(
                "sessions", {**fields, "lines": [], "next_index": 0, "text": "", "outputs": []}
            )
            return self.save(record)

    def update(self, key, request):
        with self.store.lock:
            self.tasks.ensure_idle([key])
            self.library.validate_bindings(request.bindings)
            self.store.get("projects", request.project_id)
            session = self.store.get("sessions", key)
            if session["project_id"] != request.project_id:
                self._move_files(key, session["project_id"], request.project_id)
            session.update(request.model_dump())
            return self.save(session)

    def _move_files(self, key, old_project, new_project):
        source = self.store.path(folder(old_project, key))
        target = self.store.path(folder(new_project, key))
        if not source.exists():
            return
        if target.exists():
            raise ValueError("目标 session 目录已存在")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        for resource in self.store.list("audio"):
            old = self.store.path(resource["path"])
            if old.is_relative_to(source):
                resource["path"] = self.store.relative(target / old.relative_to(source))
                self.store.save("audio", resource)

    def delete(self, key):
        with self.store.lock:
            self.tasks.ensure_idle([key])
            session = self.store.get("sessions", key)
            root = self.store.path(folder(session["project_id"], key))
            owned = [
                r for r in self.store.list("audio") if self.store.path(r["path"]).is_relative_to(root)
            ]
            if self.audio.referenced(exclude_session=key) & {r["id"] for r in owned}:
                raise ValueError("session 音频仍被其他角色、session 或任务引用，请先解除引用")
            for resource in owned:
                self.store.delete("audio", resource["id"])
            shutil.rmtree(root, ignore_errors=True)
            self.store.delete("sessions", key)

    def delete_project(self, key):
        with self.store.lock:
            self.store.get("projects", key)
            sessions = self.of_project(key)
            self.tasks.ensure_idle([s["id"] for s in sessions])
            for session in sessions:
                self.delete(session["id"])
            self.store.delete("projects", key)

    # Lines

    def add_line(self, session, fields):
        line = {
            **fields,
            "id": uid(),
            "index": session["next_index"],
            "takes": [],
            "current_take_id": None,
            "next_take_index": 1,
            "revision": 0,
            "selection_revision": 0,
        }
        session["next_index"] += 1
        session["lines"].append(line)
        return line

    def replace_text(self, key, text):
        parsed = parse_dialogue(text)

        def change(session):
            if session["lines"]:
                raise ValueError("已有句子请逐句编辑或新增，以保留 index 和 Take；批量文本用于空 session")
            for fields in parsed:
                self.add_line(session, fields)

        return self.edit(key, change)

    def update_line(self, key, line_id, fields):
        def change(session):
            line = find_line(session, line_id)
            line.update(fields)
            line["revision"] += 1

        # Editing during generation is allowed; the revision keeps the user's selection.
        return self.edit(key, change, idle=False)

    def delete_line(self, key, line_id):
        with self.store.lock:
            # Mark every take unused first, so failures keep the line for a retry.
            self.edit(key, lambda s: find_line(s, line_id).update(current_take_id=None))
            if self.cleanup([key], line_id)["failures"]:
                raise ValueError("部分 Take 删除失败，请重试清理后再删除句子")
            return self.edit(
                key, lambda s: s.update(lines=[l for l in s["lines"] if l["id"] != line_id])
            )

    def reorder(self, key, line_ids):
        def change(session):
            if sorted(line_ids) != sorted(l["id"] for l in session["lines"]):
                raise ValueError("排序必须包含所有句子且不重复")
            session["lines"] = [find_line(session, i) for i in line_ids]

        return self.edit(key, change)

    # Takes

    def snapshot(self, session, line):
        binding = next((b for b in session["bindings"] if b["speaker"] == line["speaker"]), None)
        if not binding or not binding.get("audio_id"):
            raise ValueError(f"句子 #{line['index']} 的角色 {line['speaker']} 未绑定参考音频")
        self.audio.path(binding["audio_id"])
        return {
            "text": line["text"],
            "speaker": line["speaker"],
            "audio_id": binding["audio_id"],
            "generation": deepcopy(session["generation"]),
        }

    def reserve(self, key, line_ids=None):
        """Allocate take indexes for lines (all when None) before queueing generation."""
        jobs = []

        def change(session):
            lines = [find_line(session, i) for i in line_ids] if line_ids else session["lines"]
            if not lines:
                raise ValueError("没有句子")
            snapshots = [self.snapshot(session, line) for line in lines]
            for line, snapshot in zip(lines, snapshots):
                take = {
                    "id": uid(),
                    "take_index": line["next_take_index"],
                    "snapshot": snapshot,
                    "created_at": now(),
                }
                line["next_take_index"] += 1
                path = self.store.path(
                    f"{folder(session['project_id'], key)}/takes/{line['id']}/{take['take_index']}_{take['id']}.wav"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                jobs.append(
                    {
                        "line_id": line["id"],
                        "index": line["index"],
                        "take": take,
                        "path": path,
                        "revision": line["revision"],
                        "selection_revision": line["selection_revision"],
                    }
                )

        self.edit(key, change, idle=False)
        return jobs

    def complete(self, key, job):
        def change(session):
            line = find_line(session, job["line_id"])
            take = job["take"]
            take["audio_id"] = self.audio.register(
                job["path"], f"#{line['index']} · Take {take['take_index']}"
            )["id"]
            line["takes"].append(take)
            # Keep a selection or edit the user made while this take was generating.
            if (line["revision"], line["selection_revision"]) == (job["revision"], job["selection_revision"]):
                line["current_take_id"] = take["id"]

        return self.edit(key, change, idle=False)

    def select(self, key, line_id, take_id):
        def change(session):
            line = find_line(session, line_id)
            take = next((t for t in line["takes"] if t["id"] == take_id), None)
            if not take or not take.get("audio_id"):
                raise ValueError("Take 不存在或音频缺失")
            self.audio.path(take["audio_id"])
            line["current_take_id"] = take_id
            line["selection_revision"] += 1

        return self.edit(key, change, idle=False)

    def add_output(self, key, audio_id):
        return self.edit(key, lambda s: s["outputs"].append(audio_id), idle=False)

    def cleanup(self, session_ids, line_id=None):
        """Delete non-current takes; failures are reported and kept for retry."""
        with self.store.lock:
            self.tasks.ensure_idle(session_ids)
            result = {"deleted": 0, "bytes": 0, "failures": []}
            # Protect by path too, in case imported data shares a file between records.
            protected = {self.store.get("audio", i)["path"] for i in self.audio.referenced()}
            for key in session_ids:
                session = self.store.get("sessions", key)
                lines = [find_line(session, line_id)] if line_id else session["lines"]
                for line in lines:
                    allowed = self.store.path(f"{folder(session['project_id'], key)}/takes/{line['id']}")
                    keep = []
                    for take in line["takes"]:
                        if take["id"] == line["current_take_id"]:
                            keep.append(take)
                            continue
                        try:
                            result["bytes"] += self._delete_take(take, allowed, protected)
                            result["deleted"] += 1
                        except (OSError, ValueError, KeyError) as error:
                            keep.append(take)
                            result["failures"].append(
                                {"session_id": key, "index": line["index"], "take_id": take["id"], "error": str(error)}
                            )
                    line["takes"] = keep
                self.save(session)
            return result

    def _delete_take(self, take, allowed, protected):
        if not take.get("audio_id"):
            return 0
        resource = self.store.get("audio", take["audio_id"])
        path = self.store.path(resource["path"])
        if resource["path"] in protected or not path.is_relative_to(allowed):
            raise ValueError("资源仍被使用或不属于该句 Take 目录")
        size = path.stat().st_size if path.exists() else 0
        path.unlink(missing_ok=True)
        self.store.delete("audio", take["audio_id"])
        return size
