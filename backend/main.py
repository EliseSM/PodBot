import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Thread
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse, PlainTextResponse
from pydantic import BaseModel

load_dotenv()

from agent.graph import build_graph
from agent.llm_factory import get_llm
from agent.state import PodcastState
from database import init_db, save_podcast, get_podcast, list_podcasts
from ingestion.scraper import scrape_url
from ingestion.parser import parse_uploaded_file
from tts.openai_tts import OpenAITTSProvider
from tts.stitcher import generate_audio

# Directory where generated MP3s are saved for persistent sharing
AUDIO_DIR = Path(__file__).parent / "podcasts" / "audio"


# ---------------------------------------------------------------------------
# App lifespan — initialise DB on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="PodBot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store (single-user local app)
# jobs[job_id] = {
#   "status":          "running" | "complete" | "error",
#   "queue":           asyncio.Queue,   # SSE progress events
#   "script":          str | None,
#   "audio":           bytes | None,
#   "title":           str,
#   "source_url":      str | None,
#   "source_filename": str | None,
#   "llm_provider":    str,
# }
# ---------------------------------------------------------------------------
jobs: dict = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    source_content: str
    original_prompt: str = "Podcast Episode"
    llm_provider: str = "openai"
    max_rewrites: int = 2
    source_url: str | None = None
    source_filename: str | None = None


class IngestUrlRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Background pipeline (runs in a daemon thread)
# ---------------------------------------------------------------------------

