interface Props {
  src: string
  label?: string
  refreshKey?: number
}

export default function VideoPlayer({ src, label, refreshKey = 0 }: Props) {
  return (
    <div className="space-y-1">
      {label && <p className="text-sm font-medium text-gray-600">{label}</p>}
      <div className="bg-black rounded-xl overflow-hidden">
        <video
          key={`${src}-${refreshKey}`}
          controls
          className="w-full max-h-[400px]"
          src={src}
        >
          お使いのブラウザは動画再生に対応していません。
        </video>
      </div>
    </div>
  )
}
