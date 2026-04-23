import { useState } from 'react'
import { Setting, updateSettings } from '../api/settings'

interface Props {
  settings: Setting[]
  onSaved: () => void
}

export default function SettingsEditor({ settings, onSaved }: Props) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(settings.map((s) => [s.key, s.value])),
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const updates = Object.entries(values).map(([key, value]) => ({ key, value }))
      await updateSettings(updates)
      setSaved(true)
      onSaved()
    } catch {
      setError('保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
      <div className="grid gap-4">
        {settings.map((s) => (
          <div key={s.key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{s.key}</label>
            {s.description && (
              <p className="text-xs text-gray-400 mb-1">{s.description}</p>
            )}
            <input
              type="text"
              value={values[s.key] ?? ''}
              onChange={(e) =>
                setValues((prev) => ({ ...prev, [s.key]: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors disabled:opacity-50"
        >
          {saving ? '保存中...' : '設定を保存'}
        </button>
        {saved && <span className="text-green-600 text-sm">保存しました</span>}
        {error && <span className="text-red-500 text-sm">{error}</span>}
      </div>
    </div>
  )
}
