# PodBot — Design Document

## Overview

PodBot converts a URL, uploaded document, or pasted text into a multi-host podcast audio file. A LangGraph agent iteratively writes, critiques, and refines a dialogue-format script, which is then synthesized to audio via TTS and served through a React frontend with a FastAPI backend.

---

## Tech Stack & Rationale

| Technology | Why chosen |
|---|---|
| **LangGraph** | Already in use; clean cyclic graph model for the draft→critique→revise loop |
| **OpenAI GPT-4o** | Existing API key; strong at structured dialogue writing |
| **Claude Sonnet 4.6** (`langchain-anthropic`) | Better long-form instruction following; offered as user-selectable alternative |
| **OpenAI TTS** (`tts-1`) | Same API key, zero extra setup; sufficient for prototype. ALEX=`alloy` voice, SAM=`echo` voice |
| **`TTSProvider` ABC** | Interface abstraction so ElevenLabs can be swapped in by implementing one class — no changes elsewhere |
| **FastAPI** | Lightweight Python backend; native async streaming support for SSE progress updates; serves the MP3 as a file response |
| **React** | Full control over the `<audio>` element's `onPlay`/`onPause` events, enabling the spinning CD animation to be cleanly tied to playback state via component state |
| **`requests` + `BeautifulSoup4`** | Already installed in conda env; sufficient for article/blog/doc URL scraping |
| **`pypdf`** | Pure-Python PDF extraction, no system dependencies |
| **`python-docx`** | Standard DOCX parser |
| **`pydub` + `ffmpeg`** | Clean API for stitching per-line TTS MP3 segments into one audio file |

> **Why React + FastAPI over Streamlit:** The spinning CD animation requires listening to `<audio>` element play/pause events and toggling a CSS animation in response. Streamlit renders `st.audio()` and custom HTML components in separate iframes, making cross-component event communication impossible without hacks. React gives direct access to the DOM audio element via a `ref`, making the animation a clean one-liner.

---

## File Structure

```
PodBot/
├── DESIGN.md
├── .env                            # API keys (not committed to git)
│
├── backend/
│   ├── main.py                     # FastAPI app — routes and SSE streaming
│   ├── requirements.txt
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py                # PodcastState TypedDict
│   │   ├── nodes.py                # LangGraph node functions
│   │   ├── prompts.py              # All prompt strings
│   │   ├── graph.py                # build_graph(llm) → CompiledStateGraph
│   │   └── llm_factory.py          # get_llm(provider) → BaseChatModel
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── scraper.py              # scrape_url(url) → str
│   │   └── parser.py               # parse_uploaded_file(filename, bytes) → str
│   │
│   └── tts/
│       ├── __init__.py
│       ├── base.py                 # TTSProvider ABC + DialogueLine dataclass
│       ├── openai_tts.py           # OpenAITTSProvider
│       ├── elevenlabs_tts.py       # ElevenLabsTTSProvider stub (future)
│       └── stitcher.py             # parse_script() + generate_audio()
│
└── frontend/
    ├── package.json
    ├── public/
    │   └── cd.svg                  # CD disc SVG placeholder (swappable)
    └── src/
        ├── App.jsx                 # Root component, routing
        ├── components/
        │   ├── InputPanel.jsx      # URL / file upload / paste text tabs
        │   ├── SettingsPanel.jsx   # LLM selector, max rewrites slider
        │   ├── GenerateButton.jsx
        │   ├── ProgressFeed.jsx    # SSE-driven node-by-node status list
        │   ├── CDPlayer.jsx        # Spinning CD + audio controls
        │   ├── ScriptViewer.jsx    # Collapsible script display
        │   └── DownloadButtons.jsx # MP3 + script download
        └── api.js                  # Fetch wrappers for all backend calls
```

---

## LangGraph State (`backend/agent/state.py`)

