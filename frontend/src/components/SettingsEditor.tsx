import { useEffect, useState } from 'react'
import { Setting, updateSettings } from '../api/settings'
import { getTtsOptions, TtsOptions } from '../api/tts'

interface Props {
  settings: Setting[]
  onSaved: () => void
}

const NUMBER_KEYS = new Set(['segment_duration', 'event_grouping_window', 'game_audio_volume'])

const MODE_OPTIONS = [
  { label: 'voice_clone_profile（保存済みプロファイル）', value: 'voice_clone_profile' },
  { label: 'custom_voice（プリセット話者）', value: 'custom_voice' },
  { label: 'voice_design（パラメータ指定）', value: 'voice_design' },
]

export default function SettingsEditor({ settings, onSaved }: Props) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(settings.map((s) => [s.key, s.value])),
  )
  const [ttsOptions, setTtsOptions] = useState<TtsOptions>({
    speakers: [],
    profiles: [],
    languages: [],
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getTtsOptions().then(setTtsOptions).catch(() => {})
  }, [])

  const handleChange = (key: string, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }))

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

  const currentMode = values['tts_default_mode'] ?? ''

  const speakerOptions: string[] =
    currentMode === 'voice_clone_profile'
      ? ttsOptions.profiles
      : currentMode === 'custom_voice'
        ? ttsOptions.speakers
        : []

  const renderField = (s: Setting) => {
    if (s.key === 'tts_default_mode') {
      return (
        <select
          value={values[s.key] ?? ''}
          onChange={(e) => handleChange(s.key, e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 bg-white"
        >
          {MODE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      )
    }

    if (s.key === 'tts_default_speaker') {
      if (currentMode === 'voice_design') {
        return (
          <p className="text-xs text-gray-400 italic py-2">
            voice_design モードでは話者指定は不要です
          </p>
        )
      }
      if (speakerOptions.length > 0) {
        return (
          <select
            value={values[s.key] ?? ''}
            onChange={(e) => handleChange(s.key, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 bg-white"
          >
            <option value="">-- 選択してください --</option>
            {speakerOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        )
      }
      return (
        <input
          type="text"
          value={values[s.key] ?? ''}
          onChange={(e) => handleChange(s.key, e.target.value)}
          placeholder={currentMode === 'voice_clone_profile' ? 'default.pt' : '話者名'}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
      )
    }

    if (s.key === 'tts_default_language') {
      const langOptions = ttsOptions.languages.length > 0
        ? ttsOptions.languages
        : ['auto', 'japanese', 'english']
      return (
        <select
          value={values[s.key] ?? ''}
          onChange={(e) => handleChange(s.key, e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 bg-white"
        >
          {langOptions.map((lang) => (
            <option key={lang} value={lang}>{lang}</option>
          ))}
        </select>
      )
    }

    if (NUMBER_KEYS.has(s.key)) {
      return (
        <input
          type="number"
          step={s.key === 'game_audio_volume' ? '0.05' : '1'}
          min={s.key === 'game_audio_volume' ? '0' : undefined}
          max={s.key === 'game_audio_volume' ? '1' : undefined}
          value={values[s.key] ?? ''}
          onChange={(e) => handleChange(s.key, e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
      )
    }

    return (
      <input
        type="text"
        value={values[s.key] ?? ''}
        onChange={(e) => handleChange(s.key, e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
      />
    )
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
            {renderField(s)}
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
