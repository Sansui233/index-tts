from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .config import DATA, ROOT
from .storage import Store
from .tasks import Tasks
from .audio import Audio
from .engine import Engine
from .sessions import Sessions, Busy
from .generation import GenerationService
from .routes import resource_routes
from .session_routes import session_routes


def create_app(data=DATA, engine=None):
    store = Store(data)
    tasks = Tasks(store)
    audio = Audio(store)
    engine = engine or Engine()
    sessions = Sessions(store, tasks, audio)
    generation = GenerationService(store, audio, sessions, engine)

    @asynccontextmanager
    async def lifespan(app):
        yield
        tasks.close()
        if engine.status()["state"] == "loaded":
            engine.unload()

    app = FastAPI(title="IndexTTS WebUI3", lifespan=lifespan)
    app.state.store, app.state.tasks, app.state.sessions = store, tasks, sessions

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse(
            status_code=409 if isinstance(error, Busy) else 400,
            content={"detail": str(error)},
        )

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    resources, validate = resource_routes(store, audio, tasks, engine, generation)
    app.include_router(resources)
    app.include_router(session_routes(store, sessions, tasks, generation, validate))
    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app
