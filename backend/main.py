import asyncio
import json
import os
from threading import Thread
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

load_dotenv()

from agent.graph import build_graph
from agent.llm_factory import get_llm
from agent.state import PodcastState
from ingestion.scraper import scrape_url
from ingestion.parser import parse_uploaded_file
from tts.openai_tts import OpenAITTSProvider
from tts.stitcher import generate_audio


app = FastAPI(title="PodBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store (single-user local app)
# jobs[job_id] = {
#   "status":  "running" | "complete" | "error",
#   "queue":   asyncio.Queue,   # SSE progress events
#   "script":  str | None,
#   "audio":   bytes | None,
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

        emit({"type": "done"})

    except Exception as exc:
        jobs[job_id]["status"] = "error"
        emit({"type": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Starts a podcast generation job.
    Returns a job_id to use with /progress, /audio, and /script.
    """
    job_id = str(uuid4())
    loop   = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    jobs[job_id] = {
        "status": "running",
        "queue":  queue,
        "script": None,
        "audio":  None,
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
    """Returns the stitched MP3 for a completed job."""
    if job_id not in jobs or jobs[job_id]["audio"] is None:
        raise HTTPException(status_code=404, detail="Audio not ready")
    return Response(content=jobs[job_id]["audio"], media_type="audio/mpeg")


@app.get("/script/{job_id}")
async def get_script(job_id: str):
    """Returns the final podcast script as plain text."""
    if job_id not in jobs or jobs[job_id]["script"] is None:
        raise HTTPException(status_code=404, detail="Script not ready")
    return Response(content=jobs[job_id]["script"], media_type="text/plain")


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
