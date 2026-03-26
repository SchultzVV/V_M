export const getImageUrl = (imagePath: string | undefined, fallback: string = '/def-placeholder.svg'): string => {
  if (!imagePath) return fallback

  console.log(`[getImageUrl] Converting: "${imagePath}"`)

  // If it's already a full URL (http/https), return it
  if (imagePath.startsWith('http')) {
    console.log(`[getImageUrl] Already full URL, returning as-is`)
    return imagePath
  }

  // Remove token query param se existir
  const pathWithoutToken = imagePath.split('?')[0]
  
  // If starts with /media/, it's stored in MinIO
  if (pathWithoutToken.startsWith('/media/')) {
    // Path format: /media/{bucket}/{product-name}/{image}.jpg
    // MinIO structure: http://localhost:9000/{bucket}/{path}
    // We need to extract bucket and rest of path
    const parts = pathWithoutToken.split('/').filter(p => p) // Remove empty strings
    if (parts.length >= 3 && parts[0] === 'media') {
      const bucket = parts[1] // e.g., 'mercadolivre'
      const restPath = parts.slice(2).join('/') // e.g., 'produto/image.jpg'
      const minioUrl = `http://localhost:9000/${bucket}/${restPath}`
      console.log(`[getImageUrl] Converted /media path → MinIO: ${minioUrl}`)
      return minioUrl
    }
  }

  // Fallback: try to construct MinIO URL directly
  const minioUrl = `http://localhost:9000${pathWithoutToken}`
  console.log(`[getImageUrl] Fallback MinIO URL: ${minioUrl}`)
  return minioUrl
}

export const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(price)
}

export const calculateDiscount = (originalPrice: number, currentPrice: number): number => {
  return Math.round(((originalPrice - currentPrice) / originalPrice) * 100)
}

export const getSavingsAmount = (originalPrice: number, currentPrice: number): number => {
  return originalPrice - currentPrice
}
