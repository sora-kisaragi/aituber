import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { MEDIA_BASE } from '../api/client'
import { getTimeline, getVideo, getVideoTags, updateVideo } from '../api/videos'
import CommentaryList from '../components/CommentaryList'
import PipelineControl from '../components/PipelineControl'
import ProgressPanel from '../components/ProgressPanel'
import VideoPlayer from '../components/VideoPlayer'
import { Progress, useSSE } from '../hooks/useSSE'

type OpState = 'idle' | 'running' | 'done'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [tagInput, setTagInput] = useState('')
  const [tagSaving, setTagSaving] = useState(false)
  const { data: video, isLoading } = useQuery({
    queryKey: ['video', id],
    queryFn: () => getVideo(id!),
    enabled: !!id,
  })
  const { data: tagInfo, refetch: refetchTags } = useQuery({
    queryKey: ['video-tags', id],
    queryFn: () => getVideoTags(id!),
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
  const panelProgress: Progress | null = (() => {
    if (opState === 'done') {
      return { step: 'done', pct: 100, message: '完了' }
    }
    if (!sseProgress) {
      return null
    }

    const cappedPct = Math.min(sseProgress.pct, 99)
    const isFinalizing =
      sseProgress.step === 'done' || sseProgress.pct >= 100 || cappedPct >= 99

    if (isFinalizing) {
      return { step: 'finalizing', pct: 99, message: '最終処理中...' }
    }

    return { ...sseProgress, pct: cappedPct }
  })()

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
    refetchTags()
  }

  const failOp = () => setOpState('idle')

  if (isLoading) return <p className="text-gray-400">読み込み中...</p>
  if (!video) return <p className="text-red-500">動画が見つかりません</p>

  const inputSrc = timeline?.input_rel
    ? `${MEDIA_BASE}/${timeline.input_rel}`
    : null
  const outputSrc = `${MEDIA_BASE}/${video.id}/output.mp4`
  const parseTags = (raw: string): string[] =>
    raw
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0)
  const dedupe = (tags: string[]): string[] => {
    const out: string[] = []
    const seen = new Set<string>()
    for (const tag of tags) {
      const key = tag.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      out.push(tag)
    }
    return out
  }
  const isSystemTag = (tag: string) => tag.startsWith('cfg:') || tag.startsWith('video:')
  const effectiveTags = tagInfo?.tags_effective ?? []
  const systemTags = effectiveTags.filter(isSystemTag)
  const contentTags = effectiveTags.filter((tag) => !isSystemTag(tag))
  const manualTags = tagInfo?.tags_manual ?? []

  const saveManualTags = async (nextManualTags: string[]) => {
    if (!id) return
    setTagSaving(true)
    try {
      await updateVideo(id, { tags_manual: nextManualTags })
      await refetchTags()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`タグ更新に失敗しました: ${msg}`)
    } finally {
      setTagSaving(false)
    }
  }

  const handleManualTagAdd = async () => {
    const incoming = parseTags(tagInput)
    if (incoming.length === 0) {
      window.alert('追加するタグを入力してください。')
      return
    }
    const nextTags = dedupe([...manualTags, ...incoming])
    await saveManualTags(nextTags)
    setTagInput('')
  }

  const handleManualTagRemove = async (target: string) => {
    const nextTags = manualTags.filter((tag) => tag !== target)
    await saveManualTags(nextTags)
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-gray-800">{video.title}</h1>

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
        <h2 className="font-semibold text-gray-700">タグ</h2>

        <div className="space-y-2">
          <p className="text-xs text-gray-500">コンテンツタグ</p>
          <div className="flex flex-wrap gap-1">
            {contentTags.length === 0 ? (
              <span className="text-sm text-gray-400">なし</span>
            ) : (
              contentTags.map((tag) => (
                <span
                  key={`content-${tag}`}
                  className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-100"
                >
                  {tag}
                </span>
              ))
            )}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs text-gray-500">システムタグ</p>
          <div className="flex flex-wrap gap-1">
            {systemTags.length === 0 ? (
              <span className="text-sm text-gray-400">なし</span>
            ) : (
              systemTags.map((tag) => (
                <span
                  key={`system-${tag}`}
                  className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700 border border-gray-200"
                >
                  {tag}
                </span>
              ))
            )}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs text-gray-500">手動タグ編集</p>
          <div className="flex flex-wrap gap-2">
            {manualTags.length === 0 ? (
              <span className="text-sm text-gray-400">手動タグなし</span>
            ) : (
              manualTags.map((tag) => (
                <button
                  key={`manual-${tag}`}
                  type="button"
                  onClick={() => handleManualTagRemove(tag)}
                  disabled={tagSaving}
                  className="px-2 py-0.5 text-xs rounded-full bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 disabled:opacity-50"
                  title="クリックで削除"
                >
                  {tag} ×
                </button>
              ))
            )}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="追加タグ（カンマ区切り）"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
            <button
              type="button"
              onClick={handleManualTagAdd}
              disabled={tagSaving}
              className="px-3 py-2 border border-amber-200 text-amber-700 rounded-lg text-sm hover:bg-amber-50 disabled:opacity-50"
            >
              {tagSaving ? '保存中...' : '手動タグ追加'}
            </button>
          </div>
        </div>
      </div>

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
