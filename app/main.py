from fastapi import FastAPI
from app.api import videos, events, plans, commentaries, tts, subtitles

app = FastAPI(title="AITuber", version="0.1.0")

app.include_router(videos.router, prefix="/videos", tags=["videos"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(commentaries.router, prefix="/commentaries", tags=["commentaries"])
app.include_router(tts.router, prefix="/tts", tags=["tts"])
app.include_router(subtitles.router, prefix="/subtitles", tags=["subtitles"])


@app.get("/health")
def health():
    return {"status": "ok"}
