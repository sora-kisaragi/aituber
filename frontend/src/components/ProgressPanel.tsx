import { Progress } from '../hooks/useSSE'

interface Props {
  progress: Progress | null
  active: boolean
}

export default function ProgressPanel({ progress, active }: Props) {
  if (!active && !progress) return null

  const pct = progress?.pct ?? 0
  const step = progress?.step ?? ''
  const message = progress?.message ?? ''
  const stepLabels: Record<string, string> = {
    segmentation: '動画分割',
    vision: 'フレーム解析',
    planning: '発話計画',
    commentary: '実況生成',
    tts: '音声合成',
    compose: '動画合成',
    finalizing: '最終処理中...',
    done: '完了',
  }
  const stepLabel = stepLabels[step] ?? step

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>{stepLabel || (active ? '処理開始中...' : '完了')}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-3">
        <div
          className={`h-3 rounded-full transition-all ${pct >= 100 ? 'bg-green-500' : 'bg-blue-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {message && <p className="text-xs text-gray-400">{message}</p>}
    </div>
  )
}
