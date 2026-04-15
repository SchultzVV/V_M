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
  
  // If starts with /media/, serve via nginx proxy (nginx → minio:9000 internally)
  // This avoids mixed-content (HTTPS page → HTTP) and works via Cloudflare tunnel
  if (pathWithoutToken.startsWith('/media/')) {
    console.log(`[getImageUrl] MinIO path via nginx proxy: ${pathWithoutToken}`)
    return pathWithoutToken
  }

  // Fallback: treat as a /media/ relative path through nginx proxy
  const proxiedUrl = `/media${pathWithoutToken.startsWith('/') ? '' : '/'}${pathWithoutToken}`
  console.log(`[getImageUrl] Fallback proxied URL: ${proxiedUrl}`)
  return proxiedUrl
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
