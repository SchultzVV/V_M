import { Outlet, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function AdminLayout() {
  const { logout } = useAuthStore()

  return (
    <div className="min-h-screen bg-black-deep flex">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-gray border-r border-gray-steel p-6">
        <Link to="/" className="block mb-8">
          <div className="text-xl font-mono font-bold">
            <span className="text-neon-green">DEF</span>
            <span className="text-neon-red">.</span>
          </div>
        </Link>

        <nav className="space-y-2">
          <Link
            to="/admin/dashboard"
            className="block px-4 py-2 rounded text-gray-light hover:bg-gray-steel hover:text-neon-green transition-colors"
          >
            Dashboard
          </Link>
        </nav>

        <button
          onClick={logout}
          className="mt-8 w-full px-4 py-2 rounded bg-neon-red text-black-deep font-bold hover:bg-neon-red-dim transition-colors"
        >
          Logout
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1">
        <div className="container-def py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
