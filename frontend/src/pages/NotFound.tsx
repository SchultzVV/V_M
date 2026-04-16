import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-black-deep flex flex-col items-center justify-center px-4">
      <div className="border border-neon-red p-8 max-w-md w-full text-center space-y-6">
        <div className="font-mono">
          <p className="text-gray-text text-xs tracking-widest mb-2">SISTEMA_DEF</p>
          <h1 className="text-neon-red text-6xl font-bold tracking-tighter">404</h1>
          <p className="text-gray-light text-xl font-bold tracking-widest mt-2">ERRO_NÃO_ENCONTRADO</p>
        </div>

        <div className="border-t border-gray-steel pt-4">
          <p className="font-mono text-sm text-gray-text">
            A página que você procura não existe ou foi removida.
          </p>
        </div>

        <Link
          to="/"
          className="block w-full bg-neon-red text-black-deep font-mono font-bold text-sm tracking-widest py-3 text-center hover:bg-neon-red-dim transition-colors"
        >
          ← INÍCIO
        </Link>
      </div>
    </div>
  )
}
