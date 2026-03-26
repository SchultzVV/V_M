import { useEffect, useState, ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

interface ProtectedRouteProps {
  children: ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { token, validateToken } = useAuthStore()
  const [isChecking, setIsChecking] = useState(true)
  const [isValid, setIsValid] = useState(false)

  useEffect(() => {
    const checkToken = async () => {
      if (!token) {
        setIsValid(false)
        setIsChecking(false)
        return
      }

      try {
        const valid = await validateToken()
        setIsValid(valid)
      } catch (error) {
        console.error('Token validation failed:', error)
        setIsValid(false)
      } finally {
        setIsChecking(false)
      }
    }

    checkToken()
  }, [token, validateToken])

  if (isChecking) {
    return (
      <div className="min-h-screen bg-black-deep flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse text-neon-green font-mono text-2xl mb-4">...</div>
          <p className="text-gray-text">Verificando autenticação...</p>
        </div>
      </div>
    )
  }

  if (!isValid) {
    return <Navigate to="/admin/login" replace />
  }

  return <>{children}</>
}
