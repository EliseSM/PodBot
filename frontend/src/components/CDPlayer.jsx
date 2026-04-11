import { useState } from 'react'

function CDPlayer({ audioUrl }) {
  const [isPlaying, setIsPlaying] = useState(false)

  return (
    <div className="cd-player">
      <div className="cd-container">
        <img
          src="/cd.svg"
          alt="CD disc"
          className={`cd-disc${isPlaying ? ' spinning' : ''}`}
        />
      </div>
      <audio
        src={audioUrl}
        controls
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
        className="audio-element"
      />
    </div>
  )
}

export default CDPlayer
