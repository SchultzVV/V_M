import ProductCard from './ProductCard'
import { Product } from '../services/productService'

interface ProductGridProps {
  products: Product[]
  isLoading?: boolean
  error?: string | null
}

export default function ProductGrid({ products, isLoading = false, error = null }: ProductGridProps) {
  if (isLoading) {
    return (
      <div className="grid-def">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="card-def animate-pulse h-96">
            <div className="bg-gray-steel h-32 mb-4"></div>
            <div className="h-4 bg-gray-steel rounded mb-2"></div>
            <div className="h-4 bg-gray-steel rounded w-2/3"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-neon-red mb-2">⚠️</div>
        <p className="text-gray-text mb-4">Erro ao carregar produtos</p>
        <p className="text-sm text-gray-text">{error}</p>
      </div>
    )
  }

  if (!products || products.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-text mb-4">Nenhum equipamento encontrado</p>
        <p className="text-sm text-gray-text">Tente outra busca ou categoria</p>
      </div>
    )
  }

  return (
    <div className="grid-def">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  )
}
