import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function AdminLogin() {
  const navigate = useNavigate()
  const { login, error: authError, isLoading } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (!username.trim() || !password.trim()) {
      setLocalError('Username e password são obrigatórios')
      return
    }

    try {
      await login(username, password)
      navigate('/admin/dashboard')
    } catch (err) {
      console.error('Login failed:', err)
    }
  }

  const error = authError || localError

  return (
    <div className="min-h-screen bg-black-deep flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-12">
          <Link to="/" className="inline-block">
            <div className="text-4xl font-mono font-bold">
              <span className="text-neon-green">DEF</span>
              <span className="text-neon-red">.</span>
            </div>
          </Link>
          <p className="text-gray-text text-sm mt-4">Acesso Administrativo</p>
        </div>

        {/* Form Card */}
        <div className="card-def p-8 border-2 border-gray-steel">
          <h1 className="text-2xl font-bold text-gray-light mb-6">Admin Login</h1>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block text-sm font-semibold text-gray-light mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="seu_usuario"
                disabled={isLoading}
                className="w-full px-4 py-2 bg-black-deep border border-gray-steel rounded text-gray-light placeholder-gray-text focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green disabled:opacity-50"
              />
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-gray-light mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                disabled={isLoading}
                className="w-full px-4 py-2 bg-black-deep border border-gray-steel rounded text-gray-light placeholder-gray-text focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green disabled:opacity-50"
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-neon-red bg-opacity-10 border border-neon-red rounded">
                <p className="text-sm text-neon-red">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Entrando...
                </>
              ) : (
                'Entrar'
              )}
            </button>
          </form>

          {/* Back to Home */}
          <div className="mt-6 text-center">
            <Link
              to="/"
              className="text-sm text-gray-text hover:text-neon-green transition-colors"
            >
              ← Voltar ao Catálogo
            </Link>
          </div>
        </div>

        {/* Footer Note */}
        <div className="text-center mt-8">
          <p className="text-xs text-gray-text">
            Este é o painel administrativo da DEF.<br />
            Equipamento restrito.
          </p>
        </div>
      </div>
    </div>
  )
}
