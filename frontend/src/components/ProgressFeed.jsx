const NODE_LABELS = {
  create_outline:  'Creating episode outline',
  create_draft:    'Writing first draft',
  critique_draft:  'Critiquing draft',
  revise_draft:    'Revising script',
  finalize:        'Finalizing script',
  generating_audio:'Generating audio',
}

function ProgressFeed({ nodes, isGenerating }) {
  return (
    <div className="progress-feed">
      <p className="progress-title">Generation Progress</p>
      <div className="progress-list">
        {nodes.map((node, i) => (
          <div key={i} className="progress-item done">
            <span className="progress-dot">✓</span>
            <span className="progress-label">{NODE_LABELS[node] ?? node}</span>
          </div>
        ))}
        {isGenerating && (
          <div className="progress-item running">
            <span className="progress-dot">●</span>
            <span className="progress-label">Working…</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default ProgressFeed
