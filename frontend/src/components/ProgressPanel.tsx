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

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>{step || (active ? '処理開始中...' : '完了')}</span>
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
