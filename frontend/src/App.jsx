import { useState } from 'react'
import SettingsPanel from './components/SettingsPanel'
import InputPanel from './components/InputPanel'
import ProgressFeed from './components/ProgressFeed'
import CDPlayer from './components/CDPlayer'
import ScriptViewer from './components/ScriptViewer'
import DownloadButtons from './components/DownloadButtons'
import { startGeneration, openProgressStream, fetchAudio, fetchScript } from './api'

function App() {
  const [settings, setSettings] = useState({ llmProvider: 'openai', maxRewrites: 2 })
  const [sourceContent, setSourceContent] = useState('')
  const [originalPrompt, setOriginalPrompt] = useState('')
  const [sourceMeta, setSourceMeta] = useState({ source_url: null, source_filename: null })
  const [isGenerating, setIsGenerating] = useState(false)
  const [progressNodes, setProgressNodes] = useState([])
  const [audioUrl, setAudioUrl] = useState(null)
  const [audioBlob, setAudioBlob] = useState(null)
  const [scriptText, setScriptText] = useState('')
  const [error, setError] = useState(null)
  const [isDone, setIsDone] = useState(false)
  const [shareJobId, setShareJobId] = useState(null)
  const [copied, setCopied] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    setProgressNodes([])
    setAudioUrl(null)
    setAudioBlob(null)
    setScriptText('')
    setError(null)
    setIsDone(false)
    setShareJobId(null)
    setCopied(false)

    try {
      // 1. Start the job on the backend
      const { job_id } = await startGeneration({
        sourceContent,
        originalPrompt,
        llmProvider: settings.llmProvider,
        maxRewrites: settings.maxRewrites,
        sourceUrl: sourceMeta.source_url,
        sourceFilename: sourceMeta.source_filename,
      })

      // 2. Stream progress events via SSE
      const es = openProgressStream(job_id)

      es.onmessage = async (e) => {
        const msg = JSON.parse(e.data)

        if (msg.type === 'progress') {
          setProgressNodes(prev => [...prev, msg.node])

        } else if (msg.type === 'done') {
          es.close()

          // 3. Fetch audio and script in parallel
          const [blob, script] = await Promise.all([
            fetchAudio(job_id),
            fetchScript(job_id),
          ])

          const url = URL.createObjectURL(blob)
          setAudioBlob(blob)
          setAudioUrl(url)
          setScriptText(script)
          setShareJobId(job_id)
          setIsDone(true)
          setIsGenerating(false)

        } else if (msg.type === 'error') {
          es.close()
          setError(msg.message)
          setIsGenerating(false)
        }
      }

      es.onerror = () => {
        es.close()
        setError('Connection to server lost. Please try again.')
        setIsGenerating(false)
      }

    } catch (err) {
      setError(err.message)
      setIsGenerating(false)
    }
  }

  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">🎙</span>
          <span className="logo-text">PodBot</span>
        </div>
        <SettingsPanel
          settings={settings}
          onChange={setSettings}
          disabled={isGenerating}
        />
      </aside>

      {/* ── Main content ── */}
      <main className="main">
        <InputPanel
          sourceContent={sourceContent}
          onSourceContent={setSourceContent}
          originalPrompt={originalPrompt}
          onOriginalPrompt={setOriginalPrompt}
          onSourceMeta={setSourceMeta}
          disabled={isGenerating}
        />

        <button
          className="generate-btn"
          onClick={handleGenerate}
          disabled={!sourceContent.trim() || isGenerating}
        >
          {isGenerating ? 'Generating…' : 'Generate Podcast'}
        </button>

        {error && (
          <div className="error-banner">{error}</div>
        )}

        {(isGenerating || progressNodes.length > 0) && (
          <ProgressFeed nodes={progressNodes} isGenerating={isGenerating} />
        )}

        {isDone && (
          <div className="output-section">
            <CDPlayer audioUrl={audioUrl} />

            {shareJobId && (
              <div className="share-bar">
                <span className="share-bar-label">Share this podcast</span>
                <div className="share-bar-row">
                  <input
                    readOnly
                    className="share-input"
                    value={`${window.location.origin}/share/${shareJobId}`}
                    onFocus={e => e.target.select()}
                  />
                  <button
                    className="share-copy-btn"
                    onClick={() => {
                      navigator.clipboard.writeText(`${window.location.origin}/share/${shareJobId}`)
                      setCopied(true)
                      setTimeout(() => setCopied(false), 2000)
                    }}
                  >
                    {copied ? 'Copied!' : 'Copy Link'}
                  </button>
                </div>
              </div>
            )}

            <ScriptViewer script={scriptText} />
            <DownloadButtons audioBlob={audioBlob} scriptText={scriptText} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
