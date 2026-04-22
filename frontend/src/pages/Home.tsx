import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import ProductGrid from '../components/ProductGrid'
import ProductCard from '../components/ProductCard'
import CatalogNav from '../components/CatalogNav'
import SearchBar from '../components/SearchBar'
import Pagination from '../components/Pagination'
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
          {/* CatalogNav: 1-click to any category or subtag */}
          <CatalogNav />

          {isLanding ? (
            /* ─── Landing view: 3 products per category ─── */
            <div className="flex flex-col gap-12 pb-16">
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

                    {/* 3-product grid */}
                    {isLoadingHome ? (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[1, 2, 3].map(i => (
                          <div key={i} className="card-def animate-pulse">
                            <div className="bg-gray-steel h-48 mb-4" />
                            <div className="h-4 bg-gray-steel rounded mx-4 mb-2" />
                            <div className="h-4 bg-gray-steel rounded mx-4 w-2/3 mb-4" />
                          </div>
                        ))}
                      </div>
                    ) : homeError ? (
                      <p className="font-mono text-sm text-gray-text">{homeError}</p>
                    ) : items.length === 0 ? (
                      <p className="font-mono text-sm text-gray-text">Nenhum produto nesta categoria ainda.</p>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {items.map(product => (
                          <ProductCard key={product.id} product={product} />
                        ))}
                      </div>
                    )}

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
          ) : (
            /* ─── Catalog view: full filtered grid ─── */
            <>
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

