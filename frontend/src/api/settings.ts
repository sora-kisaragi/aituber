import { api } from './client'

export interface Setting {
  key: string
  value: string
  description: string | null
}

export async function getSettings(): Promise<Setting[]> {
  const { data } = await api.get<Setting[]>('/settings/')
  return data
}

export async function updateSettings(
  updates: { key: string; value: string }[],
): Promise<Setting[]> {
  const { data } = await api.put<Setting[]>('/settings/', updates)
  return data
}
