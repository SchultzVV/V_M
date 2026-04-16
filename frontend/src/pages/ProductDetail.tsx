import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Product, productService } from '../services/productService'
import { formatPrice, calculateDiscount, getImageUrl } from '../services/imageUtils'

type Tab = 'ADQUIRIR' | 'FICHA_TECNICA'

const PLATFORM_PATTERNS: [string, string][] = [
  ['mercado livre', 'ML'],
  ['mercadolivre', 'ML'],
  ['shopee', 'Shopee'],
  ['amazon', 'Amazon'],
]

function getPlatform(tags?: string[]): string | null {
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

function truncateLink(url: string, max = 45): string {
  return url.length > max ? url.slice(0, max) + '...' : url
}

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('ADQUIRIR')
  const [currentImageIndex, setCurrentImageIndex] = useState(0)

  useEffect(() => {
    if (product) {
      document.title = `${product.title} — DEF`
      return () => { document.title = 'DEF — Catálogo' }
    }
  }, [product])

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
  const images = product.images && product.images.length > 0
    ? product.images
    : [product.image].filter(Boolean) as string[]
  const hasMultipleImages = images.length > 1
  const imageUrl = getImageUrl(images[currentImageIndex] ?? images[0])
  const platform = getPlatform(product.tags)

  const handlePrev = () => setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length)
  const handleNext = () => setCurrentImageIndex((prev) => (prev + 1) % images.length)

  return (
    <div className="bg-black-deep min-h-screen">
      {/* Top nav - Back button */}
      <div className="border-b border-gray-steel">
        <div className="container-def py-4">
          <Link to="/" className="btn-secondary inline-block text-sm">
            ← VOLTAR AO CATÁLOGO
          </Link>

          {/* Breadcrumb */}
          {(product.category || product.subcategory) && (
            <nav className="flex items-center gap-1 mt-3 text-xs font-mono text-gray-text" aria-label="Breadcrumb">
              <Link to="/" className="hover:text-neon-green transition-colors">INÍCIO</Link>
              {product.category && (
                <>
                  <span className="mx-1">›</span>
                  <Link to={`/?tag=${product.category}`} className="hover:text-neon-green transition-colors uppercase">
                    {product.category}
                  </Link>
                </>
              )}
              {product.subcategory && (
                <>
                  <span className="mx-1">›</span>
                  <span className="text-gray-light capitalize">{product.subcategory}</span>
                </>
              )}
            </nav>
          )}
        </div>
      </div>

      {/* INDISPONÍVEL banner */}
      {!product.available && (
        <div className="bg-neon-red text-black-deep font-mono font-bold text-sm tracking-widest py-3 text-center">
          ⚠ PRODUTO INDISPONÍVEL — Consulte outras opções no catálogo
        </div>
      )}

      {/* Product Detail Section */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-12">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">

            {/* Image with Carousel */}
            <div className="flex items-center justify-center">
              <div className="bg-dark-gray p-8 w-full aspect-square flex flex-col items-center justify-center relative overflow-hidden">
                <img
                  src={imageUrl}
                  alt={`${product.title} - ${currentImageIndex + 1}`}
                  loading="lazy"
                  decoding="async"
                  className="max-w-full max-h-full object-contain"
                  onError={(e) => {
                    e.currentTarget.src = '/def-placeholder.svg'
                  }}
                />

                {/* Discount Badge */}
                {hasDiscount && (
                  <div className="absolute top-4 right-4 bg-neon-red text-white font-mono font-bold text-2xl px-4 py-2">
                    -{discountPercent}%
                  </div>
                )}

                {/* Carousel Controls */}
                {hasMultipleImages && (
                  <>
                    <button
                      onClick={handlePrev}
                      className="absolute left-3 top-1/2 -translate-y-1/2 bg-black/70 hover:bg-black/90 text-neon-green p-2 transition-all z-10"
                      aria-label="Imagem anterior"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                    <button
                      onClick={handleNext}
                      className="absolute right-3 top-1/2 -translate-y-1/2 bg-black/70 hover:bg-black/90 text-neon-green p-2 transition-all z-10"
                      aria-label="Próxima imagem"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>

                    {/* Counter */}
                    <div className="absolute bottom-3 left-3 bg-black/70 text-neon-green text-xs font-mono px-2 py-1">
                      {currentImageIndex + 1}/{images.length}
                    </div>

                    {/* Dots */}
                    <div className="absolute bottom-3 right-3 flex gap-1">
                      {images.map((_, i) => (
                        <button
                          key={i}
                          onClick={() => setCurrentImageIndex(i)}
                          className={`h-2 transition-all ${
                            i === currentImageIndex
                              ? 'bg-neon-green w-4'
                              : 'bg-neon-green/40 hover:bg-neon-green/70 w-2'
                          }`}
                          aria-label={`Imagem ${i + 1}`}
                        />
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Info Panel with Tabs */}
            <div className="flex flex-col">
              {/* Product Title */}
              <h1 className="text-3xl md:text-4xl font-bold text-gray-light mb-6">
                {product.title}
              </h1>

              {/* Tab Headers */}
              <div className="flex border-b border-zinc-800 mb-6">
                {(['ADQUIRIR', 'FICHA_TECNICA'] as Tab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`font-mono uppercase tracking-widest text-sm px-4 py-3 transition-colors ${
                      activeTab === tab
                        ? 'border-b-2 border-neon-green text-neon-green -mb-px'
                        : 'text-zinc-500 hover:text-gray-light'
                    }`}
                  >
                    {tab === 'ADQUIRIR' ? 'ADQUIRIR' : 'FICHA TÉCNICA'}
                  </button>
                ))}
              </div>

              {/* Tab: ADQUIRIR */}
              {activeTab === 'ADQUIRIR' && (
                <div className="flex flex-col flex-1">
                  {/* Price */}
                  <div className="mb-8 pb-8 border-b border-gray-steel">
                    <div className="border-l-2 border-neon-green pl-4">
                      <div className="price-display text-neon-green mb-2">
                        {formatPrice(product.price)}
                      </div>
                      {hasDiscount && (
                        <>
                          <div className="price-original mb-4">
                            {formatPrice(product.old_price!)}
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-lg font-mono bg-neon-green bg-opacity-20 text-neon-green px-3 py-1 font-bold">
                              -{discountPercent}%
                            </span>
                            <span className="text-lg text-neon-green font-bold">
                              Economize {formatPrice(product.old_price! - product.price)}
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Availability */}
                  <div className="mb-6">
                    {product.available ? (
                      <span className="inline-flex items-center gap-2 text-sm font-mono text-neon-green">
                        <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                        Disponível para aquisição
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2 text-sm font-mono text-neon-red">
                        <span className="w-2 h-2 rounded-full bg-neon-red" />
                        Indisponível no momento
                      </span>
                    )}
                  </div>

                  {/* Description */}
                  {product.description && (
                    <div className="mb-8 pb-8 border-b border-gray-steel">
                      <p className="text-gray-text leading-relaxed">{product.description}</p>
                    </div>
                  )}

                  {/* Redirect notice + Action Button */}
                  <div className="mt-auto">
                    {product.link && product.available && (
                      <p className="text-xs font-mono text-gray-text mb-3">
                        ↗ Você será redirecionado para {platform === 'ML' ? 'o Mercado Livre' : platform || 'o site externo'}
                      </p>
                    )}
                    {product.link && product.available ? (
                      <a
                        href={product.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-primary inline-block w-full text-center"
                      >
                        COMPRAR
                      </a>
                    ) : (
                      <button className="btn-primary w-full opacity-50 cursor-not-allowed" disabled>
                        {product.available ? 'COMPRAR' : 'INDISPONÍVEL'}
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Tab: FICHA TÉCNICA */}
              {activeTab === 'FICHA_TECNICA' && (
                <div className="bg-gray-steel/30 border border-zinc-800">
                  <table className="w-full text-sm">
                    <tbody>
                      {platform && (
                        <tr className="border-b border-zinc-800">
                          <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3">Plataforma</td>
                          <td className="text-gray-light px-4 py-3">{platform}</td>
                        </tr>
                      )}
                      {product.category && (
                        <tr className="border-b border-zinc-800">
                          <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3">Categoria</td>
                          <td className="text-gray-light px-4 py-3 capitalize">{product.category}</td>
                        </tr>
                      )}
                      {product.subcategory && (
                        <tr className="border-b border-zinc-800">
                          <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3">Subcategoria</td>
                          <td className="text-gray-light px-4 py-3 capitalize">{product.subcategory}</td>
                        </tr>
                      )}
                      <tr className="border-b border-zinc-800">
                        <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3">Disponível</td>
                        <td className={`px-4 py-3 font-mono text-sm ${product.available ? 'text-neon-green' : 'text-neon-red'}`}>
                          {product.available ? 'Sim' : 'Não'}
                        </td>
                      </tr>
                      {product.tags && product.tags.length > 0 && (
                        <tr className="border-b border-zinc-800">
                          <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3 align-top">Tags</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {product.tags.map((tag) => (
                                <span key={tag} className="text-xs font-mono bg-gray-steel text-gray-light px-2 py-0.5">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                      <tr className="border-b border-zinc-800">
                        <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3">ID</td>
                        <td className="text-gray-light px-4 py-3 font-mono text-xs break-all">{product.id}</td>
                      </tr>
                      {product.link && (
                        <tr>
                          <td className="text-neon-green font-mono text-xs uppercase px-4 py-3 w-1/3">Link</td>
                          <td className="text-gray-light px-4 py-3 font-mono text-xs break-all">
                            {truncateLink(product.link)}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
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