```python
class PodcastState(TypedDict):
    original_prompt: str     # Topic label from user
    source_content: str      # Ingested text (URL/file/paste) — set before graph runs
    research_content: str    # Supplementary notes added during revision
    outline: str             # Episode structure
    draft: str               # Current ALEX:/SAM: formatted script
    critique: str            # Latest critique
    rewrites: int            # Loop counter (starts at 0)
    max_rewrites: int        # User-set ceiling
    final_script: str        # Approved script (set by finalize node)
    audio_path: str          # Optional local file path
```

Removed unused stubs from the notebook: `context_db`, `critique_db`, `critique_method`, `memory`.

---

## Agent Graph Flow (`backend/agent/graph.py`)

```
source_content (pre-ingested)
        │
        ▼
create_outline → create_draft → [should_continue]
                      ↑               │              │
                      │         rewrites < max   rewrites >= max
                      │               │              │
                 revise_draft ← critique_draft     finalize → END
```

- `should_continue` is a conditional edge returning `"critique"` or `"finalize"`
- LLM is injected via `functools.partial` so nodes remain pure functions
- `InMemorySaver` checkpointer (same as notebook)
- `graph.stream(stream_mode="updates")` is consumed by the FastAPI SSE endpoint

### Node changes from existing notebook

| Notebook node | New node | Change |
|---|---|---|
| `research()` | **Removed** | Replaced by ingestion pipeline that runs *before* the graph |
| `create_draft()` | `create_draft()` | Prompt updated to enforce `ALEX:` / `SAM:` dialogue format |
| `critique()` | `critique_draft()` | Renamed for clarity |
| `research_more()` | `revise_draft()` | Uses critique to rewrite directly; no fake web search |
| `should_continue()` | `should_continue()` | Fixed: `rewrites` starts at 0; routes to `"finalize"` node |

---

## LLM Factory (`backend/agent/llm_factory.py`)

```python
def get_llm(provider: str, temperature: float = 0.7) -> BaseChatModel:
    if provider == "openai":
        return ChatOpenAI(model="gpt-4o", temperature=temperature)
    elif provider == "anthropic":
        return ChatAnthropic(model="claude-sonnet-4-6", temperature=temperature)
```

---

## FastAPI Backend (`backend/main.py`)

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/generate` | Accepts JSON `{source_content, original_prompt, llm_provider, max_rewrites}`, returns `{job_id}` |
| `GET` | `/progress/{job_id}` | Server-Sent Events stream — emits `{node, status}` as each graph node completes |
| `GET` | `/audio/{job_id}` | Returns the stitched MP3 as a `FileResponse` |
| `GET` | `/script/{job_id}` | Returns the final script as plain text |
| `POST` | `/ingest/url` | Accepts `{url}`, returns `{text}` |
| `POST` | `/ingest/file` | Accepts multipart file upload, returns `{text}` |

### SSE Progress Streaming

```python
@app.get("/progress/{job_id}")
async def progress(job_id: str):
    async def event_stream():
        for event in graph.stream(state, config, stream_mode="updates"):
            node_name = list(event.keys())[0]
            yield f"data: {json.dumps({'node': node_name})}\n\n"
        yield f"data: {json.dumps({'node': 'done'})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## TTS Abstraction (`backend/tts/base.py`)

```python
class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice_id: str) -> bytes: ...
    # Returns raw MP3 bytes

    @abstractmethod
    def get_voice_for_host(self, host: Literal["ALEX", "SAM"]) -> str: ...
    # Returns provider-specific voice identifier
```

**OpenAI implementation** (`backend/tts/openai_tts.py`):
- `ALEX → "alloy"`, `SAM → "echo"`, model `tts-1`
- Upgrade to `tts-1-hd` is a one-line config change

**ElevenLabs stub** (`backend/tts/elevenlabs_tts.py`):
- Raises `NotImplementedError`; voice ID placeholders are ready to fill in
- Swapping providers requires changing one instantiation line in `main.py`

### Audio stitching (`backend/tts/stitcher.py`)

1. Regex-parse final script into `list[DialogueLine]` (ordered `ALEX`/`SAM` turns)
2. Per line: `provider.synthesize(text, voice_id)` → MP3 bytes
3. `pydub.AudioSegment` concat with 400ms silence gaps between turns
4. `combined.export(io.BytesIO(), format="mp3")` → final MP3 bytes (no temp files)

