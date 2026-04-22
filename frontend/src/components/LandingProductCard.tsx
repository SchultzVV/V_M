import { FC } from 'react'
import { useNavigate } from 'react-router-dom'
import { Product } from '../services/productService'
import { formatPrice, calculateDiscount, getImageUrl } from '../services/imageUtils'

interface LandingProductCardProps {
  product: Product
}

const LandingProductCard: FC<LandingProductCardProps> = ({ product }) => {
  const navigate = useNavigate()
  const hasDiscount = !!(product.old_price && product.old_price > product.price)
  const discountPercent = hasDiscount ? calculateDiscount(product.old_price!, product.price) : 0
  const imageUrl = getImageUrl(product.images?.[0] ?? product.image)

  return (
    <div
      className="flex flex-row h-[180px] md:h-[200px] bg-black-deep border border-gray-steel hover:border-neon-green transition-colors cursor-pointer overflow-hidden flex-1 min-w-0"
      onClick={() => navigate(`/produto/${product.id}`)}
    >
      {/* Image — 40% */}
      <div className="w-[40%] flex-shrink-0 overflow-hidden bg-gray-steel">
        <img
          src={imageUrl}
          alt={product.title}
          loading="lazy"
          decoding="async"
          className="w-full h-full object-cover"
          onError={(e) => { e.currentTarget.src = '/def-placeholder.svg' }}
        />
      </div>

      {/* Info — 60% */}
      <div className="flex flex-col p-3 gap-1.5 overflow-hidden flex-1 min-w-0">
        <h3 className="font-semibold text-gray-light text-sm leading-snug line-clamp-2">
          {product.title}
        </h3>

        <div className="mt-auto flex flex-col gap-1">
          <div className="text-lg font-mono font-bold text-neon-green leading-none">
            {formatPrice(product.price)}
          </div>
          {hasDiscount && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-mono bg-neon-red text-white px-1.5 py-0.5">
                -{discountPercent}%
              </span>
              <span className="text-xs line-through text-gray-text opacity-75">
                {formatPrice(product.old_price!)}
              </span>
            </div>
          )}
        </div>

        <button
          className="btn-primary text-xs w-full mt-1 py-1.5"
          onClick={(e) => { e.stopPropagation(); navigate(`/produto/${product.id}`) }}
        >
          VER PRODUTO
        </button>
      </div>
    </div>
  )
}

export default LandingProductCard
