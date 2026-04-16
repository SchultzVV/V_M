import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import ProductGrid from '../components/ProductGrid'
import CategoryNav from '../components/CategoryNav'
import SearchBar from '../components/SearchBar'
import Pagination from '../components/Pagination'
import { Product, productService } from '../services/productService'

const PAGE_SIZE = 20

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
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sort, setSort] = useState<SortMode>('none')

  const tag = searchParams.get('tag') ?? ''
  const search = searchParams.get('search') ?? ''
  const page = Math.max(1, Number(searchParams.get('page') ?? 1))

  useEffect(() => {
    document.title = 'DEF — Catálogo'
  }, [])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        setIsLoading(true)
        const result = await productService.getPaged({
          tag: tag || undefined,
          search: search || undefined,
          page,
          limit: PAGE_SIZE,
        })
        if (!cancelled) {
          setProducts(result.products)
          setTotal(result.total)
          setPages(result.pages)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError('Falha ao carregar produtos. Verifique a conexão com o servidor.')
          console.error('Failed to load products:', err)
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [tag, search, page])

  function handlePage(newPage: number) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('page', String(newPage))
      return next
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const categoryLabel = tag
    ? { PET: 'PET', E: 'ELETRÔNICOS', CD: 'CASA', ME: 'MODA', geral: 'GERAL' }[tag] ?? tag.toUpperCase()
    : 'TODOS'

  return (
    <div className="bg-black-deep">
      {/* Hero Section */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-12 md:py-20">
          <div className="max-w-3xl">
            <h1 className="text-4xl md:text-5xl font-mono font-bold mb-4">
              <span className="text-neon-green">DEF</span>
              <span className="mx-2">.</span>
              <span className="block mt-2 text-gray-light">Equipamento para</span>
              <span className="text-neon-red">Ambientes Hostis</span>
            </h1>
            <p className="text-lg text-gray-text">
              Catálogo de sobrevivência pós-sistema. Funcional. Frio. Necessário.
            </p>
          </div>
        </div>
      </section>

      {/* Catalogue Section */}
      <section>
        <div className="container-def pt-6">
          {/* Category tabs */}
          <CategoryNav />

          {/* Search + count + sort row */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <SearchBar />
            <p className="font-mono text-sm text-gray-text">
              {isLoading ? (
                <span className="animate-pulse">carregando...</span>
              ) : (
                <>
                  <span className="text-gray-light font-bold">{total}</span> produtos
                  {categoryLabel !== 'TODOS' && (
                    <> · <span className="text-neon-green">{categoryLabel}</span></>
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
              ['price_asc',  '↓ MAIS BARATO',   'green'],
              ['discount',   '🔥 MAIOR PROMOÇÃO', 'red'],
              ['price_desc', '↑ MAIS CARO',      'gray'],
            ] as const).map(([mode, label, color]) => {
              const active = sort === mode
              const colorMap = {
                green: active ? 'bg-neon-green text-black border-neon-green shadow-[0_0_12px_theme(colors.neon-green)]' : 'text-neon-green border-neon-green/40 hover:border-neon-green hover:shadow-[0_0_8px_theme(colors.neon-green/50%)]',
                red:   active ? 'bg-neon-red text-black border-neon-red shadow-[0_0_12px_theme(colors.neon-red)]'     : 'text-neon-red border-neon-red/40 hover:border-neon-red hover:shadow-[0_0_8px_theme(colors.neon-red/50%)]',
                gray:  active ? 'bg-gray-light text-black border-gray-light shadow-[0_0_8px_#fff3]'                   : 'text-gray-text border-gray-steel hover:border-gray-light hover:text-gray-light',
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

          {/* Grid */}
          <ProductGrid products={sortProducts(products, sort)} isLoading={isLoading} error={error} />

          {/* Pagination */}
          {!isLoading && !error && (
            <Pagination page={page} pages={pages} total={total} onPage={handlePage} />
          )}
        </div>
      </section>
    </div>
  )
}
