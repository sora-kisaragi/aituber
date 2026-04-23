import { useEffect, useRef, useState } from 'react'
import { createProgressSource } from '../api/sse'

export interface Progress {
  step: string
  pct: number
  message: string
}

export function useSSE(videoId: string | null) {
  const [progress, setProgress] = useState<Progress | null>(null)
  const [active, setActive] = useState(false)
  const sourceRef = useRef<EventSource | null>(null)

  const start = () => {
    if (!videoId || sourceRef.current) return
    setActive(true)
    setProgress(null)
    const src = createProgressSource(videoId)
    src.onmessage = (e: MessageEvent) => {
      const data = JSON.parse(e.data) as Progress
      setProgress(data)
      if (data.pct >= 100) {
        src.close()
        sourceRef.current = null
        setActive(false)
      }
    }
    src.onerror = () => {
      src.close()
      sourceRef.current = null
      setActive(false)
    }
    sourceRef.current = src
  }

  useEffect(() => {
    return () => {
      sourceRef.current?.close()
    }
  }, [])

  return { progress, active, start }
}
