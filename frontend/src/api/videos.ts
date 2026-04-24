import { api } from './client'

export interface VideoTagStatus {
  rule: string
  llm: string
  llm_error: string | null
}

export interface VideoMetadata {
  tags?: string[]
  tags_manual?: string[]
  tags_auto_rule?: string[]
  tags_auto_llm?: string[]
  tags_suggested_llm?: string[]
  tags_effective?: string[]
  tag_status?: VideoTagStatus
  [key: string]: unknown
}

export interface Video {
  id: string
  title: string
  duration_seconds: number | null
  fps: number | null
  storage_path: string
  video_metadata: VideoMetadata | null
  created_at: string | null
}

export async function listVideos(): Promise<Video[]> {
  const { data } = await api.get<Video[]>('/videos/')
  return data
}

export async function getVideo(id: string): Promise<Video> {
  const { data } = await api.get<Video>(`/videos/${id}`)
  return data
}

export async function deleteVideo(id: string): Promise<void> {
  await api.delete(`/videos/${id}`)
}

export interface VideoUpdatePayload {
  title?: string
  tags?: string[]
  tags_manual?: string[]
}

export async function updateVideo(
  id: string,
  payload: VideoUpdatePayload,
): Promise<Video> {
  const { data } = await api.patch<Video>(`/videos/${id}`, payload)
  return data
}

export async function uploadVideo(
  file: File,
  title: string,
  onProgress?: (pct: number) => void,
): Promise<Video> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<Video>('/videos/', form, {
    params: { title },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function processVideo(id: string): Promise<void> {
  await api.post(`/videos/${id}/process`)
}

export async function composeVideo(id: string): Promise<void> {
  await api.post(`/videos/${id}/compose`)
}

export function exportVideoUrl(id: string): string {
  const base = import.meta.env.VITE_API_URL ?? '/api'
  return `${base}/videos/${id}/export`
}

export interface TimelineItem {
  start_time: number
  end_time: number
  style: string
  text: string
  commentary_id: string
  audio_rel: string | null
}

export interface VideoTimeline {
  input_rel: string | null
  items: TimelineItem[]
}

export async function getTimeline(id: string): Promise<VideoTimeline> {
  const { data } = await api.get<VideoTimeline>(`/videos/${id}/timeline`)
  return data
}

export interface VideoTagInfo {
  tags_manual: string[]
  tags_auto_rule: string[]
  tags_auto_llm: string[]
  tags_suggested_llm: string[]
  tags_effective: string[]
  source_by_tag: Record<string, string>
  tag_status: VideoTagStatus
}

export async function getVideoTags(id: string): Promise<VideoTagInfo> {
  const { data } = await api.get<VideoTagInfo>(`/videos/${id}/tags`)
  return data
}

export async function refreshVideoTags(id: string): Promise<VideoTagInfo> {
  const { data } = await api.post<VideoTagInfo>(`/videos/${id}/tags/refresh`)
  return data
}

export async function refreshVideoRuleTags(id: string): Promise<VideoTagInfo> {
  const { data } = await api.post<VideoTagInfo>(`/videos/${id}/tags/rule:refresh`)
  return data
}

export async function refreshVideoLlmTags(id: string): Promise<VideoTagInfo> {
  const { data } = await api.post<VideoTagInfo>(`/videos/${id}/tags/llm:refresh`)
  return data
}
