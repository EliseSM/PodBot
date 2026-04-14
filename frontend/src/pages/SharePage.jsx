import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import './SharePage.css'

const BASE = '/api'

const LLM_LABELS = {
  openai: 'OpenAI GPT-4o',
  anthropic: 'Claude',
}

function SharePage() {
  const { id } = useParams()
  const [podcast, setPodcast] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${BASE}/share/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('This podcast could not be found.')
        return res.json()
      })
      .then(data => {
        setPodcast(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [id])

  const audioUrl    = `${BASE}/share/${id}/audio`
  const scriptUrl   = `${BASE}/share/${id}/download/script`

  if (loading) {
    return (
      <div className="share-page">
        <ShareHeader />
        <div className="share-state">Loading…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="share-page">
        <ShareHeader />
        <div className="share-state share-state--error">{error}</div>
      </div>
    )
  }

  const formattedDate = new Date(podcast.created_at + 'Z').toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  })

  const llmLabel = LLM_LABELS[podcast.llm_provider] ?? podcast.llm_provider

  return (
    <div className="share-page">
      <ShareHeader />

      <main className="share-main">
        <div className="share-card">
          <h1 className="share-title">{podcast.title}</h1>

          <div className="share-meta">
            {podcast.source_url && (
              <div className="share-meta-item">
                <span className="share-meta-label">Source</span>
                <a
                  href={podcast.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="share-meta-link"
                >
                  {podcast.source_url}
                </a>
              </div>
            )}
            {podcast.source_filename && (
              <div className="share-meta-item">
                <span className="share-meta-label">Source</span>
                <span className="share-meta-value">{podcast.source_filename}</span>
              </div>
            )}
            <div className="share-meta-pills">
              <span className="share-pill">{formattedDate}</span>
              <span className="share-pill">{llmLabel}</span>
            </div>
          </div>

          <audio
            className="share-audio"
            controls
            src={audioUrl}
          />

          <div className="share-downloads">
            <a href={audioUrl} download className="download-btn">
              Download MP3
            </a>
            <a href={scriptUrl} className="download-btn secondary">
              Download Script
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}

function ShareHeader() {
  return (
    <header className="share-header">
      <a href="/" className="logo share-logo">
        <span className="logo-icon">🎙</span>
        <span className="logo-text">PodBot</span>
      </a>
    </header>
  )
}

export default SharePage
