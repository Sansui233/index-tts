from .storage import uid


class GenerationService:
    def __init__(self, store, audio, sessions, engine):
        self.store, self.audio, self.sessions, self.engine = (
            store,
            audio,
            sessions,
            engine,
        )

    def speech(self, request, progress):
        path = self.store.path(f"outputs/{uid()}.wav")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.engine.infer(
                self.audio.path(request.audio_id),
                request.text,
                path,
                request.generation.model_dump(),
                progress,
            )
            return self.audio.register(path)
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def generate_lines(self, session_id, jobs, progress):
        results = []
        for position, (line_id, reserved) in enumerate(jobs):
            progress(position / len(jobs), f"生成 {position + 1}/{len(jobs)}")
            take, path, revision, selection = reserved
            try:
                snapshot = take["snapshot"]
                self.engine.infer(
                    self.audio.path(snapshot["audio_id"]),
                    snapshot["text"],
                    path,
                    snapshot["generation"],
                    lambda value=None, desc="", **kw: progress(
                        (position + (value or 0)) / len(jobs), desc
                    ),
                )
                self.sessions.complete(
                    session_id, line_id, take, path, revision, selection
                )
                results.append(take["id"])
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return {"session_id": session_id, "take_ids": results}

    def merge(self, session_id, progress):
        from pydub import AudioSegment

        with self.store.lock:
            session = self.store.get("sessions", session_id)
            paths = []
            for line in session["lines"]:
                take = next(
                    (t for t in line["takes"] if t["id"] == line["current_take_id"]),
                    None,
                )
                if not take or not take.get("audio_id"):
                    raise ValueError(f"句子 #{line['index']} 没有当前音频")
                paths.append(self.audio.path(take["audio_id"]))
        if not paths:
            raise ValueError("没有句子")
        combined = AudioSegment.empty()
        for index, path in enumerate(paths):
            progress(index / len(paths), f"合并 {index + 1}/{len(paths)}")
            if index:
                combined += AudioSegment.silent(duration=session["interval"] * 1000)
            combined += AudioSegment.from_file(path)
        output = self.store.path(
            f"projects/{session['project_id']}/sessions/{session_id}/merged/{uid()}.wav"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        combined.export(output, format="wav")
        record = self.audio.register(output, session["name"] + ".wav")
        with self.store.lock:
            current = self.store.get("sessions", session_id)
            current["outputs"].append(record["id"])
            self.sessions.save(current)
        return record

    def subtitles(self, request, progress):
        output = self.store.path(f"outputs/{uid()}.srt")
        output.parent.mkdir(parents=True, exist_ok=True)
        self.engine.subtitles(
            self.audio.path(request.audio_id),
            output,
            request.model,
            request.language,
            progress,
        )
        return self.audio.register(output)
