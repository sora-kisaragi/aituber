import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listVideos } from '../api/videos'
import VideoList from '../components/VideoList'
import VideoUpload from '../components/VideoUpload'

export default function VideosPage() {
  const queryClient = useQueryClient()
  const { data: videos = [], isLoading } = useQuery({
    queryKey: ['videos'],
    queryFn: listVideos,
  })

  const refetch = () => queryClient.invalidateQueries({ queryKey: ['videos'] })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">動画一覧</h1>
      <VideoUpload onUploaded={refetch} />
      {isLoading ? (
        <p className="text-gray-400 text-center py-8">読み込み中...</p>
      ) : (
        <VideoList videos={videos} />
      )}
    </div>
  )
}
