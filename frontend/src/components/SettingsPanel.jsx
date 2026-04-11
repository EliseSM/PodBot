function SettingsPanel({ settings, onChange, disabled }) {
  return (
    <div>
      <p className="settings-title">Settings</p>

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
