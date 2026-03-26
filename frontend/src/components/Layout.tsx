import { Outlet, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function Layout() {
  const { user, logout } = useAuthStore()

  return (
    <div className="min-h-screen bg-black-deep flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-steel bg-dark-gray sticky top-0 z-50">
        <div className="container-def py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="text-2xl font-mono font-bold">
              <span className="text-neon-green">DEF</span>
              <span className="text-neon-red">.</span>
            </div>
            <div className="text-xs text-gray-text uppercase tracking-wider">
              Catálogo de Equipamento
            </div>
          </Link>

          <nav className="flex items-center gap-6">
            {user ? (
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-text">{user.username}</span>
                <Link
                  to="/admin/dashboard"
                  className="text-sm hover:text-neon-green transition-colors"
                >
                  Admin
                </Link>
                <button
                  onClick={logout}
                  className="text-sm hover:text-neon-red transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <Link
                to="/admin/login"
                className="text-sm hover:text-neon-green transition-colors"
              >
                Admin
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-steel bg-dark-gray">
        <div className="container-def py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="font-mono font-bold text-neon-green mb-4">DEF</h3>
              <p className="text-sm text-gray-text">
                Catálogo de sobrevivência pós-sistema. Equipamento funcional para ambientes hostis.
              </p>
            </div>
            <div>
              <h4 className="font-bold mb-4">Categorias</h4>
              <ul className="space-y-2 text-sm text-gray-text">
                <li><a href="#" className="hover:text-neon-green transition">Casa & Decoração</a></li>
                <li><a href="#" className="hover:text-neon-green transition">Eletrônicos</a></li>
                <li><a href="#" className="hover:text-neon-green transition">Moda & Estilo</a></li>
                <li><a href="#" className="hover:text-neon-green transition">PetShop</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-gray-text">
                <li><a href="#" className="hover:text-neon-green transition">Privacidade</a></li>
                <li><a href="#" className="hover:text-neon-green transition">Termos</a></li>
                <li><a href="#" className="hover:text-neon-green transition">Contato</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-steel mt-8 pt-8 text-center text-sm text-gray-text">
            <p>© 2026 DEF. Equipamento distribuído para quem vive depois do sistema.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
