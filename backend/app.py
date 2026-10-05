from contextlib import asynccontextmanager
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .audio import Audio
from .config import DATA, ROOT
from .engine import Engine
from .generation import Generation
from .library import Library
from .routes import build_router
from .sessions import Sessions
from .storage import Store
from .tasks import Busy, Tasks


def services(data, engine):
    store = Store(data)
    tasks = Tasks(store)
    audio = Audio(store, tasks)
    library = Library(store, audio)
    sessions = Sessions(store, tasks, audio, library)
    generation = Generation(store, tasks, audio, sessions, engine)
    return SimpleNamespace(
        store=store,
        tasks=tasks,
        audio=audio,
        engine=engine,
        library=library,
        sessions=sessions,
        generation=generation,
    )


def create_app(data=DATA, engine=None):
    state = services(data, engine or Engine())

    @asynccontextmanager
    async def lifespan(app):
        yield
        state.tasks.close()
        if state.engine.status()["state"] == "loaded":
            state.engine.unload()

    app = FastAPI(title="IndexTTS WebUI", lifespan=lifespan)
    app.state.store, app.state.services = state.store, state

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        status = 409 if isinstance(error, Busy) else 400
        return JSONResponse(status_code=status, content={"detail": str(error)})

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse(status_code=404, content={"detail": str(error.args[0] if error.args else error)})

    app.include_router(build_router(state))
    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
