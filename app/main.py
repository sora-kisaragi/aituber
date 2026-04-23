from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import commentaries, events, plans, progress, settings, subtitles, tts, videos
from app.config.config import settings as app_settings

app = FastAPI(title="AITuber", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router, prefix="/videos", tags=["videos"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(commentaries.router, prefix="/commentaries", tags=["commentaries"])
app.include_router(tts.router, prefix="/tts", tags=["tts"])
app.include_router(subtitles.router, prefix="/subtitles", tags=["subtitles"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(progress.router, prefix="/videos", tags=["progress"])

app.mount("/media", StaticFiles(directory=app_settings.media_root, check_dir=False), name="media")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
