import { useRef, useState } from 'react'
import { uploadVideo } from '../api/videos'

interface Props {
  onUploaded: () => void
}

export default function VideoUpload({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [pct, setPct] = useState(0)
  const [error, setError] = useState('')

  const handleFile = async (file: File) => {
    setUploading(true)
    setError('')
    try {
      const title = file.name.replace(/\.[^.]+$/, '')
      await uploadVideo(file, title, setPct)
      onUploaded()
    } catch {
      setError('アップロードに失敗しました')
    } finally {
      setUploading(false)
      setPct(0)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
        dragging ? 'border-yellow-400 bg-yellow-50' : 'border-gray-300 bg-white'
      }`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      {uploading ? (
        <div className="space-y-2">
          <div className="text-sm text-gray-600">アップロード中... {pct}%</div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-yellow-400 h-2 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ) : (
        <>
          <p className="text-gray-500 mb-3">動画ファイルをドロップ、または</p>
          <button
            onClick={() => inputRef.current?.click()}
            className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors"
          >
            ファイルを選択
          </button>
        </>
      )}
      {error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
    </div>
  )
}
