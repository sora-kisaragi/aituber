import { MEDIA_BASE } from '../api/client'

interface Props {
  videoId: string
  refreshKey?: number
}

export default function VideoPlayer({ videoId, refreshKey = 0 }: Props) {
  const src = `${MEDIA_BASE}/${videoId}/output.mp4`

  return (
    <div className="bg-black rounded-xl overflow-hidden">
      <video
        key={`${src}-${refreshKey}`}
        controls
        className="w-full max-h-[480px]"
        src={src}
      >
        お使いのブラウザは動画再生に対応していません。
      </video>
    </div>
  )
}
