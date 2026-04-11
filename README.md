# PodBot

Turn any article, document, or webpage into a multi-host podcast — complete with audio.

PodBot uses an AI agent to iteratively write, critique, and refine a two-host dialogue script (ALEX & SAM), then synthesizes it to MP3 using text-to-speech. A React frontend lets you play and download the result.

---

## Prerequisites

Before running, make sure you have:

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Conda** (recommended) or pip — for managing the Python environment
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **ffmpeg** — required by the audio stitching library

Install ffmpeg via conda (recommended):
```bash
conda install -c conda-forge ffmpeg
```
Or verify it's already available:
```bash
ffmpeg -version
```

---

## 1. Clone / open the project

```bash
cd "C:/Users/Elise/Desktop/Personal Coding Projects/PodBot"
```

---

## 2. Set up API keys

Create a file at `backend/.env`:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

- **OpenAI key** — [platform.openai.com/api-keys](https://platform.openai.com/api-keys) — used for GPT-4o (script writing) and TTS (audio)
- **Anthropic key** — [console.anthropic.com](https://console.anthropic.com/) — used for Claude Sonnet 4.6 (optional alternative LLM)

> The Anthropic key is only required if you select Claude as the LLM provider in the UI.

---

## 3. Install backend dependencies

Activate your conda environment (or use any Python 3.10+ environment), then:

```bash
cd backend
pip install -r requirements.txt
```

---

## 4. Install frontend dependencies

```bash
cd frontend
npm install
```

---

## 5. Run the app

You need **two terminals** running simultaneously.

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
The UI will be available at `http://localhost:5173`.

Open `http://localhost:5173` in your browser.

---

## 6. Using PodBot

1. **Set your preferences** in the left sidebar:
   - Choose LLM provider (OpenAI GPT-4o or Claude Sonnet 4.6)
   - Set max rewrites (0 = no revision loop, higher = more polished but slower)

2. **Add your source content** using one of three methods:
   - **URL** — paste a link to an article or webpage and click Load
   - **Upload File** — upload a PDF, DOCX, or TXT file
   - **Paste Text** — paste content directly into the text area

3. **Enter an episode title** in the Topic field (optional but recommended)

4. **Click Generate Podcast** and watch the progress feed as the agent works through each step

5. When complete:
   - The CD player appears — click play to listen (the disc spins!)
   - Click **View Script** to read the full ALEX/SAM dialogue
   - Download the MP3 or script text using the download buttons

---

## Project Structure

```
PodBot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── requirements.txt
│   ├── .env                 # Your API keys (not committed)
│   ├── agent/               # LangGraph pipeline
│   │   ├── state.py
│   │   ├── prompts.py
│   │   ├── llm_factory.py
│   │   ├── nodes.py
│   │   └── graph.py
│   ├── ingestion/           # URL scraping + document parsing
│   │   ├── scraper.py
│   │   └── parser.py
│   └── tts/                 # Text-to-speech
│       ├── base.py          # TTSProvider interface
│       ├── openai_tts.py
│       ├── elevenlabs_tts.py  # Stub — ready for future use
│       └── stitcher.py
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── components/
    │       ├── InputPanel.jsx
    │       ├── SettingsPanel.jsx
    │       ├── ProgressFeed.jsx
    │       ├── CDPlayer.jsx
    │       ├── ScriptViewer.jsx
    │       └── DownloadButtons.jsx
    └── public/
        └── cd.svg
```

---

## Troubleshooting

**`ffmpeg not found` error**
Install ffmpeg and make sure it's on your PATH:
```bash
conda install -c conda-forge ffmpeg
```

**`OPENAI_API_KEY not set` error**
Make sure `backend/.env` exists and contains your key. The `.env` file must be in the `backend/` folder, not the project root.

**Frontend shows blank page or can't connect**
Make sure the backend is running on port 8000 before opening the frontend. Check the terminal for errors.

**URL scraping returns no content**
Some sites block scrapers or use JavaScript rendering. Try pasting the article text directly using the Paste Text tab instead.

**Generation takes a long time**
Audio generation is the slowest step — each line of dialogue is synthesized individually. A 15-minute episode (~100 dialogue lines) can take 3-5 minutes to generate audio. This is expected.
