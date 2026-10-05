"""Session index and Take lifecycle. All modifications share the store lock."""

from copy import deepcopy
from .dialogue import parse_dialogue
from .storage import now, uid


class Busy(ValueError):
    pass


class Sessions:
    def __init__(self, store, tasks, audio):
        self.store, self.tasks, self.audio = store, tasks, audio

    def available(self, ids):
        if self.tasks.busy(ids):
            raise Busy("该 session 有排队或运行中的任务，请等待完成或取消后操作")

    def create(self, fields):
        self.store.get("projects", fields["project_id"])
        return self.store.create(
            "sessions",
            {**fields, "lines": [], "next_index": 0, "text": "", "outputs": []},
        )

    def line(self, session, key):
        for line in session["lines"]:
            if line["id"] == key:
                return line
        raise KeyError("句子不存在")

    def save(self, session):
        session["text"] = "\n".join(
            f"[{line['speaker']}] {line['text']}" for line in session["lines"]
        )
        saved = self.store.save("sessions", session)
        # This session index lives beside its generated files; the top-level record enables listing.
        self.store.write_json(
            f"projects/{session['project_id']}/sessions/{session['id']}/index.json",
            saved,
        )
        return saved

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
        with self.store.lock:
            self.available([key])
            session = self.store.get("sessions", key)
            if session["lines"]:
                raise ValueError(
                    "已有句子请逐句编辑或新增，以保留 index 和 Take；批量文本用于空 session"
                )
            for fields in parsed:
                self.add_line(session, fields)
            return self.save(session)

    def snapshot(self, session, line):
        binding = next(
            (b for b in session["bindings"] if b["speaker"] == line["speaker"]), None
        )
        if not binding or not binding.get("audio_id"):
            raise ValueError(
                f"句子 #{line['index']} 的角色 {line['speaker']} 未绑定参考音频"
            )
        return {
            "text": line["text"],
            "speaker": line["speaker"],
            "audio_id": binding["audio_id"],
            "generation": deepcopy(session["generation"]),
        }

    def select(self, key, line_id, take_id):
        with self.store.lock:
            session = self.store.get("sessions", key)
            line = self.line(session, line_id)
            take = next((t for t in line["takes"] if t["id"] == take_id), None)
            if not take or not take.get("audio_id"):
                raise ValueError("Take 不存在或音频缺失")
            self.audio.path(take["audio_id"])
            line["current_take_id"] = take_id
            line["selection_revision"] += 1
            return self.save(session)

    def reserve(self, session_id, line_id):
        with self.store.lock:
            session = self.store.get("sessions", session_id)
            line = self.line(session, line_id)
            snapshot = self.snapshot(session, line)
            self.audio.path(snapshot["audio_id"])
            index = line["next_take_index"]
            line["next_take_index"] += 1
            self.save(session)
            take_id = uid()
            path = self.store.path(
                f"projects/{session['project_id']}/sessions/{session_id}/takes/{line_id}/{index}_{take_id}.wav"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            return (
                {
                    "id": take_id,
                    "take_index": index,
                    "snapshot": snapshot,
                    "created_at": now(),
                },
                path,
                line["revision"],
                line["selection_revision"],
            )

    def complete(self, key, line_id, take, path, revision, selection_revision):
        with self.store.lock:
            session = self.store.get("sessions", key)
            line = self.line(session, line_id)
            take["audio_id"] = self.audio.register(
                path, f"#{line['index']} · Take {take['take_index']}"
            )["id"]
            line["takes"].append(take)
            if (
                line["revision"] == revision
                and line["selection_revision"] == selection_revision
            ):
                line["current_take_id"] = take["id"]
            return self.save(session)

    def cleanup(self, session_ids, line_id=None):
        with self.store.lock:
            self.available(session_ids)
            result = {"deleted": 0, "bytes": 0, "failures": []}
            # Protect any selected resource even if bad imported data shares a file.
            protected = {
                self.store.get("audio", audio_id)["path"]
                for audio_id in self.audio.referenced()
            }
            for key in session_ids:
                session = self.store.get("sessions", key)
                lines = [self.line(session, line_id)] if line_id else session["lines"]
                for line in lines:
                    keep = []
                    allowed = self.store.path(
                        f"projects/{session['project_id']}/sessions/{key}/takes/{line['id']}"
                    )
                    for take in line["takes"]:
                        if take["id"] == line["current_take_id"]:
                            keep.append(take)
                            continue
                        try:
                            size = 0
                            if take.get("audio_id"):
                                resource = self.store.get("audio", take["audio_id"])
                                path = self.store.path(resource["path"])
                                if resource[
                                    "path"
                                ] in protected or not path.is_relative_to(allowed):
                                    raise ValueError(
                                        "资源仍被使用或不属于该句 Take 目录"
                                    )
                                size = path.stat().st_size if path.exists() else 0
                                path.unlink(missing_ok=True)
                                self.store.delete("audio", take["audio_id"])
                            result["deleted"] += 1
                            result["bytes"] += size
                        except (OSError, ValueError, KeyError) as error:
                            keep.append(take)
                            result["failures"].append(
                                {
                                    "session_id": key,
                                    "index": line["index"],
                                    "take_id": take["id"],
                                    "error": str(error),
                                }
                            )
                    line["takes"] = keep
                self.save(session)
            return result
