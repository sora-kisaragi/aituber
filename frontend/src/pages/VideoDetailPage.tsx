import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { MEDIA_BASE } from '../api/client'
import { getTimeline, getVideo } from '../api/videos'
import CommentaryList from '../components/CommentaryList'
import PipelineControl from '../components/PipelineControl'
import ProgressPanel from '../components/ProgressPanel'
import VideoPlayer from '../components/VideoPlayer'
import { Progress, useSSE } from '../hooks/useSSE'

type OpState = 'idle' | 'running' | 'done'

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

  const { progress: sseProgress, start } = useSSE(id ?? null)
  const [opState, setOpState] = useState<OpState>('idle')
  const [videoKey, setVideoKey] = useState(0)

  // SSE は途中経過のみ（99% 上限）。POST 完了時に初めて 100% を表示する。
  const panelProgress: Progress | null =
    opState === 'done'
      ? { step: 'done', pct: 100, message: '完了' }
      : sseProgress
        ? { ...sseProgress, pct: Math.min(sseProgress.pct, 99) }
        : null

  const startOp = () => {
    setOpState('running')
    start()
  }

  const finishCompose = () => {
    setOpState('done')
    setVideoKey((k) => k + 1)
    refetchTimeline()
  }

  const finishProcess = () => {
    setOpState('done')
    refetchTimeline()
  }

  const failOp = () => setOpState('idle')

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
        onProcessStart={startOp}
        onComposeStart={startOp}
        onProcessDone={finishProcess}
        onComposeDone={finishCompose}
        onOperationFail={failOp}
        disabled={opState === 'running'}
      />

      <ProgressPanel progress={panelProgress} active={opState === 'running'} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {inputSrc && <VideoPlayer src={inputSrc} label="オリジナル動画" />}
        <VideoPlayer src={outputSrc} label="合成動画" refreshKey={videoKey} />
      </div>

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