def run_pipeline(job_id: str, request: GenerateRequest, loop: asyncio.AbstractEventLoop) -> None:
    """
    Runs the full podcast generation pipeline in a background thread.

    Progress events are posted to the job's asyncio.Queue via
    loop.call_soon_threadsafe so the SSE endpoint can stream them safely.
    On completion, the MP3 is written to disk and the podcast is saved to the DB.
    """
    def emit(event: dict) -> None:
        loop.call_soon_threadsafe(jobs[job_id]["queue"].put_nowait, event)

    try:
        llm   = get_llm(request.llm_provider)
        graph = build_graph(llm)

        initial_state: PodcastState = {
            "original_prompt":  request.original_prompt,
            "source_content":   request.source_content,
            "research_content": "",
            "outline":          "",
            "draft":            "",
            "critique":         "",
            "rewrites":         0,
            "max_rewrites":     request.max_rewrites,
            "final_script":     "",
            "audio_path":       "",
        }

        config = {"configurable": {"thread_id": job_id}}

        # Stream graph execution — each chunk is {node_name: state_update}
        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            node_name = list(chunk.keys())[0]
            emit({"type": "progress", "node": node_name})

        # Retrieve final state from checkpointer
        final_state = graph.get_state(config).values
        final_script = final_state["final_script"]
        jobs[job_id]["script"] = final_script

        # Generate audio
        emit({"type": "progress", "node": "generating_audio"})
        tts = OpenAITTSProvider(api_key=os.environ["OPENAI_API_KEY"])
        audio_bytes = generate_audio(final_script, tts)
        jobs[job_id]["audio"] = audio_bytes
        jobs[job_id]["status"] = "complete"

        # Persist audio to disk
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        audio_path = AUDIO_DIR / f"{job_id}.mp3"
        audio_path.write_bytes(audio_bytes)

        # Persist metadata to DB (fire-and-forget from the thread)
        asyncio.run_coroutine_threadsafe(
            save_podcast(
                id=job_id,
                title=jobs[job_id]["title"],
                source_url=jobs[job_id].get("source_url"),
                source_filename=jobs[job_id].get("source_filename"),
                llm_provider=jobs[job_id]["llm_provider"],
                audio_path=str(audio_path),
                final_script=final_script,
            ),
            loop,
        )

        emit({"type": "done"})

    except Exception as exc:
        jobs[job_id]["status"] = "error"
        emit({"type": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Generation endpoints
# ---------------------------------------------------------------------------

@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Starts a podcast generation job.
    Returns a job_id to use with /progress, /audio, /script, and /share.
    """
    job_id = str(uuid4())
    loop   = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    jobs[job_id] = {
        "status":          "running",
        "queue":           queue,
        "script":          None,
        "audio":           None,
        "title":           request.original_prompt,
        "source_url":      request.source_url,
        "source_filename": request.source_filename,
        "llm_provider":    request.llm_provider,
    }

    thread = Thread(target=run_pipeline, args=(job_id, request, loop), daemon=True)
    thread.start()

    return {"job_id": job_id}


@app.get("/progress/{job_id}")
async def progress(job_id: str):
    """
    Server-Sent Events stream for generation progress.
    Emits {"type": "progress", "node": "<node_name>"} as each graph node completes.
    Emits {"type": "done"} or {"type": "error", "message": "..."} at the end.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue = jobs[job_id]["queue"]

    async def event_stream():
        while True:
            msg = await queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] in ("done", "error"):
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/audio/{job_id}")
async def get_audio(job_id: str):
    """Returns the stitched MP3 for a completed job (fast in-memory path)."""
    if job_id not in jobs or jobs[job_id]["audio"] is None:
        raise HTTPException(status_code=404, detail="Audio not ready")
    return Response(content=jobs[job_id]["audio"], media_type="audio/mpeg")


@app.get("/script/{job_id}")
async def get_script(job_id: str):
    """Returns the final podcast script as plain text."""
    if job_id not in jobs or jobs[job_id]["script"] is None:
        raise HTTPException(status_code=404, detail="Script not ready")
    return Response(content=jobs[job_id]["script"], media_type="text/plain")


# ---------------------------------------------------------------------------
# Ingest endpoints
# ---------------------------------------------------------------------------

@app.post("/ingest/url")
async def ingest_url(request: IngestUrlRequest):
    """Scrapes a URL and returns its readable text content."""
    try:
        text = scrape_url(request.url)
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Parses an uploaded PDF, DOCX, or TXT file and returns its text."""
    try:
        content = await file.read()
        text = parse_uploaded_file(file.filename, content)
        return {"text": text}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Library endpoint
# ---------------------------------------------------------------------------

@app.get("/library")
async def get_library():
    """Returns all saved podcasts ordered newest first."""
    podcasts = await list_podcasts()
    return {"podcasts": podcasts}


# ---------------------------------------------------------------------------
# Share endpoints (persistent — work after server restart)
# ---------------------------------------------------------------------------

@app.get("/share/{podcast_id}")
async def get_share_metadata(podcast_id: str):
    """Returns metadata for a shared podcast page."""
    podcast = await get_podcast(podcast_id)
    if podcast is None:
        raise HTTPException(status_code=404, detail="Podcast not found")
    # Return only public-facing fields (exclude internal audio_path)
    return {
        "id":              podcast["id"],
        "title":           podcast["title"],
        "source_url":      podcast["source_url"],
        "source_filename": podcast["source_filename"],
        "llm_provider":    podcast["llm_provider"],
        "created_at":      podcast["created_at"],
    }


@app.get("/share/{podcast_id}/audio")
async def get_share_audio(podcast_id: str):
    """Streams the MP3 for a shared podcast."""
    podcast = await get_podcast(podcast_id)
    if podcast is None:
        raise HTTPException(status_code=404, detail="Podcast not found")
    audio_path = Path(podcast["audio_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{podcast['title']}.mp3",
    )


@app.get("/share/{podcast_id}/download/script")
async def get_share_script(podcast_id: str):
    """Returns the podcast script as a downloadable plain text file."""
    podcast = await get_podcast(podcast_id)
    if podcast is None:
        raise HTTPException(status_code=404, detail="Podcast not found")
    if not podcast.get("final_script"):
        raise HTTPException(status_code=404, detail="Script not available")
    filename = f"{podcast['title']}.txt"
    return PlainTextResponse(
        content=podcast["final_script"],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
