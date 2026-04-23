import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import ProductGrid from '../components/ProductGrid'
import CatalogNav from '../components/CatalogNav'
import SearchBar from '../components/SearchBar'
import Pagination from '../components/Pagination'
import LandingProductCard from '../components/LandingProductCard'
import TagHeroGrid from '../components/TagHeroGrid'
import { Product, productService } from '../services/productService'
import { TAG_CONFIG } from '../data/subtags'

const PAGE_SIZE = 20
const TAG_ORDER = ['CD', 'ME', 'E', 'PET'] as const

type SortMode = 'none' | 'price_asc' | 'price_desc' | 'discount'

function sortProducts(products: Product[], mode: SortMode): Product[] {
  if (mode === 'none') return products
  return [...products].sort((a, b) => {
    if (mode === 'price_asc')  return a.price - b.price
    if (mode === 'price_desc') return b.price - a.price
    if (mode === 'discount') {
      const discA = a.old_price ? (a.old_price - a.price) / a.old_price : 0
      const discB = b.old_price ? (b.old_price - b.price) / b.old_price : 0
      return discB - discA
    }
    return 0
  })
}

export default function Home() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Catalog (filtered) state
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(false)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [sort, setSort] = useState<SortMode>('none')

  // Landing (homepage) state
  const [homepageData, setHomepageData] = useState<Record<string, Product[]>>({})
  const [isLoadingHome, setIsLoadingHome] = useState(true)
  const [homeError, setHomeError] = useState<string | null>(null)
  const [sliceIdx, setSliceIdx] = useState<Record<string, number>>({})
  const rotationPaused = useRef(false)

  const tag = searchParams.get('tag') ?? ''
  const search = searchParams.get('search') ?? ''
  const subtag = searchParams.get('subtag') ?? ''
  const page = Math.max(1, Number(searchParams.get('page') ?? 1))

  const isLanding = !tag && !subtag && !search

  useEffect(() => {
    document.title = 'DEF — Catálogo'
  }, [])

  // Landing: load 3 products per category from /api/homepage
  useEffect(() => {
    if (!isLanding) return
    let cancelled = false
    setIsLoadingHome(true)
    productService.getHomepage()
      .then(data => { if (!cancelled) { setHomepageData(data); setHomeError(null) } })
      .catch(() => { if (!cancelled) setHomeError('Falha ao carregar produtos.') })
      .finally(() => { if (!cancelled) setIsLoadingHome(false) })
    return () => { cancelled = true }
  }, [isLanding])

  // Reset rotation when data reloads
  useEffect(() => {
    setSliceIdx({})
  }, [homepageData])

  // Rotate products every 90s — pauses when mouse is over the landing section
  useEffect(() => {
    if (!isLanding || isLoadingHome || homeError) return
    const interval = setInterval(() => {
      if (rotationPaused.current) return
      setSliceIdx(prev => {
        const next = { ...prev }
        for (const tagKey of TAG_ORDER) {
          const items = homepageData[tagKey] ?? []
          const pageCount = Math.ceil(items.length / 3)
          if (pageCount > 1) {
            next[tagKey] = ((prev[tagKey] ?? 0) + 1) % pageCount
          }
        }
        return next
      })
    }, 90000)
    return () => clearInterval(interval)
  }, [isLanding, isLoadingHome, homeError, homepageData])

  function goLeft(tagKey: string) {
    const items = homepageData[tagKey] ?? []
    const pageCount = Math.ceil(items.length / 3)
    if (pageCount <= 1) return
    setSliceIdx(prev => ({ ...prev, [tagKey]: ((prev[tagKey] ?? 0) - 1 + pageCount) % pageCount }))
  }

  function goRight(tagKey: string) {
    const items = homepageData[tagKey] ?? []
    const pageCount = Math.ceil(items.length / 3)
    if (pageCount <= 1) return
    setSliceIdx(prev => ({ ...prev, [tagKey]: ((prev[tagKey] ?? 0) + 1) % pageCount }))
  }

  // Catalog: load full filtered list
  useEffect(() => {
    if (isLanding) return
    let cancelled = false
    const load = async () => {
      try {
        setIsLoadingCatalog(true)
        const result = await productService.getPaged({
          tag: tag || undefined,
          subtag: subtag || undefined,
          search: search || undefined,
          page,
          limit: PAGE_SIZE,
        })
        if (!cancelled) {
          setProducts(result.products)
          setTotal(result.total)
          setPages(result.pages)
          setCatalogError(null)
        }
      } catch {
        if (!cancelled) setCatalogError('Falha ao carregar produtos. Verifique a conexão com o servidor.')
      } finally {
        if (!cancelled) setIsLoadingCatalog(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [tag, subtag, search, page, isLanding])

  function handlePage(newPage: number) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('page', String(newPage))
      return next
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const tagConfig = tag ? TAG_CONFIG[tag] : null
  const categoryLabel = tagConfig?.label ?? 'TODOS'
  const subtagLabel = subtag
    ? tagConfig?.subtags.find(s => s.value === subtag)?.label ?? subtag
    : ''

  return (
    <div className="bg-black-deep">
      {/* Hero */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-6 md:py-10">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 mb-5">
            <h1 className="font-mono font-bold text-2xl md:text-3xl leading-none">
              <span className="text-neon-green">DEF</span>
              <span className="text-gray-text">.</span>
            </h1>
            <p className="font-mono text-xs text-gray-text tracking-widest uppercase">
              Equipamento para{' '}
              <span className="text-neon-red">Ambientes Hostis</span>
              {' '}—{' '}Funcional. Frio. Necessário.
            </p>
          </div>
          <SearchBar hero />
        </div>
      </section>

      {/* Main */}
      <section>
        <div className="container-def pt-6">
          {isLanding ? (
            <>
              <TagHeroGrid />
              <div className="border-t border-gray-steel/30 my-8" />
              {/* ─── Landing view: 3 products per category ─── */}
              <div
                className="flex flex-col gap-12 pb-16"
                onMouseEnter={() => { rotationPaused.current = true }}
                onMouseLeave={() => { rotationPaused.current = false }}
              >
              {TAG_ORDER.map(tagKey => {
                const config = TAG_CONFIG[tagKey]
                const items = homepageData[tagKey] ?? []
                return (
                  <div key={tagKey}>
                    {/* Section header */}
                    <div className="flex items-center justify-between mb-4 border-b-2 border-neon-green pb-2">
                      <button
                        onClick={() => setSearchParams({ tag: tagKey })}
                        className="font-mono text-sm font-bold tracking-[0.2em] uppercase text-neon-green hover:text-white transition-colors"
                      >
                        {config.label}
                      </button>
                      <button
                        onClick={() => setSearchParams({ tag: tagKey })}
                        className="font-mono text-xs text-gray-text hover:text-gray-light tracking-wider transition-colors"
                      >
                        ver todos →
                      </button>
                    </div>

                    {/* Horizontal slider */}
                    {isLoadingHome ? (
                      <div className="flex gap-4">
                        {[1, 2, 3].map(i => (
                          <div key={i} className="flex-1 h-[180px] bg-gray-steel animate-pulse" />
                        ))}
                      </div>
                    ) : homeError ? (
                      <p className="font-mono text-sm text-gray-text">{homeError}</p>
                    ) : items.length === 0 ? (
                      <p className="font-mono text-sm text-gray-text">Nenhum produto nesta categoria ainda.</p>
                    ) : (() => {
                      const pageCount = Math.ceil(items.length / 3)
                      const currentPage = sliceIdx[tagKey] ?? 0
                      return (
                        <div className="relative">
                          {/* Left arrow */}
                          {pageCount > 1 && (
                            <button
                              onClick={() => goLeft(tagKey)}
                              className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-black/80 hover:bg-neon-green hover:text-black text-neon-green px-3 py-4 transition-all font-mono font-bold text-xl leading-none select-none"
                              aria-label="Anterior"
                            >
                              ‹
                            </button>
                          )}

                          {/* Sliding track */}
                          <div className="overflow-hidden">
                            <div
                              className="flex transition-transform duration-500 ease-in-out"
                              style={{ transform: `translateX(-${currentPage * 100}%)` }}
                            >
                              {Array.from({ length: pageCount }, (_, pageIdx) => (
                                <div key={pageIdx} className="w-full flex-shrink-0 flex gap-4">
                                  {items.slice(pageIdx * 3, (pageIdx + 1) * 3).map(product => (
                                    <LandingProductCard key={product.id} product={product} />
                                  ))}
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Right arrow */}
                          {pageCount > 1 && (
                            <button
                              onClick={() => goRight(tagKey)}
                              className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-black/80 hover:bg-neon-green hover:text-black text-neon-green px-3 py-4 transition-all font-mono font-bold text-xl leading-none select-none"
                              aria-label="Próximo"
                            >
                              ›
                            </button>
                          )}

                          {/* Page counter */}
                          {pageCount > 1 && (
                            <div className="text-center font-mono text-[10px] text-gray-text mt-2 tracking-widest">
                              {currentPage + 1} / {pageCount}
                            </div>
                          )}
                        </div>
                      )
                    })()}

                    {/* Subtag quick-filter chips */}
                    <div className="flex flex-wrap gap-1.5 mt-4">
                      {config.subtags.map(sub => (
                        <button
                          key={sub.value}
                          onClick={() => setSearchParams({ tag: tagKey, subtag: sub.value })}
                          className="font-mono text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 border border-gray-steel/50 text-gray-text hover:border-neon-green hover:text-neon-green transition-all duration-150"
                        >
                          {sub.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
            </>
          ) : (
            /* ─── Catalog view: full filtered grid ─── */
            <>
              <CatalogNav />
              {/* Count row */}
              <div className="flex flex-wrap items-center gap-4 mb-4">
                <p className="font-mono text-sm text-gray-text">
                  {isLoadingCatalog ? (
                    <span className="animate-pulse">carregando...</span>
                  ) : (
                    <>
                      <span className="text-gray-light font-bold">{total}</span> produtos
                      {categoryLabel !== 'TODOS' && (
                        <> · <span className="text-neon-green">{categoryLabel}</span></>
                      )}
                      {subtagLabel && (
                        <> · <span className="text-neon-green/70">{subtagLabel}</span></>
                      )}
                      {search && (
                        <> · <span className="text-neon-red">"{search}"</span></>
                      )}
                    </>
                  )}
                </p>
              </div>

              {/* Sort buttons */}
              <div className="flex flex-wrap gap-2 mb-6">
                {([
                  ['price_asc',  '↓ MAIS BARATO',    'green'],
                  ['discount',   '🔥 MAIOR PROMOÇÃO', 'red'],
                  ['price_desc', '↑ MAIS CARO',       'gray'],
                ] as const).map(([mode, label, color]) => {
                  const active = sort === mode
                  const colorMap = {
                    green: active ? 'bg-neon-green text-black border-neon-green shadow-[0_0_12px_theme(colors.neon-green)]' : 'text-neon-green border-neon-green/40 hover:border-neon-green hover:shadow-[0_0_8px_theme(colors.neon-green/50%)]',
                    red:   active ? 'bg-neon-red text-black border-neon-red shadow-[0_0_12px_theme(colors.neon-red)]'       : 'text-neon-red border-neon-red/40 hover:border-neon-red hover:shadow-[0_0_8px_theme(colors.neon-red/50%)]',
                    gray:  active ? 'bg-gray-light text-black border-gray-light shadow-[0_0_8px_#fff3]'                     : 'text-gray-text border-gray-steel hover:border-gray-light hover:text-gray-light',
                  }
                  return (
                    <button
                      key={mode}
                      onClick={() => setSort(prev => prev === mode ? 'none' : mode)}
                      className={`font-mono text-xs font-bold tracking-widest px-4 py-2 border transition-all duration-200 ${colorMap[color]}`}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>

              <ProductGrid products={sortProducts(products, sort)} isLoading={isLoadingCatalog} error={catalogError} />

              {!isLoadingCatalog && !catalogError && (
                <Pagination page={page} pages={pages} total={total} onPage={handlePage} />
              )}
            </>
          )}
        </div>
      </section>
    </div>
  )
}

