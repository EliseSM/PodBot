import { useState } from 'react'
import { ingestUrl, ingestFile } from '../api'

function InputPanel({ sourceContent, onSourceContent, originalPrompt, onOriginalPrompt, onSourceMeta, disabled }) {
  const [activeTab, setActiveTab] = useState('url')
  const [urlInput, setUrlInput] = useState('')
  const [status, setStatus] = useState(null)   // { type: 'loading'|'success'|'error', message }
  const [isLoading, setIsLoading] = useState(false)

  const handleTabChange = (tabId) => {
    setActiveTab(tabId)
    if (tabId === 'paste') {
      onSourceMeta?.({ source_url: null, source_filename: null })
    }
  }

  const handleLoadUrl = async () => {
    if (!urlInput.trim()) return
    setIsLoading(true)
    setStatus({ type: 'loading', message: 'Fetching URL…' })
    try {
      const { text } = await ingestUrl(urlInput.trim())
      onSourceContent(text)
      onSourceMeta?.({ source_url: urlInput.trim(), source_filename: null })
      setStatus({ type: 'success', message: `Loaded ${text.length.toLocaleString()} characters` })
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setIsLoading(true)
    setStatus({ type: 'loading', message: `Reading ${file.name}…` })
    try {
      const { text } = await ingestFile(file)
      onSourceContent(text)
      onSourceMeta?.({ source_url: null, source_filename: file.name })
      setStatus({ type: 'success', message: `Loaded ${text.length.toLocaleString()} characters from ${file.name}` })
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="input-panel">
      <div className="field-group">
        <label className="field-label">Episode Topic / Title</label>
        <input
          type="text"
          className="field-input"
          placeholder="e.g. The Rise of AI Agents"
          value={originalPrompt}
          onChange={e => onOriginalPrompt(e.target.value)}
          disabled={disabled}
        />
      </div>

      <div className="tabs">
        {[
          { id: 'url',   label: 'URL' },
          { id: 'file',  label: 'Upload File' },
          { id: 'paste', label: 'Paste Text' },
        ].map(({ id, label }) => (
          <button
            key={id}
            className={`tab${activeTab === id ? ' active' : ''}`}
            onClick={() => handleTabChange(id)}
            disabled={disabled}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'url' && (
          <div className="url-row">
            <input
              type="url"
              className="field-input"
              placeholder="https://example.com/article"
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLoadUrl()}
              disabled={disabled || isLoading}
            />
            <button
              className="load-btn"
              onClick={handleLoadUrl}
              disabled={!urlInput.trim() || disabled || isLoading}
            >
              {isLoading ? '…' : 'Load'}
            </button>
          </div>
        )}

        {activeTab === 'file' && (
          <label className="file-upload-area">
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              disabled={disabled || isLoading}
              className="file-input-hidden"
            />
            <span className="file-upload-text">
              {isLoading ? 'Processing…' : 'Click to upload PDF, DOCX, or TXT'}
            </span>
          </label>
        )}

        {activeTab === 'paste' && (
          <textarea
            className="paste-area"
            placeholder="Paste your article or document text here…"
            value={sourceContent}
            onChange={e => onSourceContent(e.target.value)}
            disabled={disabled}
            rows={7}
          />
        )}

        {status && activeTab !== 'paste' && (
          <div className={`status-msg status-${status.type}`}>
            {status.message}
          </div>
        )}

        {sourceContent && activeTab !== 'paste' && (
          <div className="content-preview">
            <span className="preview-label">Content loaded</span>
            <span className="preview-chars">{sourceContent.length.toLocaleString()} chars</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default InputPanel
