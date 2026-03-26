import { useState, useEffect } from 'react'
import ProductGrid from '../components/ProductGrid'
import { Product, productService } from '../services/productService'

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setIsLoading(true)
        const data = await productService.getAll()
        console.log('✅ Produtos carregados:', data.length, 'items')
        console.log('Primeiro produto:', data[0])
        setProducts(data)
        setError(null)
      } catch (err) {
        setError('Falha ao carregar produtos. Verifique a conexão com o servidor.')
        console.error('Failed to load products:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadProducts()
  }, [])

  return (
    <div className="bg-black-deep">
      {/* Hero Section */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-16 md:py-24">
          <div className="max-w-3xl">
            <h1 className="text-4xl md:text-5xl font-mono font-bold mb-4">
              <span className="text-neon-green">DEF</span>
              <span className="mx-2">.</span>
              <span className="block mt-2 text-gray-light">Equipamento para</span>
              <span className="text-neon-red">Ambientes Hostis</span>
            </h1>
            <p className="text-lg text-gray-text mb-6">
              Catálogo de sobrevivência pós-sistema. Não vendemos coisas. Distribuímos equipamento.
            </p>
            <p className="text-sm text-gray-text">
              Para quem vive depois do sistema. Funcional. Frio. Necessário.
            </p>
          </div>
        </div>
      </section>

      {/* Filter/Search Section - Optional */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-6 flex items-center justify-between">
          <div>
            <h2 className="font-mono font-bold text-gray-light">
              Catálogo Completo
            </h2>
            <p className="text-sm text-gray-text">
              {products.length} equipamentos disponíveis
            </p>
          </div>
          {/* Future: Add filter/sort controls here */}
        </div>
      </section>

      {/* Products Grid Section */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-12">
          <ProductGrid products={products} isLoading={isLoading} error={error} />
        </div>
      </section>

      {/* Call to Action Section */}
      <section className="border-b border-gray-steel">
        <div className="container-def py-16 text-center">
          <h2 className="text-2xl md:text-3xl font-mono font-bold mb-4">
            Procurando Algo Específico?
          </h2>
          <p className="text-gray-text mb-8 max-w-2xl mx-auto">
            Nosso catálogo é constantemente atualizado com novo equipamento funcional
            designado para ambientes hostis.
          </p>
          <button className="btn-primary">
            Explorar Categorias
          </button>
        </div>
      </section>
    </div>
  )
}
