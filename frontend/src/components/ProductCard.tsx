import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Product } from '../services/productService'
import { formatPrice, calculateDiscount, getImageUrl } from '../services/imageUtils'

interface ProductCardProps {
  product: Product
}

const PLATFORM_PATTERNS: [string, string][] = [
  ['mercado livre', 'ML'],
  ['mercadolivre', 'ML'],
  [' ml', 'ML'],
  ['shopee', 'Shopee'],
  ['amazon', 'Amazon'],
]

function getPlatformBadge(tags?: string[]): string | null {
  if (!tags) return null
  for (const tag of tags) {
    const lower = tag.toLowerCase()
    if (lower === 'ml') return 'ML'
    for (const [pattern, label] of PLATFORM_PATTERNS) {
      if (lower.includes(pattern)) return label
    }
  }
  return null
}

export default function ProductCard({ product }: ProductCardProps) {
  const navigate = useNavigate()
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const images = product.images && product.images.length > 0 ? product.images : [product.image].filter(Boolean) as string[]
  const hasMultipleImages = images.length > 1

  const hasDiscount = product.old_price && product.old_price > product.price
  const discountPercent = hasDiscount ? calculateDiscount(product.old_price!, product.price) : 0
  const imageUrl = getImageUrl(images[currentImageIndex])
  const platformBadge = getPlatformBadge(product.tags)

  const handleNextImage = (e: React.MouseEvent) => {
    e.stopPropagation()
    setCurrentImageIndex((prev) => (prev + 1) % images.length)
  }

  const handlePrevImage = (e: React.MouseEvent) => {
    e.stopPropagation()
    setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length)
  }

  const handleDotClick = (e: React.MouseEvent, index: number) => {
    e.stopPropagation()
    setCurrentImageIndex(index)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        setCurrentImageIndex((prev) => (prev + 1) % images.length)
      } else if (e.key === 'ArrowLeft') {
        setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [images.length])

  return (
    <div className="card-def group overflow-hidden h-full flex flex-col hover:shadow-neon-red transition-shadow duration-300">
      {/* Price Section - PRIMARY FOCUS */}
      <div className="bg-black-deep p-4 border-b-2 border-neon-green">
        <div className="border-l-2 border-neon-green pl-3">
          <div className="price-display text-neon-green">
            {formatPrice(product.price)}
          </div>
          {hasDiscount && (
            <>
              <div className="price-original">
                {formatPrice(product.old_price!)}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs font-mono bg-neon-green bg-opacity-20 text-neon-green px-2 py-1 rounded">
                  -{discountPercent}%
                </span>
                <span className="text-xs text-neon-green font-bold">
                  Economize {formatPrice(product.old_price! - product.price)}
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Image Section - SECONDARY with CAROUSEL */}
      <div className="relative flex-1 overflow-hidden bg-gray-steel group">
        <img
          src={imageUrl}
          alt={`${product.title} - Image ${currentImageIndex + 1}`}
          loading="lazy"
          decoding="async"
          className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
          onError={(e) => {
            e.currentTarget.src = '/def-placeholder.svg'
          }}
        />

        {/* Platform Badge */}
        {platformBadge && (
          <div className="absolute top-2 left-2 bg-black/80 text-neon-green font-mono text-[10px] px-2 py-0.5 z-10">
            {platformBadge}
          </div>
        )}

        {/* Navigation Arrows (only if multiple images) */}
        {hasMultipleImages && (
          <>
            <button
              onClick={handlePrevImage}
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-black bg-opacity-60 hover:bg-opacity-80 text-neon-green p-1.5 rounded transition-all z-10"
              aria-label="Previous image"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>

            <button
              onClick={handleNextImage}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-black bg-opacity-60 hover:bg-opacity-80 text-neon-green p-1.5 rounded transition-all z-10"
              aria-label="Next image"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>

            {/* Image Counter */}
            <div className="absolute bottom-2 left-2 bg-black bg-opacity-70 text-neon-green text-xs font-mono px-2 py-1 rounded">
              {currentImageIndex + 1}/{images.length}
            </div>

            {/* Dot Indicators */}
            <div className="absolute bottom-2 right-2 flex gap-1">
              {images.map((_, index) => (
                <button
                  key={index}
                  onClick={(e) => handleDotClick(e, index)}
                  className={`w-2 h-2 rounded-full transition-all ${
                    index === currentImageIndex
                      ? 'bg-neon-green w-3'
                      : 'bg-neon-green bg-opacity-40 hover:bg-opacity-70'
                  }`}
                  aria-label={`Go to image ${index + 1}`}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Product Info Section */}
      <div className="p-4 flex-1 flex flex-col">
        <h3 className="text-sm font-semibold text-gray-light line-clamp-2 mb-2 group-hover:text-neon-green transition-colors">
          {product.title}
        </h3>

        {/* Availability badge */}
        <div className="mt-auto">
          {product.available ? (
            <span className="inline-flex items-center gap-1.5 text-xs font-mono bg-neon-green bg-opacity-10 text-neon-green px-2 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
              Disponível
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-xs font-mono bg-neon-red bg-opacity-10 text-neon-red px-2 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-neon-red" />
              Indisponível
            </span>
          )}
        </div>

        {/* Category tag - optional */}
        {product.subcategory && (
          <p className="text-xs text-gray-text mt-2 capitalize">
            {product.subcategory}
          </p>
        )}
      </div>

      {/* CTA - Two Action Buttons */}
      <div className="p-4 border-t border-gray-steel flex gap-2">
        {product.link ? (
          <a
            href={product.link}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary flex-1 text-sm text-center"
            onClick={(e) => e.stopPropagation()}
          >
            COMPRAR
          </a>
        ) : (
          <button className="btn-primary flex-1 text-sm opacity-50 cursor-not-allowed" disabled>
            COMPRAR
          </button>
        )}
        <button
          className="btn-secondary flex-1 text-sm"
          onClick={() => navigate(`/produto/${product.id}`)}
        >
          DETALHES
        </button>
      </div>
    </div>
  )
}
