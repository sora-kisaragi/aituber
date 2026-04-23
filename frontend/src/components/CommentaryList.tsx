import { useRef, useState } from 'react'
import { MEDIA_BASE } from '../api/client'
import { TimelineItem } from '../api/videos'

interface Props {
  items: TimelineItem[]
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = (sec % 60).toFixed(1).padStart(4, '0')
  return `${m}:${s}`
}

const STYLE_BADGE: Record<string, string> = {
  excited: 'bg-red-100 text-red-700',
  neutral: 'bg-gray-100 text-gray-600',
  calm: 'bg-blue-100 text-blue-700',
}

export default function CommentaryList({ items }: Props) {
  const [playingId, setPlayingId] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const toggle = (item: TimelineItem) => {
    if (!item.audio_rel) return

    if (playingId === item.commentary_id) {
      audioRef.current?.pause()
      setPlayingId(null)
      return
    }

    if (audioRef.current) {
      audioRef.current.pause()
    }
    const audio = new Audio(`${MEDIA_BASE}/${item.audio_rel}`)
    audio.onended = () => setPlayingId(null)
    audio.play()
    audioRef.current = audio
    setPlayingId(item.commentary_id)
  }

  if (items.length === 0) {
    return <p className="text-gray-400 text-sm text-center py-4">実況データがありません（解析・実況生成を実行してください）</p>
  }

  return (
    <div className="divide-y divide-gray-100">
      {items.map((item) => {
        const isPlaying = playingId === item.commentary_id
        const badge = STYLE_BADGE[item.style] ?? 'bg-gray-100 text-gray-600'
        return (
          <div key={item.commentary_id} className="flex gap-3 py-3 items-start">
            {/* 時間 */}
            <span className="text-xs text-gray-400 font-mono w-14 shrink-0 pt-0.5">
              {formatTime(item.start_time)}
            </span>

            {/* 再生ボタン */}
            <button
              onClick={() => toggle(item)}
              disabled={!item.audio_rel}
              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors
                ${item.audio_rel
                  ? isPlaying
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                  : 'bg-gray-100 text-gray-300 cursor-not-allowed'}`}
              title={item.audio_rel ? (isPlaying ? '停止' : '再生') : '音声なし'}
            >
              {isPlaying ? '■' : '▶'}
            </button>

            {/* スタイルバッジ＋テキスト */}
            <div className="flex-1 min-w-0">
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${badge} mr-2`}>
                {item.style}
              </span>
              <span className="text-sm text-gray-800 leading-relaxed break-words">
                {item.text}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
