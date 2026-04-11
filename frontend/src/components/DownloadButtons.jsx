function DownloadButtons({ audioBlob, scriptText }) {
  const download = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadAudio = () => {
    download(audioBlob, 'podcast_episode.mp3')
  }

  const handleDownloadScript = () => {
    const blob = new Blob([scriptText], { type: 'text/plain' })
    download(blob, 'podcast_script.txt')
  }

  return (
    <div className="download-buttons">
      <button className="download-btn" onClick={handleDownloadAudio}>
        ↓ Download MP3
      </button>
      <button className="download-btn secondary" onClick={handleDownloadScript}>
        ↓ Download Script
      </button>
    </div>
  )
}

export default DownloadButtons
