import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MEDIA_BASE } from '../api/client'
import { deleteVideo, updateVideo, Video } from '../api/videos'

interface Props {
  videos: Video[]
  onChanged: () => void
}

export default function VideoList({ videos, onChanged }: Props) {
  const [search, setSearch] = useState('')
  const [tagFilter, setTagFilter] = useState<string>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [tagInput, setTagInput] = useState('')
  const [tagging, setTagging] = useState(false)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameInput, setRenameInput] = useState('')
  const [renaming, setRenaming] = useState(false)
  const [thumbnailErrorMap, setThumbnailErrorMap] = useState<
    Record<string, boolean>
  >({})

  const allTags = Array.from(
    new Set(
      videos.flatMap((v) => (Array.isArray(v.video_metadata?.tags) ? v.video_metadata.tags : [])),
    ),
  ).sort((a, b) => a.localeCompare(b, 'ja'))

  const filtered = videos.filter((v) =>
    {
      const tags = Array.isArray(v.video_metadata?.tags) ? v.video_metadata.tags : []
      const query = search.trim().toLowerCase()
      const matchSearch =
        query.length === 0 ||
        v.title.toLowerCase().includes(query) ||
        tags.some((t) => t.toLowerCase().includes(query))
      const matchTag = tagFilter === 'all' || tags.includes(tagFilter)
      return matchSearch && matchTag
    },
  )
  const filteredIds = filtered.map((v) => v.id)
  const allFilteredSelected =
    filteredIds.length > 0 && filteredIds.every((id) => selectedIds.has(id))

  const parseTags = (raw: string): string[] =>
    raw
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0)

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

  const toggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        for (const id of filteredIds) next.delete(id)
        return next
      })
      return
    }
    setSelectedIds((prev) => {
      const next = new Set(prev)
      for (const id of filteredIds) next.add(id)
      return next
    })
  }

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleDelete = async (video: Video) => {
    if (
      !window.confirm(`「${video.title}」を削除しますか？\n関連データも削除されます。`)
    ) {
      return
    }
    setDeletingId(video.id)
    try {
      await deleteVideo(video.id)
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.delete(video.id)
        return next
      })
      onChanged()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`削除に失敗しました: ${msg}`)
    } finally {
      setDeletingId(null)
    }
  }

  const handleApplyTag = async () => {
    const targetIds = Array.from(selectedIds)
    const newTags = parseTags(tagInput)
    if (targetIds.length === 0) {
      window.alert('タグを付ける動画を選択してください。')
      return
    }
    if (newTags.length === 0) {
      window.alert('タグを入力してください。例: お気に入り, 要確認')
      return
    }

    setTagging(true)
    try {
      await Promise.all(
        targetIds.map(async (id) => {
          const video = videos.find((v) => v.id === id)
          const current = Array.isArray(video?.video_metadata?.tags)
            ? video!.video_metadata!.tags!
            : []
          await updateVideo(id, { tags: mergeTags(current, newTags) })
        }),
      )
      setTagInput('')
      setSelectedIds(new Set())
      onChanged()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`タグ更新に失敗しました: ${msg}`)
    } finally {
      setTagging(false)
    }
  }

  const startRename = (video: Video) => {
    setRenamingId(video.id)
    setRenameInput(video.title)
  }

  const cancelRename = () => {
    setRenamingId(null)
    setRenameInput('')
  }

  const handleRename = async (videoId: string) => {
    const title = renameInput.trim()
    if (!title) {
      window.alert('名前を入力してください。')
      return
    }

    setRenaming(true)
    try {
      await updateVideo(videoId, { title })
      cancelRename()
      onChanged()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      window.alert(`名前変更に失敗しました: ${msg}`)
    } finally {
      setRenaming(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <input
          type="text"
          placeholder="検索フィルタ（タイトル・タグ）"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
        <select
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">タグ: すべて</option>
          {allTags.map((tag) => (
            <option key={tag} value={tag}>
              タグ: {tag}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={toggleSelectAll}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
        >
          {allFilteredSelected ? '全選択解除' : '全選択'}
        </button>
      </div>

      <div className="flex flex-col md:flex-row gap-2 md:items-center">
        <input
          type="text"
          placeholder="タグ付け（カンマ区切り）"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
        <button
          type="button"
          onClick={handleApplyTag}
          disabled={tagging}
          className="px-3 py-2 border border-blue-200 text-blue-700 rounded-lg text-sm hover:bg-blue-50 disabled:opacity-50"
        >
          {tagging ? 'タグ更新中...' : `選択中(${selectedIds.size})へタグ付け`}
        </button>
      </div>

      {filtered.length === 0 ? (
        <p className="text-gray-400 text-center py-8">動画がありません</p>
      ) : (
        <ul className="space-y-2">
          {filtered.map((v) => (
            <li
              key={v.id}
              className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:border-yellow-400 transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedIds.has(v.id)}
                onChange={() => toggleSelect(v.id)}
                className="w-4 h-4"
                aria-label={`${v.title} を選択`}
              />
              <Link
                to={`/videos/${v.id}`}
                className="flex items-center gap-3 flex-1 min-w-0"
              >
                {thumbnailErrorMap[v.id] ? (
                  <div className="w-24 h-14 bg-gray-200 rounded shrink-0" />
                ) : (
                  <img
                    src={`${MEDIA_BASE}/${v.id}/thumbnail.jpg`}
                    alt={`${v.title} のサムネイル`}
                    className="w-24 h-14 object-cover rounded bg-gray-200 shrink-0"
                    onError={() =>
                      setThumbnailErrorMap((prev) => ({ ...prev, [v.id]: true }))
                    }
                  />
                )}
                <div>
                  <div className="font-medium text-gray-800">{v.title}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {v.duration_seconds != null
                      ? `${Math.round(v.duration_seconds)}秒`
                      : '不明'}
                    {v.created_at &&
                      ` · ${new Date(v.created_at).toLocaleString('ja-JP')}`}
                  </div>
                  {Array.isArray(v.video_metadata?.tags) &&
                    v.video_metadata.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {v.video_metadata.tags.map((tag) => (
                          <span
                            key={`${v.id}-${tag}`}
                            className="px-2 py-0.5 text-[10px] rounded-full bg-gray-100 text-gray-600"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                </div>
              </Link>
              {renamingId === v.id ? (
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={renameInput}
                    onChange={(e) => setRenameInput(e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded text-xs w-40"
                  />
                  <button
                    type="button"
                    onClick={() => handleRename(v.id)}
                    disabled={renaming}
                    className="px-2 py-1 text-xs rounded border border-green-200 text-green-700 hover:bg-green-50 disabled:opacity-50"
                  >
                    保存
                  </button>
                  <button
                    type="button"
                    onClick={cancelRename}
                    className="px-2 py-1 text-xs rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    取消
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => startRename(v)}
                  className="px-3 py-1.5 text-xs rounded border border-gray-200 text-gray-700 hover:bg-gray-50"
                >
                  名前変更
                </button>
              )}
              <button
                type="button"
                onClick={() => handleDelete(v)}
                disabled={deletingId === v.id}
                className="px-3 py-1.5 text-xs rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {deletingId === v.id ? '削除中...' : '削除'}
              </button>
              <span className="text-gray-400 text-sm">→</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
