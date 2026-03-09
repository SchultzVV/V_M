# 🚀 Estratégia de Visibilidade para o Site

## 📋 Índice
1. [SEO (Search Engine Optimization)](#seo)
2. [Google Ads & Marketing Pago](#google-ads)
3. [Implementações Técnicas para Desenvolvedores](#implementações-técnicas)
4. [Redes Sociais & Marketing de Conteúdo](#redes-sociais)
5. [Alternativas ao ngrok](#alternativas-ngrok)
6. [Analytics & Monitoramento](#analytics)
7. [Plano de Ação Prioritário](#plano-de-ação)

---

## 1. SEO (Search Engine Optimization) {#seo}

### 🎯 Fundamentos Essenciais

#### A) Meta Tags Obrigatórias
```html
<!-- Em cada página HTML -->
<head>
    <!-- Title otimizado (50-60 caracteres) -->
    <title>Seu Produto - Descrição Curta | Nome da Loja</title>
    
    <!-- Meta Description (150-160 caracteres) -->
    <meta name="description" content="Descrição atrativa com palavras-chave principais">
    
    <!-- Open Graph para redes sociais -->
    <meta property="og:title" content="Título para compartilhamento">
    <meta property="og:description" content="Descrição para redes sociais">
    <meta property="og:image" content="https://seusite.com/imagem-preview.jpg">
    <meta property="og:url" content="https://seusite.com/pagina">
    <meta property="og:type" content="website">
    
    <!-- Twitter Cards -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Título para Twitter">
    <meta name="twitter:description" content="Descrição para Twitter">
    <meta name="twitter:image" content="https://seusite.com/imagem-preview.jpg">
    
    <!-- Canonical URL (evita conteúdo duplicado) -->
    <link rel="canonical" href="https://seusite.com/pagina-principal">
    
    <!-- Viewport para mobile -->
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
```

#### B) Structured Data (Schema.org)
```html
<!-- Para produtos de e-commerce -->
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": "Nome do Produto",
  "image": [
    "https://seusite.com/produto-1.jpg",
    "https://seusite.com/produto-2.jpg"
  ],
  "description": "Descrição completa do produto",
  "sku": "SKU123",
  "brand": {
    "@type": "Brand",
    "name": "Marca"
  },
  "offers": {
    "@type": "Offer",
    "url": "https://seusite.com/produto",
    "priceCurrency": "BRL",
    "price": "99.99",
    "priceValidUntil": "2026-12-31",
    "availability": "https://schema.org/InStock",
    "seller": {
      "@type": "Organization",
      "name": "Sua Loja"
    }
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.5",
    "reviewCount": "89"
  }
}
</script>

<!-- Para organização/empresa -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Nome da Sua Empresa",
  "url": "https://seusite.com",
  "logo": "https://seusite.com/logo.png",
  "sameAs": [
    "https://www.facebook.com/suapagina",
    "https://www.instagram.com/suaperfil",
    "https://twitter.com/suaperfil"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+55-11-9999-9999",
    "contactType": "customer service"
  }
}
</script>
```

#### C) Sitemap XML
```xml
<!-- sitemap.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://seusite.com/</loc>
    <lastmod>2026-02-02</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://seusite.com/produtos</loc>
    <lastmod>2026-02-02</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <!-- Adicionar todas as páginas importantes -->
</urlset>
```

#### D) robots.txt
```txt
# robots.txt
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /private/

Sitemap: https://seusite.com/sitemap.xml
```

#### E) Core Web Vitals - Performance
```python
# Otimizações de Performance no Backend (FastAPI)

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import datetime, timedelta

app = FastAPI()

# Compressão GZIP
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Cache Headers
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    
    # Cache estático por 1 ano
    if request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    # Cache de imagens por 1 mês
    elif request.url.path.endswith(('.jpg', '.png', '.webp', '.svg')):
        response.headers['Cache-Control'] = 'public, max-age=2592000'
    # Cache de HTML por 1 hora
    elif request.url.path.endswith('.html') or request.url.path == '/':
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

# Lazy loading de imagens
# Em seus templates HTML:
"""
<img src="placeholder.jpg" 
     data-src="imagem-real.jpg" 
     loading="lazy" 
     alt="Descrição da imagem">
"""
```

### 📍 Checklist SEO Técnico

```markdown
## Checklist SEO On-Page
- [ ] Title tags únicos e otimizados (50-60 caracteres)
- [ ] Meta descriptions atrativas (150-160 caracteres)
- [ ] URLs amigáveis e descritivas
- [ ] Headings hierárquicos (H1, H2, H3)
- [ ] Alt text em todas as imagens
- [ ] Links internos relevantes
- [ ] Sitemap.xml configurado
- [ ] robots.txt configurado
- [ ] Canonical tags quando necessário
- [ ] Schema.org/structured data
- [ ] Open Graph tags
- [ ] Twitter Cards
- [ ] Mobile responsive
- [ ] Velocidade de carregamento < 3s
- [ ] HTTPS configurado
- [ ] Compressão GZIP ativada
- [ ] Imagens otimizadas (WebP quando possível)
- [ ] Lazy loading de imagens
- [ ] Cache browser configurado
```

---

## 2. Google Ads & Marketing Pago {#google-ads}

### 🎯 Configuração Google Ads

#### A) Estrutura de Conta Recomendada
```
Conta Google Ads
├── Campanha 1: Pesquisa - Produtos Principais
│   ├── Grupo de Anúncios: Produto A
│   │   ├── Palavras-chave: específicas do produto A
│   │   └── Anúncios: 3-5 variações
│   └── Grupo de Anúncios: Produto B
│       ├── Palavras-chave: específicas do produto B
│       └── Anúncios: 3-5 variações
│
├── Campanha 2: Display - Remarketing
│   └── Visitantes do site (últimos 30 dias)
│
└── Campanha 3: Shopping (se aplicável)
    └── Feed de produtos do Mercado Livre/Shopee
```

#### B) Google Ads API - Implementação
```python
# Instalação
# pip install google-ads

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Configuração
# Criar arquivo google-ads.yaml
"""
developer_token: SEU_DEVELOPER_TOKEN
client_id: SEU_CLIENT_ID
client_secret: SEU_CLIENT_SECRET
refresh_token: SEU_REFRESH_TOKEN
login_customer_id: SEU_CUSTOMER_ID
"""

class GoogleAdsManager:
    def __init__(self, config_path="google-ads.yaml"):
        self.client = GoogleAdsClient.load_from_storage(config_path)
    
    def create_campaign(self, customer_id, campaign_name, budget_amount):
        """Criar campanha de pesquisa"""
        campaign_service = self.client.get_service("CampaignService")
        campaign_budget_service = self.client.get_service("CampaignBudgetService")
        
        # Criar orçamento
        campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
        campaign_budget = campaign_budget_operation.create
        campaign_budget.name = f"Budget for {campaign_name}"
        campaign_budget.amount_micros = budget_amount * 1_000_000  # Convertter para micros
        campaign_budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD
        
        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[campaign_budget_operation]
        )
        
        # Criar campanha
        campaign_operation = self.client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = campaign_name
        campaign.advertising_channel_type = self.client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.status = self.client.enums.CampaignStatusEnum.PAUSED
        campaign.campaign_budget = budget_response.results[0].resource_name
        
        campaign_response = campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[campaign_operation]
        )
        
        return campaign_response.results[0].resource_name
    
    def create_ad_group(self, customer_id, campaign_resource_name, ad_group_name):
        """Criar grupo de anúncios"""
        ad_group_service = self.client.get_service("AdGroupService")
        
        ad_group_operation = self.client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        ad_group.name = ad_group_name
        ad_group.campaign = campaign_resource_name
        ad_group.type_ = self.client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.cpc_bid_micros = 1_000_000  # R$ 1.00
        
        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[ad_group_operation]
        )
        
        return response.results[0].resource_name

# Uso
ads_manager = GoogleAdsManager()
campaign = ads_manager.create_campaign(
    customer_id="1234567890",
    campaign_name="Produtos - Pesquisa",
    budget_amount=50.00  # R$ 50 por dia
)
```

#### C) Google Tag Manager (GTM)
```html
<!-- Adicionar no <head> de todas as páginas -->
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-XXXXXXX');</script>
<!-- End Google Tag Manager -->

<!-- Adicionar logo após <body> -->
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXXX"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
```

#### D) Conversão e Tracking
```javascript
// Event tracking - conversões
function trackConversion(conversionLabel, value) {
    gtag('event', 'conversion', {
        'send_to': 'AW-CONVERSION_ID/' + conversionLabel,
        'value': value,
        'currency': 'BRL'
    });
}

// Exemplo de uso
document.querySelector('#buy-button').addEventListener('click', function() {
    trackConversion('COMPRA_LABEL', 99.99);
});

// Event tracking personalizado
gtag('event', 'add_to_cart', {
    'event_category': 'ecommerce',
    'event_label': 'Nome do Produto',
    'value': 99.99
});
```

### 💰 Orçamento Sugerido (Inicial)

```
Investimento Mensal Sugerido:
┌────────────────────────────┬──────────┬────────────┐
│ Canal                      │ Budget   │ CPC Médio  │
├────────────────────────────┼──────────┼────────────┤
│ Google Ads - Pesquisa      │ R$ 500   │ R$ 1-3     │
│ Google Ads - Display       │ R$ 200   │ R$ 0.50    │
│ Facebook/Instagram Ads     │ R$ 300   │ R$ 0.30    │
│ Google Shopping (opcional) │ R$ 400   │ R$ 0.80    │
├────────────────────────────┼──────────┼────────────┤
│ Total                      │ R$ 1.400 │            │
└────────────────────────────┴──────────┴────────────┘

Começar com: R$ 500-800/mês
Escalar conforme ROI
```

---

## 3. Implementações Técnicas para Desenvolvedores {#implementações-técnicas}

### 🛠️ A) Sistema de SEO Automático
```python
# services/site/services/seo_service.py

from typing import Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

class SEOService:
    """Serviço para gerenciar SEO automaticamente"""
    
    def generate_meta_tags(self, page_type: str, data: Dict) -> Dict[str, str]:
        """Gera meta tags otimizadas baseado no tipo de página"""
        
        templates = {
            'product': {
                'title': f"{data['name']} - {data['category']} | {data['store_name']}",
                'description': f"Compre {data['name']} por R$ {data['price']}. {data['short_description'][:100]}...",
                'keywords': f"{data['name']}, {data['category']}, {', '.join(data.get('tags', []))}"
            },
            'category': {
                'title': f"{data['category']} - Produtos em Oferta | {data['store_name']}",
                'description': f"Encontre os melhores {data['category']} com preços incríveis. Entrega rápida e segura.",
                'keywords': f"{data['category']}, comprar {data['category']}, {data['category']} barato"
            },
            'home': {
                'title': f"{data['store_name']} - {data['slogan']}",
                'description': data['about'][:160],
                'keywords': ', '.join(data.get('main_categories', []))
            }
        }
        
        return templates.get(page_type, templates['home'])
    
    def generate_structured_data(self, product_data: Dict) -> str:
        """Gera JSON-LD structured data para produto"""
        
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": product_data['name'],
            "image": product_data['images'],
            "description": product_data['description'],
            "sku": product_data.get('sku', ''),
            "brand": {
                "@type": "Brand",
                "name": product_data.get('brand', 'Generic')
            },
            "offers": {
                "@type": "Offer",
                "url": f"https://seusite.com/produto/{product_data['slug']}",
                "priceCurrency": "BRL",
                "price": str(product_data['price']),
                "priceValidUntil": "2026-12-31",
                "availability": "https://schema.org/InStock",
                "seller": {
                    "@type": "Organization",
                    "name": product_data.get('seller', 'Sua Loja')
                }
            }
        }
        
        if 'rating' in product_data:
            schema["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": str(product_data['rating']),
                "reviewCount": str(product_data.get('review_count', 0))
            }
        
        import json
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def generate_sitemap(self, base_url: str, pages: list) -> str:
        """Gera sitemap XML dinamicamente"""
        
        urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        
        for page in pages:
            url = ET.SubElement(urlset, 'url')
            ET.SubElement(url, 'loc').text = f"{base_url}{page['path']}"
            ET.SubElement(url, 'lastmod').text = page.get('lastmod', datetime.now().strftime('%Y-%m-%d'))
            ET.SubElement(url, 'changefreq').text = page.get('changefreq', 'daily')
            ET.SubElement(url, 'priority').text = str(page.get('priority', 0.5))
        
        return ET.tostring(urlset, encoding='unicode', method='xml')

# Endpoint no FastAPI
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()
seo_service = SEOService()

@router.get("/sitemap.xml")
async def get_sitemap():
    pages = [
        {'path': '/', 'priority': 1.0, 'changefreq': 'daily'},
        {'path': '/produtos', 'priority': 0.9, 'changefreq': 'daily'},
        # Adicionar páginas de produtos dinamicamente
    ]
    
    sitemap_xml = seo_service.generate_sitemap("https://seusite.com", pages)
    return Response(content=sitemap_xml, media_type="application/xml")

@router.get("/robots.txt")
async def get_robots():
    robots = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: https://seusite.com/sitemap.xml"""
    
    return Response(content=robots, media_type="text/plain")
```

### 🔍 B) Sistema de Analytics
```python
# services/site/services/analytics_service.py

from datetime import datetime, timedelta
from typing import Dict, List
import httpx

class AnalyticsService:
    """Serviço para tracking e analytics"""
    
    def __init__(self):
        self.events = []
    
    async def track_event(self, event_type: str, data: Dict):
        """Registra evento de analytics"""
        
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        self.events.append(event)
        
        # Enviar para Google Analytics 4
        await self.send_to_ga4(event)
    
    async def send_to_ga4(self, event: Dict):
        """Envia evento para Google Analytics 4"""
        
        measurement_id = "G-XXXXXXXXXX"
        api_secret = "SEU_API_SECRET"
        
        url = f"https://www.google-analytics.com/mp/collect?measurement_id={measurement_id}&api_secret={api_secret}"
        
        payload = {
            "client_id": event['data'].get('client_id', 'anonymous'),
            "events": [{
                "name": event['type'],
                "params": event['data']
            }]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload)
            except Exception as e:
                print(f"Erro ao enviar para GA4: {e}")
    
    def get_popular_pages(self, days: int = 7) -> List[Dict]:
        """Retorna páginas mais visitadas"""
        cutoff = datetime.now() - timedelta(days=days)
        
        page_views = {}
        for event in self.events:
            if event['type'] == 'page_view' and datetime.fromisoformat(event['timestamp']) > cutoff:
                page = event['data'].get('page')
                page_views[page] = page_views.get(page, 0) + 1
        
        return sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:10]

# Middleware para tracking automático
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Track page view
        analytics = AnalyticsService()
        await analytics.track_event('page_view', {
            'page': str(request.url.path),
            'referrer': request.headers.get('referer'),
            'user_agent': request.headers.get('user-agent')
        })
        
        response = await call_next(request)
        return response

# Adicionar no main.py
app.add_middleware(AnalyticsMiddleware)
```

### 📱 C) PWA (Progressive Web App)
```json
// static/manifest.json
{
  "name": "Nome da Sua Loja",
  "short_name": "Loja",
  "description": "Descrição da sua loja",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#000000",
  "icons": [
    {
      "src": "/static/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

```javascript
// static/service-worker.js
const CACHE_NAME = 'loja-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/icons/icon-192x192.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
```

```html
<!-- Adicionar no <head> -->
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#000000">

<script>
// Registrar Service Worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/service-worker.js')
    .then(reg => console.log('Service Worker registrado', reg))
    .catch(err => console.log('Erro ao registrar Service Worker', err));
}
</script>
```

---

## 4. Redes Sociais & Marketing de Conteúdo {#redes-sociais}

### 📱 A) Estratégia de Conteúdo

#### Frequência de Posts
```
Instagram:
- Feed: 3-5x por semana
- Stories: Diariamente (5-10 stories)
- Reels: 3-4x por semana

Facebook:
- Posts: 1-2x por dia
- Lives: 1x por semana

TikTok:
- Vídeos: 1-3x por dia

Pinterest:
- Pins: 5-10x por dia
```

#### Tipos de Conteúdo
```markdown
1. **Conteúdo de Produto** (40%)
   - Fotos profissionais
   - Vídeos de demonstração
   - Unboxing
   - Reviews de clientes

2. **Conteúdo Educacional** (30%)
   - Tutoriais
   - Dicas de uso
   - Comparações
   - FAQs

3. **Conteúdo de Engajamento** (20%)
   - Enquetes
   - Perguntas
   - Desafios
   - User-generated content

4. **Conteúdo Promocional** (10%)
   - Ofertas exclusivas
   - Cupons
   - Lançamentos
   - Flash sales
```

### 🤖 B) Automação de Redes Sociais
```python
# services/site/services/social_media_service.py

from typing import Dict, List
import httpx
from datetime import datetime

class SocialMediaService:
    """Serviço para automação de redes sociais"""
    
    def __init__(self):
        self.instagram_token = "SEU_TOKEN_INSTAGRAM"
        self.facebook_token = "SEU_TOKEN_FACEBOOK"
    
    async def post_to_instagram(self, image_url: str, caption: str, hashtags: List[str]):
        """Posta no Instagram via API oficial"""
        
        # Instagram Graph API
        ig_user_id = "SEU_IG_USER_ID"
        
        # Criar container
        container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        container_params = {
            'image_url': image_url,
            'caption': f"{caption}\n\n{' '.join(['#' + tag for tag in hashtags])}",
            'access_token': self.instagram_token
        }
        
        async with httpx.AsyncClient() as client:
            container_response = await client.post(container_url, data=container_params)
            container_id = container_response.json()['id']
            
            # Publicar
            publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
            publish_params = {
                'creation_id': container_id,
                'access_token': self.instagram_token
            }
            
            response = await client.post(publish_url, data=publish_params)
            return response.json()
    
    async def post_to_facebook(self, message: str, link: str = None):
        """Posta no Facebook via API"""
        
        page_id = "SUA_PAGE_ID"
        url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        
        params = {
            'message': message,
            'access_token': self.facebook_token
        }
        
        if link:
            params['link'] = link
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=params)
            return response.json()
    
    def generate_hashtags(self, product_category: str, product_name: str) -> List[str]:
        """Gera hashtags relevantes automaticamente"""
        
        base_tags = ['loja', 'compras', 'ofertas', 'promoção']
        category_tags = [product_category.lower().replace(' ', '')]
        product_tags = [word.lower() for word in product_name.split() if len(word) > 3]
        
        return base_tags + category_tags + product_tags[:5]
    
    async def schedule_post(self, platform: str, content: Dict, scheduled_time: datetime):
        """Agenda post para horário específico"""
        
        # Implementar sistema de agendamento
        # Pode usar Celery ou similar
        pass

# Endpoint para auto-post quando produto é adicionado
@router.post("/auto-share-product")
async def auto_share_product(product_data: Dict):
    social = SocialMediaService()
    
    # Gerar caption otimizada
    caption = f"✨ Novo produto! {product_data['name']}\n\n"
    caption += f"💰 Apenas R$ {product_data['price']}\n\n"
    caption += f"🛒 Link na bio!\n"
    
    # Gerar hashtags
    hashtags = social.generate_hashtags(
        product_data['category'],
        product_data['name']
    )
    
    # Postar no Instagram
    await social.post_to_instagram(
        product_data['image_url'],
        caption,
        hashtags
    )
    
    # Postar no Facebook
    await social.post_to_facebook(
        caption + ' ' + ' '.join(['#' + tag for tag in hashtags]),
        product_data['product_url']
    )
    
    return {"status": "posted"}
```

### 📊 C) Pixel de Conversão
```html
<!-- Facebook Pixel -->
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'SEU_PIXEL_ID');
fbq('track', 'PageView');
</script>
<noscript>
<img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id=SEU_PIXEL_ID&ev=PageView&noscript=1"/>
</noscript>

<!-- Track eventos -->
<script>
// Visualização de produto
fbq('track', 'ViewContent', {
    content_ids: ['PRODUCT_ID'],
    content_type: 'product',
    value: 99.99,
    currency: 'BRL'
});

// Adicionar ao carrinho
fbq('track', 'AddToCart', {
    content_ids: ['PRODUCT_ID'],
    content_type: 'product',
    value: 99.99,
    currency: 'BRL'
});

// Compra
fbq('track', 'Purchase', {
    content_ids: ['PRODUCT_ID'],
    content_type: 'product',
    value: 99.99,
    currency: 'BRL'
});
</script>
```

---

## 5. Alternativas ao ngrok {#alternativas-ngrok}

### 🌐 Opções de Hospedagem e Túnel

#### A) ngrok Premium
```bash
# Vantagens do Premium:
- Domínio customizado (seusite.ngrok.io ou seu-dominio.com)
- Sem limite de conexões
- Mais regiões disponíveis
- IP estático
- Melhor performance

# Preços:
- Personal: $10/mês - 1 domínio, 3 endpoints
- Pro: $25/mês - 3 domínios, 10 endpoints
- Business: $60/mês - domínio customizado completo

# Comandos úteis:
ngrok http 8000 --region=sa --hostname=seusite.ngrok.io
```

#### B) Cloudflare Tunnel (GRÁTIS!)
```bash
# Instalação
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Login
cloudflared tunnel login

# Criar túnel
cloudflared tunnel create meu-site

# Configurar
cat > ~/.cloudflared/config.yml << EOF
tunnel: SEU_TUNNEL_ID
credentials-file: /home/user/.cloudflared/SEU_TUNNEL_ID.json

ingress:
  - hostname: seusite.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Configurar DNS no Cloudflare
cloudflared tunnel route dns meu-site seusite.com

# Executar
cloudflared tunnel run meu-site

# Como serviço (inicia automaticamente)
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

#### C) Outras Alternativas

```markdown
### 1. **Serveo** (Grátis)
```bash
ssh -R 80:localhost:8000 serveo.net
# URL: https://random.serveo.net
```

### 2. **LocalTunnel** (Grátis)
```bash
npm install -g localtunnel
lt --port 8000 --subdomain seusite
# URL: https://seusite.loca.lt
```

### 3. **Pagekite** (Pago - €3/mês)
```bash
curl -O https://pagekite.net/pk/pagekite.py
python pagekite.py 8000 seusite.pagekite.me
```

### 4. **Bore** (Grátis - Open Source)
```bash
cargo install bore-cli
bore local 8000 --to bore.pub
```

### 5. **Cloudflare Pages/Workers** (Grátis + Serverless)
- Deploy direto do GitHub
- HTTPS automático
- CDN global
- 500 builds/mês grátis
```

#### D) VPS Próprio (Recomendado para Produção)
```markdown
### Provedores VPS Brasil:

1. **Contabo** (Mais barato)
   - VPS S: €4.50/mês (~R$25)
   - 4 vCPU, 8GB RAM, 200GB SSD
   - Datacenter na Europa

2. **DigitalOcean**
   - Droplet Basic: $6/mês (~R$30)
   - 1 vCPU, 1GB RAM, 25GB SSD
   - Datacenter em São Paulo

3. **Vultr**
   - Cloud Compute: $6/mês
   - 1 vCPU, 1GB RAM, 25GB SSD
   - Datacenter em São Paulo

4. **AWS Lightsail**
   - $3.50/mês (primeiro ano)
   - 512MB RAM, 20GB SSD

5. **Hostinger VPS**
   - R$19.99/mês
   - 1 vCPU, 4GB RAM, 50GB SSD
   - Suporte em português

### Setup VPS Rápido:
```bash
# 1. Conectar via SSH
ssh root@seu-ip

# 2. Atualizar sistema
apt update && apt upgrade -y

# 3. Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Instalar Docker Compose
apt install docker-compose -y

# 5. Clonar seu projeto
git clone seu-repositorio.git
cd seu-projeto

# 6. Subir aplicação
docker-compose up -d

# 7. Configurar Nginx como proxy reverso
apt install nginx -y
nano /etc/nginx/sites-available/default

# Adicionar:
server {
    listen 80;
    server_name seudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# 8. Configurar SSL (Let's Encrypt)
apt install certbot python3-certbot-nginx -y
certbot --nginx -d seudominio.com
```
```

---

## 6. Analytics & Monitoramento {#analytics}

### 📊 A) Google Analytics 4
```html
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-XXXXXXXXXX', {
    'send_page_view': false  // Manualmente controlar pageviews
  });
  
  // Custom events
  function trackProduct(productId, productName, price) {
    gtag('event', 'view_item', {
      'currency': 'BRL',
      'value': price,
      'items': [{
        'item_id': productId,
        'item_name': productName,
        'price': price
      }]
    });
  }
</script>
```

### 🔍 B) Google Search Console
```html
<!-- Verificação do site -->
<meta name="google-site-verification" content="SEU_CODIGO_VERIFICACAO" />
```

**Tarefas no Search Console:**
1. Adicionar propriedade (seusite.com)
2. Verificar propriedade (via meta tag)
3. Enviar sitemap.xml
4. Monitorar:
   - Impressões e cliques
   - Posição média
   - Core Web Vitals
   - Erros de rastreamento
   - Coverage (cobertura de índice)

### 📈 C) Dashboard de Métricas
```python
# services/site/services/metrics_service.py

from datetime import datetime, timedelta
from typing import Dict, List

class MetricsService:
    """Serviço para métricas e KPIs"""
    
    def calculate_kpis(self, period_days: int = 30) -> Dict:
        """Calcula KPIs principais"""
        
        cutoff = datetime.now() - timedelta(days=period_days)
        
        # Simular dados (substituir com dados reais do banco)
        kpis = {
            'visitors': {
                'total': 1250,
                'unique': 890,
                'bounce_rate': 45.2,  # %
                'avg_session_duration': 185  # segundos
            },
            'conversions': {
                'total': 45,
                'rate': 3.6,  # %
                'value': 4250.00,  # R$
                'avg_order_value': 94.44  # R$
            },
            'seo': {
                'organic_traffic': 567,
                'keywords_ranking': 23,
                'avg_position': 12.5,
                'impressions': 8900
            },
            'social': {
                'instagram_followers': 1250,
                'engagement_rate': 4.2,  # %
                'post_reach': 5600
            },
            'ads': {
                'spend': 500.00,  # R$
                'clicks': 234,
                'cpc': 2.14,  # R$
                'roas': 8.5  # Return on Ad Spend
            }
        }
        
        return kpis
    
    def get_top_products(self, limit: int = 10) -> List[Dict]:
        """Retorna produtos mais vendidos"""
        
        # Implementar query no banco de dados
        products = [
            {'name': 'Produto A', 'sales': 45, 'revenue': 1350.00},
            {'name': 'Produto B', 'sales': 32, 'revenue': 960.00},
            # ...
        ]
        
        return products[:limit]
    
    def get_traffic_sources(self) -> Dict:
        """Retorna fontes de tráfego"""
        
        return {
            'organic': 45,  # %
            'direct': 25,
            'social': 20,
            'referral': 7,
            'paid': 3
        }

# Endpoint para dashboard
from fastapi import APIRouter

router = APIRouter()
metrics = MetricsService()

@router.get("/dashboard/metrics")
async def get_dashboard_metrics():
    return {
        'kpis': metrics.calculate_kpis(),
        'top_products': metrics.get_top_products(),
        'traffic_sources': metrics.get_traffic_sources()
    }
```

---

## 7. Plano de Ação Prioritário {#plano-de-ação}

### 🎯 Fase 1: Fundação SEO (Semana 1-2)

```markdown
## Prioridade ALTA - Fazer AGORA

### Dia 1-3: Setup Básico
- [ ] Configurar meta tags em todas as páginas
- [ ] Implementar structured data (schema.org)
- [ ] Criar sitemap.xml dinâmico
- [ ] Criar robots.txt
- [ ] Otimizar imagens (WebP, lazy loading)
- [ ] Configurar compressão GZIP
- [ ] Implementar cache headers

### Dia 4-7: Analytics e Tracking
- [ ] Configurar Google Analytics 4
- [ ] Configurar Google Search Console
- [ ] Instalar Google Tag Manager
- [ ] Configurar Facebook Pixel
- [ ] Implementar tracking de conversões

### Dia 8-14: Hospedagem e Domínio
- [ ] Comprar domínio (.com.br ou .com)
- [ ] Configurar Cloudflare Tunnel OU
- [ ] Contratar VPS (se budget permitir)
- [ ] Configurar HTTPS/SSL
- [ ] Testar performance (PageSpeed Insights)
```

### 🚀 Fase 2: Marketing e Visibilidade (Semana 3-4)

```markdown
## Prioridade MÉDIA

### Semana 3: Redes Sociais
- [ ] Criar perfis profissionais (Instagram, Facebook)
- [ ] Configurar Instagram Business Account
- [ ] Conectar Facebook Shop
- [ ] Criar 10-15 posts iniciais
- [ ] Configurar auto-post de novos produtos
- [ ] Planejar calendário de conteúdo mensal

### Semana 4: Google Ads (se orçamento permitir)
- [ ] Criar conta Google Ads
- [ ] Configurar primeira campanha de pesquisa
- [ ] Definir orçamento diário (R$20-30/dia inicial)
- [ ] Criar 3-5 grupos de anúncios
- [ ] Definir palavras-chave
- [ ] Criar extensões de anúncio
```

### 📈 Fase 3: Otimização e Escala (Mês 2+)

```markdown
## Prioridade BAIXA (após estabelecer base)

### Mês 2:
- [ ] Implementar PWA
- [ ] Criar blog para marketing de conteúdo
- [ ] Iniciar guest posting
- [ ] Link building
- [ ] Parcerias com influencers
- [ ] Email marketing
- [ ] Programa de afiliados

### Mês 3+:
- [ ] Google Shopping
- [ ] Remarketing avançado
- [ ] A/B testing
- [ ] Otimização de conversão (CRO)
- [ ] Expansão para outros marketplaces
- [ ] Análise de concorrentes
```

---

## 📝 Checklist Diário de Marketing

```markdown
### Todos os Dias
- [ ] Verificar métricas Google Analytics (10 min)
- [ ] Responder comentários e mensagens nas redes sociais (15 min)
- [ ] Publicar 1 story no Instagram (5 min)
- [ ] Monitorar posições de palavras-chave (Search Console)

### Todas as Semanas
- [ ] Analisar performance de anúncios (Google Ads)
- [ ] Publicar 3-4 posts no feed Instagram/Facebook
- [ ] Criar 2-3 Reels
- [ ] Revisar e otimizar palavras-chave
- [ ] Atualizar produtos no catálogo

### Todo Mês
- [ ] Relatório completo de métricas
- [ ] Revisar orçamento de marketing
- [ ] Planejar conteúdo do próximo mês
- [ ] Otimizar páginas com baixo desempenho
- [ ] Testar novos canais de aquisição
- [ ] Analisar concorrentes
```

---

## 💡 Dicas Finais

### ✅ O Que Fazer
1. **Foque em SEO primeiro** - É gratuito e de longo prazo
2. **Comece pequeno com ads** - R$500-800/mês é suficiente inicialmente
3. **Seja consistente nas redes sociais** - 1 post/dia é melhor que 7 posts/semana
4. **Meça TUDO** - Dados > Achismos
5. **Mobile First** - 70%+ do tráfego vem de mobile
6. **Velocidade importa** - Site < 3s de carregamento
7. **Conteúdo de qualidade** - Melhor que quantidade

### ❌ O Que Evitar
1. Não comprar followers/likes fake
2. Não fazer keyword stuffing
3. Não copiar conteúdo de outros sites
4. Não ignorar mobile
5. Não gastar todo budget em ads logo de início
6. Não esquecer de tracking/analytics
7. Não esperar resultados imediatos (SEO leva 3-6 meses)

---

## 📚 Recursos e Ferramentas Gratuitas

### SEO Tools
- **Google Search Console** - Monitoramento SEO
- **Google Analytics** - Analytics
- **PageSpeed Insights** - Performance
- **Ubersuggest** - Pesquisa de palavras-chave (limitado)
- **AnswerThePublic** - Ideias de conteúdo
- **Google Trends** - Tendências de busca

### Design & Conteúdo
- **Canva** - Design de posts
- **Remove.bg** - Remover fundo de imagens
- **TinyPNG** - Comprimir imagens
- **Unsplash/Pexels** - Fotos grátis

### Social Media
- **Buffer** (grátis) - Agendamento de posts
- **Later** (grátis) - Instagram scheduling
- **Hashtagify** - Pesquisa de hashtags

### Analytics
- **Hotjar** (grátis limitado) - Heatmaps
- **Google Optimize** - A/B testing
- **Microsoft Clarity** - Session recordings

---

## 🎓 Cursos e Documentação

### Grátis
1. **Google Digital Garage** - Marketing digital completo
2. **Google Skillshop** - Google Ads certification
3. **Facebook Blueprint** - Facebook/Instagram ads
4. **HubSpot Academy** - Inbound marketing
5. **SEMrush Academy** - SEO avançado

### Documentação Oficial
- [Google Search Central](https://developers.google.com/search)
- [Google Ads Help](https://support.google.com/google-ads)
- [Facebook for Business](https://www.facebook.com/business/learn)
- [Instagram for Business](https://business.instagram.com/)

---

## 📞 Próximos Passos

1. **Implementar SEO básico** (Fase 1 - 2 semanas)
2. **Escolher solução de hospedagem** (Cloudflare Tunnel ou VPS)
3. **Configurar Analytics** (GA4 + Search Console)
4. **Criar presença em redes sociais**
5. **Iniciar com budget pequeno de ads** (R$500-800/mês)
6. **Medir e otimizar continuamente**

**Lembre-se:** Visibilidade online é uma maratona, não uma corrida de 100m. Consistência e paciência são essenciais!

---

**Última atualização:** 02/02/2026
**Versão:** 1.0
