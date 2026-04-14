import { useEffect, useState } from 'react'
import { fetchLibrary } from '../api'

function formatDate(isoString) {
  return new Date(isoString + 'Z').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function LibraryPanel({ selected, onSelect }) {
  const [podcasts, setPodcasts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    fetchLibrary()
      .then(({ podcasts }) => setPodcasts(podcasts))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  if (loading) {
    return <div className="library-status">Loading…</div>
  }

  if (error) {
    return (
      <div className="library-status library-status--error">
        {error}
        <button className="library-refresh-btn" onClick={load}>Retry</button>
      </div>
    )
  }

  if (podcasts.length === 0) {
    return (
      <div className="library-status">
        No podcasts yet. Generate one to get started.
      </div>
    )
  }

  return (
    <div className="library-panel">
      <div className="library-panel-header">
        <span className="settings-title">Library</span>
        <button className="library-refresh-btn" onClick={load} title="Refresh">↺</button>
      </div>

      <ul className="library-list">
        {podcasts.map(podcast => (
          <li key={podcast.id}>
            <button
              className={`library-item${selected?.id === podcast.id ? ' library-item--active' : ''}`}
              onClick={() => onSelect(podcast)}
            >
              <span className="library-item-title">{podcast.title}</span>
              <span className="library-item-date">{formatDate(podcast.created_at)}</span>
              {podcast.source_url && (
                <span className="library-item-badge">URL</span>
              )}
              {podcast.source_filename && (
                <span className="library-item-badge">{podcast.source_filename.split('.').pop().toUpperCase()}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default LibraryPanel
