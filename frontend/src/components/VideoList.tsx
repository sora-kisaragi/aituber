import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Video } from '../api/videos'

interface Props {
  videos: Video[]
}

export default function VideoList({ videos }: Props) {
  const [search, setSearch] = useState('')

  const filtered = videos.filter((v) =>
    v.title.toLowerCase().includes(search.toLowerCase()),
  )

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
            <li key={v.id}>
              <Link
                to={`/videos/${v.id}`}
                className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-yellow-400 transition-colors"
              >
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
                <span className="text-gray-400 text-sm">→</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
