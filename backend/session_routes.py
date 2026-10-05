import shutil
from fastapi import APIRouter
from . import schemas as S


def session_routes(store, sessions, tasks, generation, validate_bindings):
    api = APIRouter(prefix="/api")

    @api.get("/projects")
    def projects():
        return store.list("projects")

    @api.post("/projects")
    def create_project(request: S.Named):
        return store.create("projects", request.model_dump())

    @api.put("/projects/{key}")
    def update_project(key: str, request: S.Named):
        with store.lock:
            record = store.get("projects", key)
            record.update(request.model_dump())
            return store.save("projects", record)

    def delete_session(key):
        sessions.available([key])
        record = store.get("sessions", key)
        folder = store.path(f"projects/{record['project_id']}/sessions/{key}")
        referenced = sessions.audio.referenced(exclude_session=key)
        for resource in store.list("audio"):
            if resource["id"] in referenced and store.path(
                resource["path"]
            ).is_relative_to(folder):
                raise ValueError(
                    "session 音频仍被其他角色、session 或任务引用，请先解除引用"
                )
        for resource in store.list("audio"):
            if store.path(resource["path"]).is_relative_to(folder):
                store.delete("audio", resource["id"])
        if folder.exists():
            shutil.rmtree(folder)
        store.delete("sessions", key)

    @api.delete("/projects/{key}")
    def delete_project(key: str):
        with store.lock:
            store.get("projects", key)
            records = [s for s in store.list("sessions") if s["project_id"] == key]
            sessions.available([s["id"] for s in records])
            for record in records:
                delete_session(record["id"])
            store.delete("projects", key)
            return {"deleted": True}

    @api.get("/sessions")
    def list_sessions(project_id: str | None = None, sort: str = "updated_at"):
        if sort not in {"name", "updated_at", "created_at"}:
            raise ValueError("不支持的排序")
        records = [
            s
            for s in store.list("sessions")
            if project_id is None or s["project_id"] == project_id
        ]
        return sorted(
            [
                {k: v for k, v in s.items() if k not in {"lines", "text"}}
                | {"line_count": len(s["lines"])}
                for s in records
            ],
            key=lambda s: s[sort],
            reverse=sort != "name",
        )

    @api.post("/sessions")
    def create_session(request: S.SessionInput):
        with store.lock:
            validate_bindings(request.bindings)
            return sessions.save(sessions.create(request.model_dump()))

    @api.get("/sessions/{key}")
    def get_session(key: str):
        return store.get("sessions", key)

    @api.put("/sessions/{key}")
    def update_session(key: str, request: S.SessionInput):
        with store.lock:
            sessions.available([key])
            validate_bindings(request.bindings)
            store.get("projects", request.project_id)
            record = store.get("sessions", key)
            if record["project_id"] != request.project_id:
                source = store.path(f"projects/{record['project_id']}/sessions/{key}")
                target = store.path(f"projects/{request.project_id}/sessions/{key}")
                if source.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        raise ValueError("目标 session 目录已存在")
                    source.rename(target)
                    for resource in store.list("audio"):
                        old = store.path(resource["path"])
                        if old.is_relative_to(source):
                            resource["path"] = (
                                (target / old.relative_to(source))
                                .relative_to(store.root)
                                .as_posix()
                            )
                            store.save("audio", resource)
            record.update(request.model_dump())
            return sessions.save(record)

    @api.delete("/sessions/{key}")
    def remove_session(key: str):
        with store.lock:
            delete_session(key)
            return {"deleted": True}

    @api.put("/sessions/{key}/text")
    def text(key: str, request: S.TextInput):
        return sessions.replace_text(key, request.text)

    @api.post("/sessions/{key}/lines")
    def add_line(key: str, request: S.LineInput):
        with store.lock:
            sessions.available([key])
            record = store.get("sessions", key)
            sessions.add_line(record, request.model_dump())
            return sessions.save(record)

    @api.put("/sessions/{key}/lines/{line_id}")
    def update_line(key: str, line_id: str, request: S.LineInput):
        with store.lock:
            record = store.get("sessions", key)
            line = sessions.line(record, line_id)
            line.update(request.model_dump())
            line["revision"] += 1
            return sessions.save(record)

    @api.delete("/sessions/{key}/lines/{line_id}")
    def delete_line(key: str, line_id: str):
        with store.lock:
            sessions.available([key])
            record = store.get("sessions", key)
            line = sessions.line(record, line_id)
            # Treat all takes as unused after deleting a sentence, retaining record on failure.
            line["current_take_id"] = None
            sessions.save(record)
            result = sessions.cleanup([key], line_id)
            if result["failures"]:
                raise ValueError("部分 Take 删除失败，请重试清理后再删除句子")
            record = store.get("sessions", key)
            record["lines"] = [
                item for item in record["lines"] if item["id"] != line_id
            ]
            return sessions.save(record)

    @api.put("/sessions/{key}/order")
    def order(key: str, request: S.Order):
        with store.lock:
            sessions.available([key])
            record = store.get("sessions", key)
            if len(request.line_ids) != len(record["lines"]) or set(
                request.line_ids
            ) != {item["id"] for item in record["lines"]}:
                raise ValueError("排序必须包含所有句子且不重复")
            record["lines"] = [sessions.line(record, i) for i in request.line_ids]
            return sessions.save(record)

    @api.get("/sessions/{key}/lines/{line_id}/takes")
    def takes(key: str, line_id: str):
        line = sessions.line(store.get("sessions", key), line_id)
        return {
            "index": line["index"],
            "current_take_id": line["current_take_id"],
            "takes": line["takes"],
        }

    @api.put("/sessions/{key}/lines/{line_id}/current-take")
    def select(key: str, line_id: str, request: S.Selection):
        return sessions.select(key, line_id, request.take_id)

    def generate(key, line_id=None):
        with store.lock:
            record = store.get("sessions", key)
            lines = [sessions.line(record, line_id)] if line_id else record["lines"]
            if not lines:
                raise ValueError("没有句子")
            for line in lines:
                sessions.snapshot(record, line)
            jobs = [(line["id"], sessions.reserve(key, line["id"])) for line in lines]
            return tasks.submit(
                "session-generate",
                lambda p: generation.generate_lines(key, jobs, p),
                [key],
                [reserved[0]["snapshot"]["audio_id"] for _, reserved in jobs],
            )

    @api.post("/sessions/{key}/generate", status_code=202)
    def generate_all(key: str):
        return generate(key)

    @api.post("/sessions/{key}/lines/{line_id}/generate", status_code=202)
    def regenerate(key: str, line_id: str):
        return generate(key, line_id)

    @api.post("/sessions/{key}/merge", status_code=202)
    def merge(key: str):
        with store.lock:
            store.get("sessions", key)
            return tasks.submit("merge", lambda p: generation.merge(key, p), [key])

    @api.post("/sessions/{key}/lines/{line_id}/takes/cleanup")
    def clean_line(key: str, line_id: str):
        return sessions.cleanup([key], line_id)

    @api.post("/sessions/{key}/takes/cleanup")
    def clean_session(key: str):
        return sessions.cleanup([key])

    @api.post("/projects/{key}/takes/cleanup")
    def clean_project(key: str):
        with store.lock:
            store.get("projects", key)
            return sessions.cleanup(
                [s["id"] for s in store.list("sessions") if s["project_id"] == key]
            )

    return api
