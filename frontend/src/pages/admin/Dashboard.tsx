import { useState, useEffect } from 'react'
import { useAuthStore } from '../../stores/authStore'
import { productService, Product } from '../../services/productService'

export default function AdminDashboard() {
  const { user } = useAuthStore()
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState({
    total: 0,
    available: 0,
    unavailable: 0,
    withDiscount: 0,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await productService.getAll()
        setProducts(data)

        // Calculate stats
        const available = data.filter((p) => p.available).length
        const withDiscount = data.filter((p) => p.old_price && p.old_price > p.price).length

        setStats({
          total: data.length,
          available,
          unavailable: data.length - available,
          withDiscount,
        })
      } catch (error) {
        console.error('Failed to load dashboard data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [])

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-light mb-2">
          Bem-vindo, <span className="text-neon-green">{user?.username}</span>
        </h1>
        <p className="text-gray-text">Painel de administração DEF</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
        {/* Total Products */}
        <div className="card-def p-6">
          <div className="text-gray-text text-sm mb-2 font-mono">TOTAL</div>
          <div className="price-display text-neon-green">{stats.total}</div>
          <p className="text-xs text-gray-text mt-2">equipamentos no catálogo</p>
        </div>

        {/* Available */}
        <div className="card-def p-6">
          <div className="text-gray-text text-sm mb-2 font-mono">DISPONÍVEIS</div>
          <div className="price-display text-neon-green">{stats.available}</div>
          <p className="text-xs text-gray-text mt-2">prontos para venda</p>
        </div>

        {/* Unavailable */}
        <div className="card-def p-6">
          <div className="text-gray-text text-sm mb-2 font-mono">INDISPONÍVEIS</div>
          <div className="price-display text-neon-red">{stats.unavailable}</div>
          <p className="text-xs text-gray-text mt-2">fora de estoque</p>
        </div>

        {/* With Discount */}
        <div className="card-def p-6">
          <div className="text-gray-text text-sm mb-2 font-mono">OFERTA</div>
          <div className="price-display text-neon-green">{stats.withDiscount}</div>
          <p className="text-xs text-gray-text mt-2">com desconto ativo</p>
        </div>
      </div>

      {/* Recent Products */}
      <div className="card-def p-6">
        <h2 className="text-2xl font-bold text-gray-light mb-6">Equipamentos Recentes</h2>

        {isLoading ? (
          <div className="text-center py-8">
            <p className="text-gray-text">Carregando...</p>
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-text">Nenhum equipamento encontrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-steel text-gray-text font-mono">
                  <th className="text-left py-3 px-4">Título</th>
                  <th className="text-left py-3 px-4">Preço</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Desconto</th>
                </tr>
              </thead>
              <tbody>
                {products.slice(0, 10).map((product) => (
                  <tr
                    key={product.id}
                    className="border-b border-gray-steel hover:bg-dark-gray transition-colors"
                  >
                    <td className="py-3 px-4 text-gray-light truncate">
                      {product.title}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-neon-green font-mono font-bold">
                        R$ {product.price.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-xs font-mono px-2 py-1 rounded ${
                          product.available
                            ? 'bg-neon-green bg-opacity-10 text-neon-green'
                            : 'bg-neon-red bg-opacity-10 text-neon-red'
                        }`}
                      >
                        {product.available ? 'Disponível' : 'Indisponível'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {product.old_price && product.old_price > product.price ? (
                        <span className="text-neon-green font-bold text-xs">
                          -{Math.round(
                            ((product.old_price - product.price) / product.old_price) * 100
                          )}
                          %
                        </span>
                      ) : (
                        <span className="text-gray-text text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
        <button className="btn-primary py-3">
          Adicionar Novo Equipamento
        </button>
        <button className="btn-secondary py-3">
          Gerar Relatorio
        </button>
      </div>
    </div>
  )
}
