"""HTTP surface. Handlers only translate requests; services hold the rules."""

from types import SimpleNamespace
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from . import schemas as S
from .engine import WHISPER_MODELS, whisper_path
from .sessions import find_line

DELETED = {"deleted": True}


def build_router(app: SimpleNamespace):
    store, audio, tasks, engine = app.store, app.audio, app.tasks, app.engine
    library, sessions, generation = app.library, app.sessions, app.generation
    api = APIRouter(prefix="/api")

    # System, model and tasks

    @api.get("/health")
    def health():
        return {"status": "ok", "data_dir": str(store.root)}

    @api.get("/settings")
    def settings():
        return {
            "generation": S.Generation().model_dump(),
            "data_dir": str(store.root),
            "subtitle_models": [
                m for m in WHISPER_MODELS if (whisper_path(m) / "config.json").exists()
            ],
        }

    @api.get("/models")
    def model_status():
        return engine.status()

    @api.post("/models/load", status_code=202)
    def load_model():
        return generation.load_model()

    @api.post("/models/unload", status_code=202)
    def unload_model():
        return generation.unload_model()

    def with_result(task):
        """Results are copies of audio records; show the current one so renames appear."""
        result = task.get("result")
        if isinstance(result, dict) and "path" in result:
            try:
                task["result"] = store.get("audio", result["id"])
            except KeyError:
                pass
        return task

    @api.get("/tasks")
    def list_tasks():
        return [with_result(t) for t in store.list("tasks", newest=True)[:100]]

    @api.get("/tasks/{key}")
    def get_task(key: str):
        return with_result(store.get("tasks", key))

    @api.post("/tasks/delete")
    def delete_tasks(request: S.Ids):
        return tasks.delete(request.ids)

    @api.post("/tasks/clear")
    def clear_tasks():
        return tasks.delete()

    @api.post("/tasks/{key}/cancel")
    def cancel_task(key: str):
        return tasks.cancel(key)

    @api.post("/speech", status_code=202)
    def speech(request: S.Speech):
        return generation.speech(request)

    @api.post("/subtitles", status_code=202)
    def subtitles(request: S.Subtitle):
        return generation.subtitles(request)

    # Audio resources

    @api.get("/audio")
    def list_audio(reference: bool = False):
        """reference=true: only uploaded/imported reference audio, not takes or outputs."""
        records = store.list("audio", newest=True)
        return [r for r in records if r["path"].startswith("audio/files/")] if reference else records

    @api.get("/audio/sources")
    def audio_sources():
        return audio.sources()

    @api.post("/audio/import")
    def import_audio(request: S.Source):
        return audio.import_source(request.path)

    @api.post("/audio/upload")
    def upload_audio(file: UploadFile = File(...)):
        with file.file:
            return audio.upload(file.file, file.filename or "")

    @api.get("/audio/{key}/file")
    def audio_file(key: str, download: bool = False):
        name = store.get("audio", key)["name"]
        return FileResponse(audio.path(key), filename=name if download else None)

    @api.get("/audio/{key}")
    def get_audio(key: str):
        return store.get("audio", key)

    @api.patch("/audio/{key}")
    def rename_audio(key: str, request: S.Named):
        return store.update("audio", key, request.model_dump())

    # Roles and presets

    @api.get("/roles")
    def list_roles():
        return store.list("roles", newest=True)

    @api.post("/roles")
    def create_role(request: S.Role):
        return library.save_role(request)

    @api.put("/roles/{key}")
    def update_role(key: str, request: S.Role):
        return library.save_role(request, key)

    @api.delete("/roles/{key}")
    def delete_role(key: str):
        library.delete_role(key)
        return DELETED

    @api.get("/presets")
    def list_presets():
        return store.list("presets", newest=True)

    @api.get("/presets/{key}")
    def get_preset(key: str):
        return store.get("presets", key)

    @api.post("/presets")
    def create_preset(request: S.Preset):
        return library.save_preset(request)

    @api.put("/presets/{key}")
    def update_preset(key: str, request: S.Preset):
        return library.save_preset(request, key)

    @api.delete("/presets/{key}")
    def delete_preset(key: str):
        store.delete("presets", key)
        return DELETED

    # Projects

    @api.get("/projects")
    def list_projects():
        return store.list("projects", newest=True)

    @api.post("/projects")
    def create_project(request: S.Named):
        return store.create("projects", request.model_dump())

    @api.put("/projects/{key}")
    def update_project(key: str, request: S.Named):
        return store.update("projects", key, request.model_dump())

    @api.delete("/projects/{key}")
    def delete_project(key: str):
        sessions.delete_project(key)
        return DELETED

    @api.post("/projects/{key}/takes/cleanup")
    def cleanup_project(key: str):
        store.get("projects", key)
        return sessions.cleanup([s["id"] for s in sessions.of_project(key)])

    # Sessions

    @api.get("/sessions")
    def list_sessions(project_id: str | None = None, sort: str = "updated_at"):
        return sessions.summaries(project_id, sort)

    @api.post("/sessions")
    def create_session(request: S.SessionInput):
        library.validate_bindings(request.bindings)
        return sessions.create(request.model_dump())

    @api.get("/sessions/{key}")
    def get_session(key: str):
        return store.get("sessions", key)

    @api.put("/sessions/{key}")
    def update_session(key: str, request: S.SessionInput):
        return sessions.update(key, request)

    @api.delete("/sessions/{key}")
    def delete_session(key: str):
        sessions.delete(key)
        return DELETED

    @api.put("/sessions/{key}/text")
    def replace_text(key: str, request: S.TextInput):
        return sessions.replace_text(key, request.text)

    @api.put("/sessions/{key}/order")
    def reorder(key: str, request: S.Order):
        return sessions.reorder(key, request.line_ids)

    @api.post("/sessions/{key}/generate", status_code=202)
    def generate_session(key: str):
        return generation.session(key)

    @api.post("/sessions/{key}/merge", status_code=202)
    def merge(key: str):
        return generation.merge(key)

    @api.post("/sessions/{key}/takes/cleanup")
    def cleanup_session(key: str):
        return sessions.cleanup([key])

    # Lines

    @api.post("/sessions/{key}/lines")
    def add_line(key: str, request: S.LineInput):
        return sessions.edit(key, lambda s: sessions.add_line(s, request.model_dump()))

    @api.put("/sessions/{key}/lines/{line_id}")
    def update_line(key: str, line_id: str, request: S.LineInput):
        return sessions.update_line(key, line_id, request.model_dump())

    @api.delete("/sessions/{key}/lines/{line_id}")
    def delete_line(key: str, line_id: str):
        return sessions.delete_line(key, line_id)

    @api.post("/sessions/{key}/lines/{line_id}/generate", status_code=202)
    def generate_line(key: str, line_id: str):
        return generation.session(key, line_id)

    @api.get("/sessions/{key}/lines/{line_id}/takes")
    def list_takes(key: str, line_id: str):
        line = find_line(store.get("sessions", key), line_id)
        return {k: line[k] for k in ("index", "current_take_id", "takes")}

    @api.put("/sessions/{key}/lines/{line_id}/current-take")
    def select_take(key: str, line_id: str, request: S.Selection):
        return sessions.select(key, line_id, request.take_id)

    @api.post("/sessions/{key}/lines/{line_id}/takes/cleanup")
    def cleanup_line(key: str, line_id: str):
        return sessions.cleanup([key], line_id)

    return api