---

## Ingestion Layer

### URL scraping (`backend/ingestion/scraper.py`)
- `requests.get()` with browser `User-Agent` header
- BeautifulSoup strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`
- Content priority: `<article>` → `<main>` → `<body>`
- Limitation: JavaScript-rendered SPAs won't work; `playwright` can replace `requests.get()` if needed

### Document parsing (`backend/ingestion/parser.py`)
- `parse_uploaded_file(filename, file_bytes)` dispatches by extension
- PDF → `pypdf.PdfReader`, iterate pages, join text
- DOCX → `python-docx`, iterate paragraphs, join text
- TXT → `bytes.decode("utf-8")`

---

## React Frontend

### Spinning CD Animation (`frontend/src/components/CDPlayer.jsx`)

The CD image is tied directly to the `<audio>` element via a React ref. When the audio plays, a CSS class is added that applies a `spin` keyframe animation; it is removed on pause or end.

```jsx
const audioRef = useRef(null);
const [isPlaying, setIsPlaying] = useState(false);

<img
  src="/cd.svg"
  className={isPlaying ? "cd-disc spinning" : "cd-disc"}
  alt="CD"
/>
<audio
  ref={audioRef}
  src={audioUrl}
  onPlay={() => setIsPlaying(true)}
  onPause={() => setIsPlaying(false)}
  onEnded={() => setIsPlaying(false)}
  controls
/>
```

```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.cd-disc.spinning {
  animation: spin 3s linear infinite;
}
```

The `cd.svg` asset lives in `frontend/public/` and can be swapped for any disc graphic without touching code.

### Live Progress Feed (`frontend/src/components/ProgressFeed.jsx`)

Connects to `/progress/{job_id}` via the `EventSource` API. Appends each node name to a list as it arrives, showing the agent's work in real time.

### Settings Panel (`frontend/src/components/SettingsPanel.jsx`)
- LLM dropdown: OpenAI GPT-4o / Claude Sonnet 4.6
- Max rewrites slider: 0–5

### Input Panel (`frontend/src/components/InputPanel.jsx`)
- Three tabs: URL input, File upload (PDF/DOCX/TXT), Paste text
- Calls `/ingest/url` or `/ingest/file` on submission to extract text before generation

---

## Packages to Install

**Backend**
```bash
pip install fastapi uvicorn langchain-anthropic pydub pypdf python-docx python-multipart
conda install -c conda-forge ffmpeg   # required by pydub for MP3 encode/decode
```

Already in the `podbot` conda env: `langgraph`, `langchain-openai`, `openai`, `requests`, `beautifulsoup4`, `python-dotenv`.

**Frontend**
```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install
```
No additional React libraries required — animation uses plain CSS, audio uses the native `<audio>` element, and SSE uses the browser's built-in `EventSource`.

---

## Security Fix

`env_config.py` currently hardcodes the OpenAI API key in plaintext. Replace with:

```
# .env (add to .gitignore)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Loaded via `python-dotenv` in `backend/main.py`. The `env_config.py` and `.env.txt` files should be deleted or gitignored.

---

## End-to-End Verification Checklist

1. `uvicorn backend.main:app --reload` + `npm start` — both servers start, UI loads
2. Paste a short article → Generate → SSE progress feed shows each node name as it completes
3. CD image spins when audio plays, stops when paused
4. Download MP3 → file plays in an external player
5. Download Script → text file contains the full `ALEX:`/`SAM:` dialogue
6. Switch LLM to Claude → generation completes using Anthropic API
7. Upload a PDF → text extracted, script reflects PDF content
8. Enter a URL → page scraped, script reflects that page's content
9. Set max_rewrites=0 → graph skips critique loop, goes directly to finalize
10. ElevenLabs stub → swapping `OpenAITTSProvider` for `ElevenLabsTTSProvider` in `main.py` raises `NotImplementedError` (confirms interface is wired correctly)
