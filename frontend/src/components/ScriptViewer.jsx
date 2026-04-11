import { useState } from 'react'

function ScriptViewer({ script }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="script-viewer">
      <button className="script-toggle" onClick={() => setIsOpen(o => !o)}>
        {isOpen ? '▲ Hide Script' : '▼ View Script'}
      </button>
      {isOpen && <pre className="script-text">{script}</pre>}
    </div>
  )
}

export default ScriptViewer
