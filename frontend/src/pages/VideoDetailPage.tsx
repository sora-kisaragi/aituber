import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { MEDIA_BASE } from '../api/client'
import { getTimeline, getVideo } from '../api/videos'
import CommentaryList from '../components/CommentaryList'
import PipelineControl from '../components/PipelineControl'
import ProgressPanel from '../components/ProgressPanel'
import VideoPlayer from '../components/VideoPlayer'
import { useSSE } from '../hooks/useSSE'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: video, isLoading } = useQuery({
    queryKey: ['video', id],
    queryFn: () => getVideo(id!),
    enabled: !!id,
  })
  const { data: timeline, refetch: refetchTimeline } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => getTimeline(id!),
    enabled: !!id,
  })
  const { progress, active, start } = useSSE(id ?? null)
  const [videoKey, setVideoKey] = useState(0)

  const onComposeDone = () => {
    setVideoKey((k) => k + 1)
    refetchTimeline()
  }

  const onProcessDone = () => {
    refetchTimeline()
  }

  if (isLoading) return <p className="text-gray-400">読み込み中...</p>
  if (!video) return <p className="text-red-500">動画が見つかりません</p>

  const inputSrc = timeline?.input_rel
    ? `${MEDIA_BASE}/${timeline.input_rel}`
    : null
  const outputSrc = `${MEDIA_BASE}/${video.id}/output.mp4`

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-gray-800">{video.title}</h1>

      <PipelineControl
        videoId={video.id}
        onProcessStart={start}
        onComposeStart={start}
        onComposeDone={onComposeDone}
        onProcessDone={onProcessDone}
        disabled={active}
      />

      <ProgressPanel progress={progress} active={active} />

      {/* 動画プレイヤー */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {inputSrc && (
          <VideoPlayer src={inputSrc} label="オリジナル動画" />
        )}
        <VideoPlayer
          src={outputSrc}
          label="合成動画"
          refreshKey={videoKey}
        />
      </div>

      {/* 実況リスト */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="font-semibold text-gray-700 mb-3">
          実況リスト
          {timeline && (
            <span className="ml-2 text-sm font-normal text-gray-400">
              {timeline.items.length} 件
            </span>
          )}
        </h2>
        <CommentaryList items={timeline?.items ?? []} />
      </div>
    </div>
  )
}
