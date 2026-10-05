"""Resource CRUD, uploads and model/task controls."""

from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from . import schemas as S
from .config import AUDIO_EXTENSIONS, ROOT
from .storage import uid


def resource_routes(store, audio, tasks, engine, generation):
    api = APIRouter(prefix="/api")

    @api.get("/health")
    def health():
        return {"status": "ok", "data_dir": str(store.root)}

    @api.get("/settings")
    def settings():
        return {
            "generation": S.Generation().model_dump(),
            "data_dir": str(store.root),
            "subtitle_models": [
                m
                for m in ("tiny", "base", "small", "medium")
                if (ROOT / f"checkpoints/whisper/whisper-{m}/config.json").exists()
            ],
        }

    @api.get("/models")
    def models():
        return engine.status()

    @api.post("/models/load", status_code=202)
    def load():
        return tasks.submit("model-load", engine.load)

    @api.post("/models/unload", status_code=202)
    def unload():
        return tasks.submit("model-unload", engine.unload)

    @api.get("/tasks")
    def list_tasks():
        return sorted(store.list("tasks"), key=lambda t: t["created_at"], reverse=True)[
            :100
        ]

    @api.get("/tasks/{key}")
    def get_task(key: str):
        return store.get("tasks", key)

    @api.post("/tasks/{key}/cancel")
    def cancel(key: str):
        return tasks.cancel(key)

    @api.post("/speech", status_code=202)
    def speech(request: S.Speech):
        audio.path(request.audio_id)
        return tasks.submit(
            "speech",
            lambda p: generation.speech(request, p),
            audio_ids=[request.audio_id],
        )

    @api.post("/subtitles", status_code=202)
    def subtitles(request: S.Subtitle):
        audio.path(request.audio_id)
        return tasks.submit(
            "subtitles",
            lambda p: generation.subtitles(request, p),
            audio_ids=[request.audio_id],
        )

    @api.get("/audio")
    def list_audio():
        return sorted(store.list("audio"), key=lambda r: r["created_at"], reverse=True)

    @api.get("/audio/sources")
    def sources():
        return audio.sources()

    @api.post("/audio/import")
    def import_source(request: S.Source):
        return audio.import_source(request.path)

    @api.post("/audio/upload")
    def upload(file: UploadFile = File(...)):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            raise ValueError("不支持的音频类型")
        path = store.path(f"audio/files/{uid()}{suffix}")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            size = 0
            with path.open("wb") as target:
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 500 * 1024 * 1024:
                        raise ValueError("音频不能超过 500 MB")
                    target.write(chunk)
            if not size:
                raise ValueError("空文件")
            return audio.register(path, Path(file.filename).name)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()

    @api.get("/audio/{key}/file")
    def file(key: str, download: bool = False):
        record = store.get("audio", key)
        path = audio.path(key)
        return FileResponse(path, filename=record["name"] if download else None)

    @api.patch("/audio/{key}")
    def rename_audio(key: str, request: S.Named):
        with store.lock:
            record = store.get("audio", key)
            record["name"] = request.name
            return store.save("audio", record)

    def validate_bindings(bindings):
        names = [b.speaker for b in bindings]
        if len(names) != len(set(names)):
            raise ValueError("说话人名称不能重复")
        for binding in bindings:
            if binding.role_id:
                role = store.get("roles", binding.role_id)
                if binding.audio_id and binding.audio_id not in role["audio_ids"]:
                    raise ValueError("参考音频不属于所选角色")
            if binding.audio_id:
                audio.path(binding.audio_id)

    @api.get("/roles")
    def roles():
        return store.list("roles")

    @api.post("/roles")
    def create_role(request: S.Role):
        with store.lock:
            for key in request.audio_ids:
                audio.path(key)
            return store.create("roles", request.model_dump())

    @api.put("/roles/{key}")
    def update_role(key: str, request: S.Role):
        with store.lock:
            record = store.get("roles", key)
            for audio_id in request.audio_ids:
                audio.path(audio_id)
            removed = set(record["audio_ids"]) - set(request.audio_ids)
            for entry in store.list("sessions") + store.list("presets"):
                if any(
                    b.get("role_id") == key and b.get("audio_id") in removed
                    for b in entry["bindings"]
                ):
                    raise ValueError("音频仍被 session 或预设引用，请先更换绑定")
            record.update(request.model_dump())
            return store.save("roles", record)

    @api.delete("/roles/{key}")
    def delete_role(key: str):
        with store.lock:
            for entry in store.list("sessions") + store.list("presets"):
                if any(b.get("role_id") == key for b in entry["bindings"]):
                    raise ValueError("角色仍被 session 或预设引用")
            store.delete("roles", key)
            return {"deleted": True}

    @api.get("/presets")
    def presets():
        return store.list("presets")

    @api.get("/presets/{key}")
    def preset(key: str):
        return store.get("presets", key)

    @api.post("/presets")
    def create_preset(request: S.Preset):
        with store.lock:
            validate_bindings(request.bindings)
            return store.create("presets", request.model_dump())

    @api.put("/presets/{key}")
    def update_preset(key: str, request: S.Preset):
        with store.lock:
            validate_bindings(request.bindings)
            record = store.get("presets", key)
            record.update(request.model_dump())
            return store.save("presets", record)

    return api, validate_bindings
