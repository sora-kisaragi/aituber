import { api } from './client'

export interface TtsOptions {
  speakers: string[]
  profiles: string[]
  languages: string[]
}

export async function getTtsOptions(): Promise<TtsOptions> {
  const [s, p, l] = await Promise.allSettled([
    api.get<{ speakers: string[] }>('/tts/speakers'),
    api.get<{ profiles: string[] }>('/tts/profiles'),
    api.get<{ languages: string[] }>('/tts/languages'),
  ])
  return {
    speakers: s.status === 'fulfilled' ? (s.value.data.speakers ?? []) : [],
    profiles: p.status === 'fulfilled' ? (p.value.data.profiles ?? []) : [],
    languages: l.status === 'fulfilled' ? (l.value.data.languages ?? []) : [],
  }
}
