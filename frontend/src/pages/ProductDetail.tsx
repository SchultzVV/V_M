import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Product, productService } from '../services/productService'
import { formatPrice, calculateDiscount, getImageUrl } from '../services/imageUtils'

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) {
      navigate('/')
      return
    }

    const loadProduct = async () => {
      try {
        setIsLoading(true)
        const data = await productService.getById(id)
        setProduct(data)
        setError(null)
      } catch (err) {
        setError('Equipamento não encontrado')
        console.error('Failed to load product:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadProduct()
  }, [id, navigate])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black-deep flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse text-neon-green font-mono text-2xl mb-4">...</div>
          <p className="text-gray-text">Carregando equipamento...</p>
        </div>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-black-deep flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-4xl text-neon-red mb-4">✕</div>
          <h1 className="text-2xl font-bold text-gray-light mb-2">Equipamento Não Encontrado</h1>
          <p className="text-gray-text mb-6">{error}</p>
          <Link to="/" className="btn-primary inline-block">
            Voltar ao Catálogo
          </Link>
        </div>
      </div>
    )
  }

  const hasDiscount = product.old_price && product.old_price > product.price
  const discountPercent = hasDiscount ? calculateDiscount(product.old_price!, product.price) : 0
  const imageUrl = getImageUrl(product.image)

  return (
    <div className="bg-black-deep min-h-screen">
      {/* Breadcrumb */}
      <div className="border-b border-gray-steel">
        <div className="container-def py-4">
          <Link to="/" className="text-sm text-neon-green hover:text-neon-green-dim transition">
            ← Voltar
          </Link>
        </div>
      </div>

      {/* Product Detail Section */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-12">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            {/* Image */}
            <div className="flex items-center justify-center">
              <div className="bg-dark-gray rounded-lg p-8 w-full aspect-square flex items-center justify-center">
                <img
                  src={imageUrl}
                  alt={product.title}
                  loading="lazy"
                  decoding="async"
                  className="max-w-full max-h-full object-contain"
                  onError={(e) => {
                    e.currentTarget.src = '/def-placeholder.svg'
                  }}
                />
              </div>
            </div>

            {/* Info */}
            <div className="flex flex-col justify-start">
              {/* Price - Big Focus */}
              <div className="mb-8 pb-8 border-b border-gray-steel">
                <div className="price-display text-neon-green mb-2">
                  {formatPrice(product.price)}
                </div>
                {hasDiscount && (
                  <>
                    <div className="price-original mb-4">
                      {formatPrice(product.old_price!)}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-mono bg-neon-green bg-opacity-20 text-neon-green px-3 py-1 rounded font-bold">
                        -{discountPercent}%
                      </span>
                      <span className="text-lg text-neon-green font-bold">
                        Economize {formatPrice(product.old_price! - product.price)}
                      </span>
                    </div>
                  </>
                )}
              </div>

              {/* Title */}
              <h1 className="text-3xl md:text-4xl font-bold text-gray-light mb-4">
                {product.title}
              </h1>

              {/* Category & Meta */}
              <div className="mb-6 space-y-2">
                {product.category && (
                  <p className="text-sm text-gray-text capitalize">
                    <span className="text-neon-green">Categoria:</span> {product.category}
                  </p>
                )}
                {product.subcategory && (
                  <p className="text-sm text-gray-text capitalize">
                    <span className="text-neon-green">Subcategoria:</span> {product.subcategory}
                  </p>
                )}
                <p className="text-sm">
                  <span className={product.available ? 'text-neon-green' : 'text-neon-red'}>
                    {product.available ? '● Disponível' : '● Indisponível'}
                  </span>
                </p>
              </div>

              {/* Description */}
              {product.description && (
                <div className="mb-8 pb-8 border-b border-gray-steel">
                  <h2 className="text-lg font-bold text-gray-light mb-4">Descrição</h2>
                  <p className="text-gray-text leading-relaxed">{product.description}</p>
                </div>
              )}

              {/* Tags */}
              {product.tags && product.tags.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold text-gray-light mb-3">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {product.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs font-mono bg-gray-steel text-gray-light px-3 py-1 rounded hover:bg-neon-green hover:text-black-deep transition-colors cursor-pointer"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4 mt-auto">
                <button className="btn-primary flex-1">
                  Equipar Agora
                </button>
                {product.link && (
                  <a
                    href={product.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary flex-1"
                  >
                    Ver Fonte
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Related Products - Optional */}
      <section className="container-def py-12">
        <h2 className="text-2xl font-bold text-gray-light mb-8">Equipamento Similar</h2>
        <p className="text-gray-text">Em desenvolvimento...</p>
      </section>
    </div>
  )
}
