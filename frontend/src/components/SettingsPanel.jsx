const DURATION_OPTIONS = [2, 5, 10, 15]

const TONE_OPTIONS = [
  { id: 'briefing',       label: 'Briefing',       sub: 'Fast, factual'      },
  { id: 'explainer',      label: 'Explainer',       sub: 'Clear, structured'  },
  { id: 'conversational', label: 'Conversational',  sub: 'Casual, engaging'   },
]

function SettingsPanel({ settings, onChange, disabled }) {
  const toggleTone = (id) => {
    const next = settings.tones.includes(id)
      ? settings.tones.filter(t => t !== id)
      : [...settings.tones, id]
    if (next.length === 0) return   // always keep at least one tone
    onChange({ ...settings, tones: next })
  }

  return (
    <div>
      <p className="settings-title">Settings</p>

      <div className="setting-group">
        <label className="setting-label">Podcast Length</label>
        <div className="duration-options">
          {DURATION_OPTIONS.map(mins => (
            <button
              key={mins}
              className={`duration-btn${settings.targetDuration === mins ? ' active' : ''}`}
              onClick={() => onChange({ ...settings, targetDuration: mins })}
              disabled={disabled}
            >
              {mins}m
            </button>
          ))}
        </div>
      </div>

      <div className="setting-group">
        <label className="setting-label">Tone</label>
        <div className="tone-options">
          {TONE_OPTIONS.map(({ id, label, sub }) => (
            <button
              key={id}
              className={`tone-btn${settings.tones.includes(id) ? ' active' : ''}`}
              onClick={() => toggleTone(id)}
              disabled={disabled}
            >
              <span className="tone-btn-label">{label}</span>
              <span className="tone-btn-sub">{sub}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="setting-group">
        <label className="setting-label">LLM Provider</label>
        <select
          className="setting-select"
          value={settings.llmProvider}
          onChange={e => onChange({ ...settings, llmProvider: e.target.value })}
          disabled={disabled}
        >
          <option value="openai">OpenAI GPT-4o</option>
          <option value="anthropic">Claude Sonnet 4.6</option>
        </select>
      </div>

      <div className="setting-group">
        <label className="setting-label">
          Max Rewrites
          <span className="setting-value">{settings.maxRewrites}</span>
        </label>
        <input
          type="range"
          min="0"
          max="5"
          value={settings.maxRewrites}
          onChange={e => onChange({ ...settings, maxRewrites: Number(e.target.value) })}
          disabled={disabled}
          className="setting-slider"
        />
        <div className="slider-labels">
          <span>0 (no revisions)</span>
          <span>5</span>
        </div>
      </div>
    </div>
  )
}

export default SettingsPanel
