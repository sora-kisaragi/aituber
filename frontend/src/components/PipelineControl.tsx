import { useState } from 'react'
import { composeVideo, exportVideoUrl, processVideo } from '../api/videos'

interface Props {
  videoId: string
  onProcessStart: () => void
  onComposeStart: () => void
  onProcessDone?: () => void
  onComposeDone: () => void
  onOperationFail?: () => void
  disabled?: boolean
}

export default function PipelineControl({
  videoId,
  onProcessStart,
  onComposeStart,
  onProcessDone,
  onComposeDone,
  onOperationFail,
  disabled,
}: Props) {
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState('')

  const run = async (
    label: string,
    fn: () => Promise<void>,
    onStart: () => void,
    onDone?: () => void,
  ) => {
    setLoading(label)
    setError('')
    onStart()
    try {
      await fn()
      onDone?.()
    } catch {
      setError(`${label}に失敗しました`)
      onOperationFail?.()
    } finally {
      setLoading(null)
    }
  }

  const isDisabled = !!loading || !!disabled

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">パイプライン</h2>
      <div className="flex flex-wrap gap-2">
        <button
          className="px-4 py-2 bg-blue-500 text-white rounded-lg font-medium text-sm hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={isDisabled}
          onClick={() =>
            run('処理', () => processVideo(videoId), onProcessStart, onProcessDone)
          }
        >
          {loading === '処理' ? '処理中...' : '解析・実況生成'}
        </button>
        <button
          className="px-4 py-2 bg-green-500 text-white rounded-lg font-medium text-sm hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={isDisabled}
          onClick={() =>
            run('合成', () => composeVideo(videoId), onComposeStart, onComposeDone)
          }
        >
          {loading === '合成' ? '合成中...' : '動画合成'}
        </button>
        <a
          href={exportVideoUrl(videoId)}
          download
          className="px-4 py-2 bg-gray-700 text-white rounded-lg font-medium text-sm hover:bg-gray-800 transition-colors inline-block"
        >
          エクスポート
        </a>
      </div>
      {error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
    </div>
  )
}
