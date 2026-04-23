import { api } from './client'

export interface Video {
  id: string
  title: string
  duration_seconds: number | null
  fps: number | null
  storage_path: string
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
