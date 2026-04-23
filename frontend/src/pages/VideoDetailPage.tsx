import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { getVideo } from '../api/videos'
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
  const { progress, active, start } = useSSE(id ?? null)
  const [videoKey, setVideoKey] = useState(0)

  if (isLoading) return <p className="text-gray-400">読み込み中...</p>
  if (!video) return <p className="text-red-500">動画が見つかりません</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">{video.title}</h1>
      <PipelineControl
        videoId={video.id}
        onProcessStart={start}
        onComposeStart={start}
        onComposeDone={() => setVideoKey((k) => k + 1)}
        disabled={active}
      />
      <ProgressPanel progress={progress} active={active} />
      <VideoPlayer videoId={video.id} refreshKey={videoKey} />
    </div>
  )
}
