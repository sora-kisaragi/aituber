import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { MEDIA_BASE } from '../api/client'
import {
  getTimeline,
  getVideo,
  getVideoTags,
  refreshVideoLlmTags,
  refreshVideoRuleTags,
  refreshVideoTags,
  updateVideo,
} from '../api/videos'
import CommentaryList from '../components/CommentaryList'
import PipelineControl from '../components/PipelineControl'
import ProgressPanel from '../components/ProgressPanel'
import VideoPlayer from '../components/VideoPlayer'
import { Progress, useSSE } from '../hooks/useSSE'

type OpState = 'idle' | 'running' | 'done'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: video, isLoading, refetch: refetchVideo } = useQuery({
    queryKey: ['video', id],
    queryFn: () => getVideo(id!),
    enabled: !!id,
  })
  const { data: timeline, refetch: refetchTimeline } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => getTimeline(id!),
    enabled: !!id,
  })
  const { data: tagInfo, refetch: refetchTags, isLoading: isTagsLoading } = useQuery({
    queryKey: ['video-tags', id],
    queryFn: () => getVideoTags(id!),
    enabled: !!id,
  })

  const { progress: sseProgress, start } = useSSE(id ?? null)
  const [opState, setOpState] = useState<OpState>('idle')
  const [videoKey, setVideoKey] = useState(0)
  const [tagInput, setTagInput] = useState('')
  const [tagUpdating, setTagUpdating] = useState(false)
  const [tagRefreshingKey, setTagRefreshingKey] = useState<string | null>(null)

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
    refetchVideo()
    refetchTags()
  }

  const finishProcess = () => {
    setOpState('done')
    refetchTimeline()
    refetchVideo()
    refetchTags()
  }

  const failOp = () => setOpState('idle')

  if (isLoading) return <p className="text-gray-400">読み込み中...</p>
  if (!video) return <p className="text-red-500">動画が見つかりません</p>

  const inputSrc = timeline?.input_rel
    ? `${MEDIA_BASE}/${timeline.input_rel}`
    : null
  const outputSrc = `${MEDIA_BASE}/${video.id}/output.mp4`
  const manualTags = tagInfo?.tags_manual ?? []
  const ruleTags = tagInfo?.tags_auto_rule ?? []
  const llmTags = tagInfo?.tags_auto_llm ?? []
  const effectiveTags = tagInfo?.tags_effective ?? []
  const suggestedTags = tagInfo?.tags_suggested_llm ?? []
  const llmError = tagInfo?.tag_status?.llm_error
  const isSystemTag = (tag: string): boolean =>
    tag.startsWith('cfg:') || tag.startsWith('video:')
  const parseTags = (raw: string): string[] =>
    raw
      .split(',')
      .map((t) => normalizeManualTagInput(t))
      .filter((t) => t.length > 0)

  const normalizeManualTagInput = (raw: string): string => {
    const tag = raw.trim()
    if (!tag) return ''
    if (tag.includes(':')) return tag
    return `topic:${tag}`
  }
  const mergeTags = (current: string[], incoming: string[]): string[] => {
    const merged: string[] = []
    const seen = new Set<string>()
    for (const tag of [...current, ...incoming]) {
      const trimmed = tag.trim()
      if (!trimmed) continue
      const key = trimmed.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      merged.push(trimmed)
    }
    return merged
  }

  const updateManualTags = async (nextTags: string[]) => {
    if (!id) return
    setTagUpdating(true)
    try {
      await updateVideo(id, { tags_manual: nextTags })
      await Promise.all([refetchVideo(), refetchTags()])
      setTagInput('')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`タグ更新に失敗しました: ${msg}`)
    } finally {
      setTagUpdating(false)
    }
  }

  const handleAddManualTags = async () => {
    const parsed = parseTags(tagInput)
    if (parsed.length === 0) {
      window.alert('タグを入力してください。例: お気に入り, 要確認')
      return
    }
    await updateManualTags(mergeTags(manualTags, parsed))
  }

  const handleRemoveManualTag = async (tag: string) => {
    await updateManualTags(manualTags.filter((t) => t !== tag))
  }

  const handleAcceptSuggestedTag = async (tag: string) => {
    await updateManualTags(mergeTags(manualTags, [tag]))
  }

  const handleRefreshTags = async (mode: 'all' | 'rule' | 'llm') => {
    if (!id) return
    const key = `${id}:${mode}`
    setTagRefreshingKey(key)
    try {
      if (mode === 'all') {
        await refreshVideoTags(id)
      } else if (mode === 'rule') {
        await refreshVideoRuleTags(id)
      } else {
        await refreshVideoLlmTags(id)
      }
      await Promise.all([refetchVideo(), refetchTags()])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`タグ再生成に失敗しました: ${msg}`)
    } finally {
      setTagRefreshingKey(null)
    }
  }

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

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-gray-700">タグ編集</h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleRefreshTags('all')}
              disabled={tagRefreshingKey === `${id}:all`}
              className="px-3 py-1.5 text-xs rounded border border-blue-200 text-blue-700 hover:bg-blue-50 disabled:opacity-50"
            >
              {tagRefreshingKey === `${id}:all` ? '再生成中...' : 'タグ再生成（全体）'}
            </button>
            <button
              type="button"
              onClick={() => handleRefreshTags('rule')}
              disabled={tagRefreshingKey === `${id}:rule`}
              className="px-3 py-1.5 text-xs rounded border border-sky-200 text-sky-700 hover:bg-sky-50 disabled:opacity-50"
            >
              Rule再生成
            </button>
            <button
              type="button"
              onClick={() => handleRefreshTags('llm')}
              disabled={tagRefreshingKey === `${id}:llm`}
              className="px-3 py-1.5 text-xs rounded border border-violet-200 text-violet-700 hover:bg-violet-50 disabled:opacity-50"
            >
              LLM再生成
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-3">
          <div className="rounded-lg border border-blue-100 bg-blue-50/40 p-3 space-y-2">
            <p className="text-xs font-semibold text-blue-800">手動タグ</p>
            <div className="flex flex-wrap gap-1">
              {manualTags.length === 0 ? (
                <span className="text-xs text-gray-400">未設定</span>
              ) : (
                manualTags.map((tag) => (
                  <span
                    key={`manual-${tag}`}
                    className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-blue-100 text-blue-800 border border-blue-200"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveManualTag(tag)}
                      disabled={tagUpdating}
                      className="text-blue-500 hover:text-blue-700 disabled:opacity-50"
                      aria-label={`${tag} を削除`}
                    >
                      ×
                    </button>
                  </span>
                ))
              )}
            </div>
            <div className="space-y-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="手動タグ追加（例: boss戦, topic:boss戦）"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
              />
              <button
                type="button"
                onClick={handleAddManualTags}
                disabled={tagUpdating}
                className="w-full px-3 py-2 border border-blue-200 text-blue-700 rounded-lg text-sm hover:bg-blue-50 disabled:opacity-50"
              >
                {tagUpdating ? '更新中...' : '手動タグを追加'}
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-sky-100 bg-sky-50/40 p-3 space-y-2">
            <p className="text-xs font-semibold text-sky-800">Ruleベースタグ</p>
            <div className="flex flex-wrap gap-1">
              {ruleTags.length === 0 ? (
                <span className="text-xs text-gray-400">未生成</span>
              ) : (
                ruleTags.map((tag) => (
                  <span
                    key={`rule-${tag}`}
                    className="px-2 py-0.5 text-[11px] rounded-full bg-sky-100 text-sky-800 border border-sky-200"
                  >
                    {tag}
                  </span>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-violet-100 bg-violet-50/40 p-3 space-y-2">
            <p className="text-xs font-semibold text-violet-800">LLMタグ</p>
            <div className="flex flex-wrap gap-1">
              {llmTags.length === 0 ? (
                <span className="text-xs text-gray-400">未生成</span>
              ) : (
                llmTags.map((tag) => (
                  <span
                    key={`llm-${tag}`}
                    className="px-2 py-0.5 text-[11px] rounded-full bg-violet-100 text-violet-800 border border-violet-200"
                  >
                    {tag}
                  </span>
                ))
              )}
            </div>
            {suggestedTags.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] text-violet-700">候補タグ（クリックで手動へ採用）</p>
                <div className="flex flex-wrap gap-1">
                  {suggestedTags.map((tag) => (
                    <button
                      key={`suggested-${tag}`}
                      type="button"
                      onClick={() => handleAcceptSuggestedTag(tag)}
                      disabled={tagUpdating}
                      className="px-2 py-0.5 text-[11px] rounded-full bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-50"
                    >
                      候補: {tag}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
            <p className="text-xs font-semibold text-gray-700">有効タグ（最終表示）</p>
            <div className="flex flex-wrap gap-1">
              {effectiveTags
                .filter((tag) => !isSystemTag(tag))
                .map((tag) => (
                  <span
                    key={`effective-content-${tag}`}
                    className="px-2 py-0.5 text-[11px] rounded-full bg-blue-50 text-blue-700 border border-blue-100"
                  >
                    {tag}
                  </span>
                ))}
              {effectiveTags
                .filter((tag) => isSystemTag(tag))
                .map((tag) => (
                  <span
                    key={`effective-system-${tag}`}
                    className="px-2 py-0.5 text-[11px] rounded-full bg-gray-100 text-gray-700 border border-gray-200"
                  >
                    SYS: {tag}
                  </span>
                ))}
            </div>
            {effectiveTags.length === 0 && !isTagsLoading && (
              <span className="text-xs text-gray-400">有効タグはまだありません</span>
            )}
          </div>
        </div>

        {llmError && <p className="text-xs text-amber-700">{llmError}</p>}
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
