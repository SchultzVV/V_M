import api from './api'

export interface Product {
  id: string
  title: string
  price: number
  old_price?: number
  images: string[]
  image?: string
  category?: string
  subcategory?: string
  link?: string
  description?: string
  available: boolean
  tags?: string[]
  updated_at?: string
}

export interface ApiProduct {
  id: string
  title: string
  price: string
  oldPrice?: string
  images?: string[]
  category?: string
  subcategory?: string
  link?: string
  description?: string
  disponivel: boolean
  tags?: string[]
  updated_at?: string
}

export interface PagedResponse {
  items: ApiProduct[]
  total: number
  page: number
  pages: number
  limit: number
}

export interface ProductsPage {
  products: Product[]
  total: number
  page: number
  pages: number
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
}

// Conversor de preço: "R$ 1.234,56" ou "R$ 1234.56" -> 1234.56
const parsePrice = (priceStr: string): number => {
  try {
    if (!priceStr) {
      console.warn('[parsePrice] Empty price string')
      return 0
    }
    
    const cleaned = priceStr.replace(/R\$\s*/g, '').trim()
    
    if (cleaned.includes(',')) {
      // Formato brasileiro: "1.234,56" -> remove pontos, substitui vírgula por ponto
      const normalized = cleaned.replace(/\./g, '').replace(',', '.')
      const result = parseFloat(normalized) || 0
      return result
    } else {
      // Formato US ou sem separadores: "1234.56" ou "1234" -> usa como está
      const parts = cleaned.split('.')
      if (parts.length > 2) {
        // Tem múltiplos pontos, último é decimal, anteriores são milhar
        return parseFloat(parts.slice(0, -1).join('') + '.' + parts[parts.length - 1]) || 0
      }
      // Sem múltiplos pontos, usar como está
      return parseFloat(cleaned) || 0
    }
  } catch (err) {
    console.error(`[parsePrice] ERROR parsing "${priceStr}":`, err)
    return 0
  }
}

// Transforma produto da API para o formato esperado pelo frontend
const transformProduct = (apiProduct: ApiProduct): Product => {
  try {
    console.log(`[transformProduct] Processing: ${apiProduct.title?.substring(0, 30)}...`)
    
    if (!apiProduct.id) {
      console.error('[transformProduct] ❌ Missing product id:', apiProduct)
      throw new Error('Product missing ID')
    }
    
    const imageUrls = apiProduct.images || []
    console.log(`[transformProduct]   📸 ${imageUrls.length} images found`)
    
    const transformed: Product = {
      id: apiProduct.id,
      title: apiProduct.title || 'Produto sem título',
      price: parsePrice(apiProduct.price),
      old_price: apiProduct.oldPrice ? parsePrice(apiProduct.oldPrice) : undefined,
      images: imageUrls,
      image: imageUrls?.[0],
      category: apiProduct.category,
      subcategory: apiProduct.subcategory,
      link: apiProduct.link,
      description: apiProduct.description,
      available: apiProduct.disponivel,
      tags: apiProduct.tags,
      updated_at: apiProduct.updated_at,
    }
    
    console.log(`[transformProduct]   ✅ ${transformed.title} @ R$ ${transformed.price.toFixed(2)}`)
    return transformed
  } catch (err) {
    console.error('[transformProduct] ❌ ERROR:', apiProduct, err)
    throw err
  }
}

export const productService = {
  async getAll(params?: { tag?: string; subtag?: string; search?: string; limit?: number }): Promise<Product[]> {
    try {
      console.log('🔄 [productService] Fetching /api/products...')
      const response = await api.get<PagedResponse>('/api/products', { params: { ...params, limit: params?.limit ?? 100 } })
      const items = response.data.items
      console.log(`✅ [productService] Received ${items.length} raw products (total: ${response.data.total})`)

      const transformed = items.map((product, index) => {
        try {
          return transformProduct(product)
        } catch (err) {
          console.error(`❌ [productService] Error transforming product ${index}:`, product, err)
          throw err
        }
      })
      console.log(`✅ [productService] Transformed ${transformed.length} products successfully`)
      return transformed
    } catch (error) {
      console.error('❌ [productService] Error fetching products:', error)
      if (error instanceof Error) {
        console.error('   Error message:', error.message)
        console.error('   Error cause:', (error as any).cause)
      }
      throw error
    }
  },

  async getPaged(params?: { tag?: string; subtag?: string; search?: string; page?: number; limit?: number }): Promise<ProductsPage> {
    try {
      const response = await api.get<PagedResponse>('/api/products', { params })
      return {
        products: response.data.items.map(transformProduct),
        total: response.data.total,
        page: response.data.page,
        pages: response.data.pages,
      }
    } catch (error) {
      console.error('❌ [productService] Error fetching paged products:', error)
      throw error
    }
  },

  async getHomepage(): Promise<Record<string, Product[]>> {
    try {
      const response = await api.get<Record<string, ApiProduct[]>>('/api/homepage')
      const result: Record<string, Product[]> = {}
      for (const [tag, items] of Object.entries(response.data)) {
        result[tag] = items.map(transformProduct)
      }
      return result
    } catch (error) {
      console.error('❌ [productService] Error fetching homepage data:', error)
      throw error
    }
  },

  async getById(id: string): Promise<Product> {
    try {
      const response = await api.get<ApiProduct>(`/api/products/${id}`)
      return transformProduct(response.data)
    } catch (error) {
      console.error(`Error fetching product ${id}:`, error)
      throw error
    }
  },

  async create(product: Partial<Product>): Promise<Product> {
    try {
      const response = await api.post<ApiProduct>('/api/products', product)
      return transformProduct(response.data)
    } catch (error) {
      console.error('Error creating product:', error)
      throw error
    }
  },

  async update(id: string, product: Partial<Product>): Promise<Product> {
    try {
      const response = await api.put<ApiProduct>(`/api/products/${id}`, product)
      return transformProduct(response.data)
    } catch (error) {
      console.error(`Error updating product ${id}:`, error)
      throw error
    }
  },

  async delete(id: string): Promise<void> {
    try {
      await api.delete(`/api/products/${id}`)
    } catch (error) {
      console.error(`Error deleting product ${id}:`, error)
      throw error
    }
  },
}
