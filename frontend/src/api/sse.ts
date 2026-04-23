const SSE_BASE = import.meta.env.VITE_API_URL ?? '/api'

export function createProgressSource(videoId: string): EventSource {
  return new EventSource(`${SSE_BASE}/videos/${videoId}/progress/stream`)
}
