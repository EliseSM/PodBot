import { useState } from 'react'
import SettingsPanel from './components/SettingsPanel'
import LibraryPanel from './components/LibraryPanel'
import InputPanel from './components/InputPanel'
import ProgressFeed from './components/ProgressFeed'
import CDPlayer from './components/CDPlayer'
import ScriptViewer from './components/ScriptViewer'
import DownloadButtons from './components/DownloadButtons'
import { startGeneration, openProgressStream, fetchAudio, fetchScript } from './api'

const BASE = '/api'

function App() {
  // Sidebar navigation
  const [sidebarView, setSidebarView] = useState('generate')

  // Generation state
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

  // Library state
  const [libraryPodcast, setLibraryPodcast] = useState(null)
  const [libraryScript, setLibraryScript] = useState(null)
  const [libraryCopied, setLibraryCopied] = useState(false)

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
      const { job_id } = await startGeneration({
        sourceContent,
        originalPrompt,
        llmProvider: settings.llmProvider,
        maxRewrites: settings.maxRewrites,
        sourceUrl: sourceMeta.source_url,
        sourceFilename: sourceMeta.source_filename,
      })

      const es = openProgressStream(job_id)

      es.onmessage = async (e) => {
        const msg = JSON.parse(e.data)

        if (msg.type === 'progress') {
          setProgressNodes(prev => [...prev, msg.node])

        } else if (msg.type === 'done') {
          es.close()

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

  const handleSelectLibraryPodcast = async (podcast) => {
    setLibraryPodcast(podcast)
    setLibraryScript(null)
    setLibraryCopied(false)
    try {
      const res = await fetch(`${BASE}/share/${podcast.id}/download/script`)
      if (res.ok) setLibraryScript(await res.text())
    } catch {}
  }

  const libraryAudioUrl  = libraryPodcast ? `${BASE}/share/${libraryPodcast.id}/audio` : null
  const libraryScriptUrl = libraryPodcast ? `${BASE}/share/${libraryPodcast.id}/download/script` : null
  const libraryShareUrl  = libraryPodcast ? `${window.location.origin}/share/${libraryPodcast.id}` : null

  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">🎙</span>
          <span className="logo-text">PodBot</span>
        </div>

        <div className="sidebar-nav">
          <button
            className={`sidebar-nav-btn${sidebarView === 'generate' ? ' active' : ''}`}
            onClick={() => setSidebarView('generate')}
          >
            New Podcast
          </button>
          <button
            className={`sidebar-nav-btn${sidebarView === 'library' ? ' active' : ''}`}
            onClick={() => setSidebarView('library')}
          >
            Library
          </button>
        </div>

        {sidebarView === 'generate' && (
          <SettingsPanel
            settings={settings}
            onChange={setSettings}
            disabled={isGenerating}
          />
        )}

        {sidebarView === 'library' && (
          <LibraryPanel
            selected={libraryPodcast}
            onSelect={handleSelectLibraryPodcast}
          />
        )}
      </aside>

      {/* ── Main content: Generate view ── */}
      {sidebarView === 'generate' && (
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
      )}

      {/* ── Main content: Library view ── */}
      {sidebarView === 'library' && (
        <main className="main">
          {!libraryPodcast ? (
            <div className="library-empty">
              <span className="library-empty-icon">🎧</span>
              <p>Select a podcast from the library to play it.</p>
            </div>
          ) : (
            <div className="output-section">
              <div className="library-player-header">
                <h2 className="library-player-title">{libraryPodcast.title}</h2>
                <div className="library-player-meta">
                  {libraryPodcast.source_url && (
                    <a
                      href={libraryPodcast.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="library-player-source"
                    >
                      {libraryPodcast.source_url}
                    </a>
                  )}
                  {libraryPodcast.source_filename && (
                    <span className="library-player-source">{libraryPodcast.source_filename}</span>
                  )}
                </div>
              </div>

              <CDPlayer key={libraryPodcast.id} audioUrl={libraryAudioUrl} />

              <div className="share-bar">
                <span className="share-bar-label">Share this podcast</span>
                <div className="share-bar-row">
                  <input
                    readOnly
                    className="share-input"
                    value={libraryShareUrl}
                    onFocus={e => e.target.select()}
                  />
                  <button
                    className="share-copy-btn"
                    onClick={() => {
                      navigator.clipboard.writeText(libraryShareUrl)
                      setLibraryCopied(true)
                      setTimeout(() => setLibraryCopied(false), 2000)
                    }}
                  >
                    {libraryCopied ? 'Copied!' : 'Copy Link'}
                  </button>
                </div>
              </div>

              {libraryScript && <ScriptViewer script={libraryScript} />}

              <div className="download-buttons">
                <a href={libraryAudioUrl} download className="download-btn">
                  ↓ Download MP3
                </a>
                <a href={libraryScriptUrl} className="download-btn secondary">
                  ↓ Download Script
                </a>
              </div>
            </div>
          )}
        </main>
      )}
    </div>
  )
}

export default App
