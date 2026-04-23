import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getSettings } from '../api/settings'
import SettingsEditor from '../components/SettingsEditor'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { data: settings = [], isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
  })

  const refetch = () => queryClient.invalidateQueries({ queryKey: ['settings'] })

  if (isLoading) return <p className="text-gray-400">読み込み中...</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">設定</h1>
      <SettingsEditor settings={settings} onSaved={refetch} />
    </div>
  )
}
