# services/seo_service.py

import json
from typing import Dict, List, Optional
from datetime import datetime

class SEOService:
    """Serviço para gerenciar SEO, meta tags e structured data"""
    
    def __init__(self, site_name: str = "DEF", site_url: str = "https://seusite.com"):
        self.site_name = site_name
        self.site_url = site_url.rstrip('/')
    
    def generate_meta_tags(self, 
                          title: str, 
                          description: str,
                          image: Optional[str] = None,
                          url: Optional[str] = None,
                          keywords: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Gera meta tags otimizadas para SEO
        
        Args:
            title: Título da página (50-60 caracteres)
            description: Descrição da página (150-160 caracteres)
            image: URL da imagem para preview
            url: URL da página
            keywords: Lista de palavras-chave
        
        Returns:
            Dicionário com todas as meta tags
        """
        
        # Garantir tamanhos adequados
        title_formatted = f"{title} | {self.site_name}" if len(title) < 50 else title[:57] + "..."
        description_formatted = description[:160] if len(description) <= 160 else description[:157] + "..."
        
        meta_tags = {
            # Meta tags básicas
            'title': title_formatted,
            'description': description_formatted,
            'keywords': ', '.join(keywords) if keywords else '',
            
            # Open Graph (Facebook, LinkedIn, etc)
            'og:title': title,
            'og:description': description_formatted,
            'og:image': image or f"{self.site_url}/static/default-image.jpg",
            'og:url': url or self.site_url,
            'og:type': 'website',
            'og:site_name': self.site_name,
            
            # Twitter Cards
            'twitter:card': 'summary_large_image',
            'twitter:title': title,
            'twitter:description': description_formatted,
            'twitter:image': image or f"{self.site_url}/static/default-image.jpg",
        }
        
        return meta_tags
    
    def generate_product_schema(self, product: Dict) -> str:
        """
        Gera JSON-LD structured data para um produto
        Isso faz seu produto aparecer com preço, avaliações e estrelas no Google!
        
        Args:
            product: Dicionário com dados do produto
        
        Returns:
            String JSON-LD pronta para inserir no HTML
        """
        
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": product.get('title', ''),
            "description": product.get('description', product.get('title', '')),
            "image": product.get('images', [])[0] if product.get('images') else '',
            "sku": str(product.get('id', '')),
            "brand": {
                "@type": "Brand",
                "name": product.get('brand', self.site_name)
            },
            "offers": {
                "@type": "Offer",
                "url": f"{self.site_url}/produto/{product.get('id', '')}",
                "priceCurrency": "BRL",
                "price": str(product.get('price', 0)),
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {
                    "@type": "Organization",
                    "name": self.site_name
                }
            }
        }
        
        # Adicionar preço antigo se existir
        if product.get('oldPrice') and product['oldPrice'] > product.get('price', 0):
            schema['offers']['priceValidUntil'] = "2026-12-31"
            
        # Adicionar avaliações se existir
        if product.get('rating'):
            schema['aggregateRating'] = {
                "@type": "AggregateRating",
                "ratingValue": str(product['rating']),
                "bestRating": "5",
                "worstRating": "1",
                "reviewCount": str(product.get('review_count', 1))
            }
        
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def generate_organization_schema(self, 
                                    organization_name: str = None,
                                    logo: str = None,
                                    social_profiles: List[str] = None) -> str:
        """
        Gera JSON-LD structured data para a organização/empresa
        
        Args:
            organization_name: Nome da empresa
            logo: URL do logo
            social_profiles: Lista de URLs de redes sociais
        
        Returns:
            String JSON-LD pronta para inserir no HTML
        """
        
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": organization_name or self.site_name,
            "url": self.site_url,
            "logo": logo or f"{self.site_url}/static/logo.png",
        }
        
        if social_profiles:
            schema['sameAs'] = social_profiles
        
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def generate_breadcrumb_schema(self, breadcrumbs: List[Dict[str, str]]) -> str:
        """
        Gera JSON-LD structured data para breadcrumbs (navegação)
        
        Args:
            breadcrumbs: Lista de dicionários com 'name' e 'url'
                        Ex: [{'name': 'Home', 'url': '/'}, {'name': 'Produtos', 'url': '/produtos'}]
        
        Returns:
            String JSON-LD pronta para inserir no HTML
        """
        
        items = []
        for i, crumb in enumerate(breadcrumbs, 1):
            items.append({
                "@type": "ListItem",
                "position": i,
                "name": crumb['name'],
                "item": f"{self.site_url}{crumb['url']}"
            })
        
        schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items
        }
        
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def generate_sitemap_xml(self, pages: List[Dict]) -> str:
        """
        Gera sitemap XML dinamicamente
        
        Args:
            pages: Lista de dicionários com 'path', 'lastmod', 'changefreq', 'priority'
        
        Returns:
            String XML do sitemap
        """
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        
        for page in pages:
            xml_lines.append('  <url>')
            xml_lines.append(f'    <loc>{self.site_url}{page["path"]}</loc>')
            xml_lines.append(f'    <lastmod>{page.get("lastmod", datetime.now().strftime("%Y-%m-%d"))}</lastmod>')
            xml_lines.append(f'    <changefreq>{page.get("changefreq", "daily")}</changefreq>')
            xml_lines.append(f'    <priority>{page.get("priority", "0.5")}</priority>')
            xml_lines.append('  </url>')
        
        xml_lines.append('</urlset>')
        
        return '\n'.join(xml_lines)
    
    def generate_robots_txt(self, 
                           disallow_paths: List[str] = None,
                           sitemap_url: str = None) -> str:
        """
        Gera robots.txt
        
        Args:
            disallow_paths: Lista de paths a bloquear
            sitemap_url: URL do sitemap
        
        Returns:
            String do robots.txt
        """
        
        lines = ['User-agent: *', 'Allow: /']
        
        if disallow_paths:
            for path in disallow_paths:
                lines.append(f'Disallow: {path}')
        
        lines.append('')
        lines.append(f'Sitemap: {sitemap_url or f"{self.site_url}/sitemap.xml"}')
        
        return '\n'.join(lines)


# Instância global do serviço
seo_service = SEOService(
    site_name="DEF - Lojinha",
    site_url="https://seusite.com"  # Alterar quando tiver domínio
)
