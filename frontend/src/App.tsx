import { Link, Route, Routes, useLocation } from 'react-router-dom'
import VideoDetailPage from './pages/VideoDetailPage'
import VideosPage from './pages/VideosPage'
import SettingsPage from './pages/SettingsPage'

const NAV_LINKS = [
  { to: '/', label: '動画一覧' },
  { to: '/settings', label: '設定' },
]

export default function App() {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-gray-900 text-white px-6 py-3 flex items-center gap-6">
        <span className="font-bold text-lg tracking-wide">AITuber</span>
        {NAV_LINKS.map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            className={`text-sm hover:text-yellow-400 transition-colors ${pathname === to ? 'text-yellow-400' : 'text-gray-300'}`}
          >
            {label}
          </Link>
        ))}
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<VideosPage />} />
          <Route path="/videos/:id" element={<VideoDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
