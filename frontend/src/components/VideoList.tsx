import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MEDIA_BASE } from '../api/client'
import { deleteVideo, Video } from '../api/videos'

interface Props {
  videos: Video[]
  onDeleted: () => void
}

export default function VideoList({ videos, onDeleted }: Props) {
  const [search, setSearch] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [thumbnailErrorMap, setThumbnailErrorMap] = useState<
    Record<string, boolean>
  >({})

  const filtered = videos.filter((v) =>
    v.title.toLowerCase().includes(search.toLowerCase()),
  )

  const handleDelete = async (video: Video) => {
    if (
      !window.confirm(`「${video.title}」を削除しますか？\n関連データも削除されます。`)
    ) {
      return
    }
    setDeletingId(video.id)
    try {
      await deleteVideo(video.id)
      onDeleted()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`削除に失敗しました: ${msg}`)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-3">
      <input
        type="text"
        placeholder="タイトル検索..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
      />
      {filtered.length === 0 ? (
        <p className="text-gray-400 text-center py-8">動画がありません</p>
      ) : (
        <ul className="space-y-2">
          {filtered.map((v) => (
            <li
              key={v.id}
              className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:border-yellow-400 transition-colors"
            >
              <Link
                to={`/videos/${v.id}`}
                className="flex items-center gap-3 flex-1 min-w-0"
              >
                {thumbnailErrorMap[v.id] ? (
                  <div className="w-24 h-14 bg-gray-200 rounded shrink-0" />
                ) : (
                  <img
                    src={`${MEDIA_BASE}/${v.id}/thumbnail.jpg`}
                    alt={`${v.title} のサムネイル`}
                    className="w-24 h-14 object-cover rounded bg-gray-200 shrink-0"
                    onError={() =>
                      setThumbnailErrorMap((prev) => ({ ...prev, [v.id]: true }))
                    }
                  />
                )}
                <div>
                  <div className="font-medium text-gray-800">{v.title}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {v.duration_seconds != null
                      ? `${Math.round(v.duration_seconds)}秒`
                      : '不明'}
                    {v.created_at &&
                      ` · ${new Date(v.created_at).toLocaleString('ja-JP')}`}
                  </div>
                </div>
              </Link>
              <button
                type="button"
                onClick={() => handleDelete(v)}
                disabled={deletingId === v.id}
                className="px-3 py-1.5 text-xs rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {deletingId === v.id ? '削除中...' : '削除'}
              </button>
              <span className="text-gray-400 text-sm">→</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
