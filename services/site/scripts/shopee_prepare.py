#!/usr/bin/env python3
"""
Preparação de produtos da Shopee via scraping.
Similar ao auto_prepare_ml.py, mas adaptado para estrutura da Shopee.

Suporta:
- Links diretos de produtos
- Links de afiliado
- Extração de informações completas do produto
- Download de imagens
- Geração de JSON para staging
"""

import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import re
from slugify import slugify
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def resolve_shopee_link(url):
    """
    Resolve links de afiliado ou encurtados da Shopee.
    
    Exemplos de URLs suportadas:
    - https://shopee.com.br/product/123456/7890123456
    - https://shope.ee/ABC123 (encurtado)
    - https://s.shopee.com.br/... (afiliado)
    """
    print(f"\n🔗 Resolvendo link da Shopee...")
    
    # Limpar caracteres escapados indevidamente (ex: \? vira ?)
    url_cleaned = url.replace(r'\?', '?').replace(r'\=', '=').replace(r'\&', '&')
    
    if url_cleaned != url:
        print(f"   🧹 URL limpa: {url_cleaned}")
        url = url_cleaned
    else:
        print(f"   URL original: {url}")
    
    try:
        # Se for link encurtado, seguir redirecionamentos
        if 'shope.ee' in url or 's.shopee' in url:
            print(f"   📍 Link encurtado detectado, seguindo redirecionamentos...")
            response = requests.get(url, allow_redirects=True, timeout=15)
            final_url = response.url
            print(f"   ✅ URL final: {final_url}")
            return final_url
        
        return url
    
    except Exception as e:
        print(f"   ⚠️  Erro ao resolver link: {e}")
        return url


def find_item_in_json(data, depth=0, max_depth=5):
    """
    Busca recursivamente por dados do item no JSON da página.
    """
    if depth > max_depth or not isinstance(data, (dict, list)):
        return None
    
    if isinstance(data, dict):
        # Verificar se é um objeto de item válido
        if 'itemid' in data and 'name' in data:
            return data
        
        # Buscar recursivamente
        for key, value in data.items():
            if key in ['item', 'data', 'product']:
                result = find_item_in_json(value, depth + 1, max_depth)
                if result:
                    return result
    
    elif isinstance(data, list):
        for item in data:
            result = find_item_in_json(item, depth + 1, max_depth)
            if result:
                return result
    
    return None


def parse_shopee_item_data(item_data):
    """
    Converte dados do item da Shopee para o formato padrão.
    """
    product = {
        'title': item_data.get('name', ''),
        'price': 0,
        'original_price': 0,
        'stock': item_data.get('stock', 0),
        'sold': item_data.get('sold', item_data.get('historical_sold', 0)),
        'rating': item_data.get('item_rating', {}).get('rating_star', 0),
        'description': item_data.get('description', ''),
        'images': [],
        'condition': 'new'
    }
    
    # Extrair preço (Shopee usa centavos * 1000)
    price = item_data.get('price', item_data.get('price_min', 0))
    if price > 1000:
        product['price'] = price / 100000
    
    # Extrair preço antigo
    old_price = item_data.get('price_before_discount', 0)
    if old_price > 1000:
        product['original_price'] = old_price / 100000
    
    # Extrair imagens
    images = item_data.get('images', [])
    if images:
        base_url = "https://down-br.img.susercontent.com/file/"
        product['images'] = [f"{base_url}{img}" for img in images[:10]]
    
    return product


def extract_product_ids(url):
    """
    Extrai shop_id e item_id da URL da Shopee.
    
    Formato típico: https://shopee.com.br/product/{shop_id}/{item_id}
    Ou: https://shopee.com.br/{product-name}-i.{shop_id}.{item_id}
    Ou: https://shopee.com.br/{shop_name}/{shop_id}/{item_id}
    """
    print(f"\n🔍 Extraindo IDs do produto...")
    
    # Padrão 1: /product/{shop_id}/{item_id}
    match = re.search(r'/product/(\d+)/(\d+)', url)
    if match:
        shop_id, item_id = match.groups()
        print(f"   ✅ Shop ID: {shop_id}")
        print(f"   ✅ Item ID: {item_id}")
        return shop_id, item_id
    
    # Padrão 2: /{nome}-i.{shop_id}.{item_id}
    match = re.search(r'-i\.(\d+)\.(\d+)', url)
    if match:
        shop_id, item_id = match.groups()
        print(f"   ✅ Shop ID: {shop_id}")
        print(f"   ✅ Item ID: {item_id}")
        return shop_id, item_id
    
    # Padrão 3: /{shop_name}/{shop_id}/{item_id}
    match = re.search(r'/([^/]+)/(\d+)/(\d+)', url)
    if match:
        shop_name, shop_id, item_id = match.groups()
        print(f"   ✅ Shop: {shop_name}")
        print(f"   ✅ Shop ID: {shop_id}")
        print(f"   ✅ Item ID: {item_id}")
        return shop_id, item_id
    
    print(f"   ⚠️  Não foi possível extrair IDs da URL")
    return None, None


def try_shopee_api(shop_id, item_id):
    """
    Tenta obter dados direto da API da Shopee
    """
    print(f"\n🔌 Tentando API direta da Shopee...")
    
    try:
        # API endpoint da Shopee
        api_url = f"https://shopee.com.br/api/v4/item/get"
        
        params = {
            'shopid': shop_id,
            'itemid': item_id
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://shopee.com.br/'
        }
        
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('error') == 0 and data.get('data'):
                item = data['data']
                
                product_data = {
                    'title': item.get('name', ''),
                    'price': (item.get('price', 0) / 100000) if item.get('price') else 0,
                    'original_price': (item.get('price_before_discount', 0) / 100000) if item.get('price_before_discount') else 0,
                    'stock': item.get('stock', 0),
                    'sold': item.get('sold', 0) or item.get('historical_sold', 0),
                    'rating': 0,
                    'rating_count': 0,
                    'description': item.get('description', ''),
                    'images': [],
                    'condition': 'new'
                }
                
                # Extrair imagens
                if item.get('images'):
                    base_url = "https://down-br.img.susercontent.com/file/"
                    product_data['images'] = [f"{base_url}{img}" for img in item['images'][:10]]
                
                # Extrair avaliação
                if item.get('item_rating'):
                    rating_data = item['item_rating']
                    product_data['rating'] = rating_data.get('rating_star', 0)
                    if rating_data.get('rating_count'):
                        product_data['rating_count'] = rating_data['rating_count'][0] if isinstance(rating_data['rating_count'], list) else rating_data['rating_count']
                
                print(f"   ✅ API: Dados obtidos com sucesso!")
                return product_data
        
        print(f"   ⚠️ API retornou status {response.status_code}")
        return None
        
    except Exception as e:
        print(f"   ⚠️ Erro na API: {e}")
        return None


def scrape_shopee_product(url, shop_id=None, item_id=None):
    """
    Faz scraping da página do produto na Shopee usando Playwright.
    Extrai: título, preço, descrição, imagens, estoque, etc.
    """
    
    print(f"\n📥 Fazendo scraping do produto com Playwright...")
    
    try:
        with sync_playwright() as p:
            # Lançar navegador headless com flags anti-detecção
            print(f"   🚀 Iniciando navegador...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security'
                ]
            )
            
            context = browser.new_context(
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Script anti-detecção
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            page = context.new_page()
            
            # Navegar para a URL
            print(f"   🌐 Carregando página...")
            response = page.goto(url, wait_until='networkidle', timeout=45000)
            
            print(f"   ⏳ Aguardando JavaScript carregar (5s)...")
            page.wait_for_timeout(5000)
            
            # Scroll para ativar lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(2000)
            
            print(f"   ✅ Página carregada, extraindo dados...")
            
            # Extrair dados da página renderizada
            product_data = extract_from_playwright_page(page, shop_id, item_id)
            
            # Verificar se Shopee redirecionou para login
            page_url = page.url
            if 'login' in page_url.lower() or 'buyer/login' in page_url:
                print(f"   🚫 SHOPEE REQUER LOGIN")
                print(f"   ℹ️  A Shopee bloqueou o acesso automatizado e redirecionou para login.")
                print(f"   💡 Alternativa: Copie os dados manualmente do produto")
                print(f"   🌐 URL do produto: {url}")
                return None
            
            # Salvar HTML para debug
            html_content = page.content()
            debug_html_path = Path("/tmp/shopee_playwright_debug.html")
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   🐛 HTML salvo em: {debug_html_path}")
            
            browser.close()
            
            # Verificar se conseguiu dados mínimos
            if product_data and (product_data.get('title') or product_data.get('stock', 0) > 0):
                return product_data
            else:
                print(f"   ⚠️ Dados incompletos, tentando fallback...")
                return scrape_shopee_product_fallback(url, shop_id, item_id)
                
    except Exception as e:
        print(f"   ❌ Erro no Playwright: {e}")
        print(f"   💡 Tentando método fallback...")
        return scrape_shopee_product_fallback(url, shop_id, item_id)


def extract_from_playwright_page(page, shop_id=None, item_id=None):
    """
    Extrai dados do produto da página renderizada pelo Playwright.
    BASEADO NO shopee_update_prices.py QUE JÁ FUNCIONA!
    """
    product_data = {
        'title': '',
        'price': 0,
        'original_price': 0,
        'discount_percent': 0,
        'stock': 0,
        'sold': 0,
        'rating': 0,
        'rating_count': 0,
        'description': '',
        'images': [],
        'condition': 'new'
    }
    
    try:
        # Aguardar um pouco para JavaScript carregar
        page.wait_for_timeout(3000)
        
        # Obter HTML renderizado
        html_content = page.content()
        
        print(f"   📊 Extraindo dados do HTML renderizado...")
        
        # ========================================
        # ESTRATÉGIA PRINCIPAL: PDP_BFF_DATA
        # (Este é o método que FUNCIONA no shopee_update_prices.py)
        # ========================================
        pdp_match = re.search(r'"PDP_BFF_DATA".*?"cachedMap"', html_content, re.DOTALL)
        if pdp_match:
            print(f"   ✅ PDP_BFF_DATA encontrado!")
            json_text = pdp_match.group(0)
            
            # Extrair título
            title_match = re.search(r'"title":"([^"]+)"', json_text)
            if title_match:
                product_data['title'] = title_match.group(1)
                print(f"   ✅ Título: {product_data['title'][:60]}...")
            
            # Extrair preço (Shopee usa price * 100000)
            price_patterns = [
                (r'"price_min":(\d+)', 'price_min'),
                (r'"price_max":(\d+)', 'price_max'),
                (r'"flash_sale"[^}]*"price":(\d+)', 'flash_sale_price'),
                (r'"tier_variations"[^}]*"price":(\d+)', 'tier_price'),
                (r'models.*?"price":(\d+)', 'model_price'),
            ]
            
            for pattern, name in price_patterns:
                matches = re.findall(pattern, json_text)
                if matches:
                    price_cents = int(matches[0])
                    if price_cents > 0:
                        product_data['price'] = price_cents / 100000
                        print(f"   ✅ Preço: R$ {product_data['price']:.2f} ({name})")
                        break
            
            # Extrair preço antigo
            old_price_patterns = [
                r'"price_before_discount":(\d+)',
                r'"original_price":(\d+)',
                r'"show_original_price":(\d+)',
            ]
            
            for pattern in old_price_patterns:
                matches = re.findall(pattern, json_text)
                if matches:
                    price_cents = int(matches[0])
                    if price_cents > 0:
                        product_data['original_price'] = price_cents / 100000
                        if product_data['original_price'] > product_data['price']:
                            print(f"   ✅ Preço antigo: R$ {product_data['original_price']:.2f}")
                        break
            
            # Estoque
            stock_match = re.search(r'"stock":(\d+)', json_text)
            if stock_match:
                product_data['stock'] = int(stock_match.group(1))
                print(f"   ✅ Estoque: {product_data['stock']} unidades")
            
            # Vendidos
            sold_patterns = [r'"sold":(\d+)', r'"historical_sold":(\d+)']
            for pattern in sold_patterns:
                sold_match = re.search(pattern, json_text)
                if sold_match:
                    product_data['sold'] = int(sold_match.group(1))
                    print(f"   ✅ Vendidos: {product_data['sold']}")
                    break
            
            # Avaliação
            rating_match = re.search(r'"rating_star":([\d.]+)', json_text)
            if rating_match:
                product_data['rating'] = float(rating_match.group(1))
                print(f"   ✅ Avaliação: {product_data['rating']}")
        
        # ========================================
        # FALLBACK: Buscar em todo o HTML se PDP_BFF_DATA não funcionou
        # ========================================
        if not product_data.get('title'):
            print(f"   ⚠️ PDP_BFF_DATA não encontrado, tentando regex genérico...")
            
            title_match = re.search(r'"title":"([^"]+)"', html_content)
            if title_match:
                product_data['title'] = title_match.group(1)
                print(f"   ✅ Título: {product_data['title'][:60]}...")
        
        # Estoque (fallback)
        if product_data['stock'] == 0:
            stock_match = re.search(r'"stock":(\d+)', html_content)
            if stock_match:
                product_data['stock'] = int(stock_match.group(1))
                print(f"   ✅ Estoque: {product_data['stock']}")
        
        # Vendidos (fallback)
        if product_data['sold'] == 0:
            for pattern in [r'"sold":(\d+)', r'"historical_sold":(\d+)']:
                sold_match = re.search(pattern, html_content)
                if sold_match:
                    product_data['sold'] = int(sold_match.group(1))
                    print(f"   ✅ Vendidos: {product_data['sold']}")
                    break
        
        # ========================================
        # IMAGENS: Usar o padrão que funciona
        # ========================================
        image_pattern = r'"image":"([a-z0-9\-]+)"'
        image_matches = re.findall(image_pattern, html_content)
        if image_matches:
            base_url = "https://down-br.img.susercontent.com/file/"
            # Pegar apenas imagens únicas
            unique_images = list(dict.fromkeys(image_matches))[:10]
            product_data['images'] = [f"{base_url}{img}" for img in unique_images]
            print(f"   ✅ {len(product_data['images'])} imagens encontradas")
        
        # Verificar se conseguiu dados mínimos
        if not product_data.get('title'):
            print(f"   ⚠️ Título não encontrado - produto pode estar indisponível")
        
        if product_data['price'] == 0:
            print(f"   ⚠️ Preço não encontrado")
        
        return product_data
        
    except Exception as e:
        print(f"   ⚠️ Erro ao extrair dados: {e}")
        return product_data


def parse_shopee_item_data(item):
    """
    Parse de dados do item encontrado no JSON.
    """
    data = {}
    
    # Título
    if 'name' in item:
        data['title'] = item['name']
    
    # Preço (Shopee guarda em centavos * 1000)
    if 'price' in item and item['price']:
        data['price'] = item['price'] / 100000
    
    if 'price_before_discount' in item and item['price_before_discount']:
        data['original_price'] = item['price_before_discount'] / 100000
    
    # Estoque
    if 'stock' in item:
        data['stock'] = item['stock']
    
    # Vendidos
    if 'sold' in item:
        data['sold'] = item['sold']
    elif 'historical_sold' in item:
        data['sold'] = item['historical_sold']
    
    # Avaliação
    if 'item_rating' in item:
        rating_data = item['item_rating']
        if 'rating_star' in rating_data:
            data['rating'] = rating_data['rating_star']
        if 'rating_count' in rating_data:
            data['rating_count'] = rating_data['rating_count'][0] if rating_data['rating_count'] else 0
    
    # Descrição
    if 'description' in item:
        data['description'] = item['description']
    
    # Imagens
    if 'images' in item:
        data['images'] = [f"https://cf.shopee.com.br/file/{img}" for img in item['images']]
    elif 'image' in item:
        data['images'] = [f"https://cf.shopee.com.br/file/{item['image']}"]
    
    return data


def find_item_in_json(data, depth=0, max_depth=5):
    """
    Procura recursivamente por dados do produto no JSON.
    """
    if depth > max_depth:
        return None
    
    if isinstance(data, dict):
        # Procurar por campos típicos de produto
        if 'itemid' in data and 'name' in data:
            return data
        
        # Chaves comuns onde os dados podem estar
        common_keys = ['item', 'product', 'itemDetail', 'productDetail', 'data']
        for key in common_keys:
            if key in data:
                result = find_item_in_json(data[key], depth + 1, max_depth)
                if result:
                    return result
        
        # Busca genérica
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result = find_item_in_json(value, depth + 1, max_depth)
                if result:
                    return result
    
    elif isinstance(data, list) and len(data) > 0:
        # Tentar o primeiro item da lista
        return find_item_in_json(data[0], depth + 1, max_depth)
    
    return None


def scrape_shopee_product_fallback(url, shop_id=None, item_id=None):
    """
    Faz scraping da página do produto na Shopee.
    Extrai: título, preço, descrição, imagens, estoque, etc.
    """
    print(f"\n📥 Fazendo scraping do produto...")
    
    # Se temos shop_id e item_id, podemos tentar usar a API pública diretamente
    if shop_id and item_id:
        print(f"   💡 Tentando API pública da Shopee...")
        api_data = try_shopee_api(shop_id, item_id)
        if api_data:
            return api_data
    
    # Fallback: scraping do HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    print(f"   📄 Fazendo scraping da página HTML...")
    
    try:
        # Remover parâmetros mobile para obter versão desktop
        clean_url = url.split('?')[0] if '?' in url else url
        
        response = requests.get(clean_url, headers=headers, timeout=20, allow_redirects=True)
        response.raise_for_status()
        
        print(f"   ✅ Página carregada com sucesso (status: {response.status_code})")
        
        # Debug: salvar HTML em caso de falha
        debug_html_path = Path("/tmp/shopee_debug.html")
        with open(debug_html_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"   🐛 HTML salvo em: {debug_html_path}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # A Shopee carrega dados via JavaScript, então procuramos pelo JSON embutido
        # O produto está em <script> tags com dados JSON
        product_data = {}
        
        # Procurar por JSON de dados do produto
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '__INITIAL_STATE__' in script.string:
                # Extrair JSON do estado inicial
                json_text = script.string
                # O JSON geralmente está entre __INITIAL_STATE__= e </script>
                start = json_text.find('{')
                end = json_text.rfind('}') + 1
                if start != -1 and end != 0:
                    try:
                        initial_state = json.loads(json_text[start:end])
                        
                        # Navegar pela estrutura para encontrar dados do produto
                        # A estrutura pode variar, mas geralmente está em item_detail ou similar
                        if 'item' in initial_state:
                            item = initial_state['item']
                        elif 'itemDetail' in initial_state:
                            item = initial_state['itemDetail']
                        else:
                            # Procurar recursivamente
                            item = find_item_in_json(initial_state)
                        
                        if item:
                            product_data = parse_shopee_item(item)
                            break
                    except json.JSONDecodeError:
                        continue
        
        # Fallback: tentar extrair do HTML se não encontrou no JSON
        if not product_data or not product_data.get('title'):
            product_data = scrape_from_html(soup)
        
        return product_data
    
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro ao fazer scraping: {e}")
        return None


def try_shopee_api(shop_id, item_id):
    """
    Tenta usar a API pública/interna da Shopee para obter dados do produto.
    Esta API não requer autenticação para consultas básicas.
    """
    try:
        # URL da API pública da Shopee (usada pelo próprio site)
        api_url = f"https://shopee.com.br/api/v4/item/get?shopid={shop_id}&itemid={item_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://shopee.com.br/',
            'Accept': 'application/json',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data and 'data' in data and data['data']:
                item = data['data']
                print(f"   ✅ Dados obtidos via API pública!")
                return parse_shopee_item(item)
        
        print(f"   ⚠️  API pública não disponível (status: {response.status_code}), continuando com HTML...")
        return None
    
    except Exception as e:
        print(f"   ⚠️  Erro ao tentar API pública: {e}, continuando com HTML...")
        return None



def scrape_from_html(soup):
    """
    Fallback: tenta extrair dados do HTML quando JSON não está disponível.
    """
    print(f"   ⚠️  JSON não encontrado, tentando extrair do HTML...")
    
    product_data = {
        'title': '',
        'price': 0,
        'original_price': 0,
        'description': '',
        'images': [],
        'stock': 0,
        'sold': 0,
        'rating': 0,
        'rating_count': 0,
    }
    
    # Título geralmente está em meta tags
    title_meta = soup.find('meta', property='og:title')
    if title_meta:
        product_data['title'] = title_meta.get('content', '')
        print(f"   ✅ Título encontrado: {product_data['title'][:50]}...")
    
    # Tentar extrair título do HTML se não encontrou em meta
    if not product_data['title']:
        title_elem = soup.find('h1') or soup.find('span', class_=re.compile('title|name', re.I))
        if title_elem:
            product_data['title'] = title_elem.get_text(strip=True)
            print(f"   ✅ Título (HTML): {product_data['title'][:50]}...")
    
    # Preço em meta tags
    price_meta = soup.find('meta', property='product:price:amount')
    if price_meta:
        try:
            product_data['price'] = float(price_meta.get('content', 0))
            print(f"   ✅ Preço encontrado: R$ {product_data['price']:.2f}")
        except ValueError:
            pass
    
    # Tentar extrair preço do HTML
    if not product_data['price']:
        # Procurar por elementos com classe relacionada a preço
        price_elems = soup.find_all(class_=re.compile('price|valor', re.I))
        for elem in price_elems:
            text = elem.get_text(strip=True)
            # Extrair números do texto (formato: R$ 49,99 ou 49.99)
            price_match = re.search(r'[\d.,]+', text.replace('.', '').replace(',', '.'))
            if price_match:
                try:
                    price_value = float(price_match.group().replace(',', '.'))
                    if price_value > 0:
                        product_data['price'] = price_value
                        print(f"   ✅ Preço (HTML): R$ {price_value:.2f}")
                        break
                except ValueError:
                    continue
    
    # Imagens
    image_metas = soup.find_all('meta', property='og:image')
    for img_meta in image_metas:
        img_url = img_meta.get('content')
        if img_url and img_url not in product_data['images']:
            product_data['images'].append(img_url)
    
    # Procurar imagens no HTML também
    if not product_data['images']:
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and 'shopee' in src and src not in product_data['images']:
                # Garantir que é URL completa
                if not src.startswith('http'):
                    src = 'https:' + src if src.startswith('//') else 'https://cf.shopee.com.br/file/' + src
                product_data['images'].append(src)
    
    if product_data['images']:
        print(f"   ✅ Imagens encontradas: {len(product_data['images'])}")
    
    # Descrição
    desc_meta = soup.find('meta', property='og:description')
    if desc_meta:
        product_data['description'] = desc_meta.get('content', '')
    
    if not product_data['description']:
        desc_elem = soup.find(class_=re.compile('description|desc', re.I))
        if desc_elem:
            product_data['description'] = desc_elem.get_text(strip=True)[:500]
    
    return product_data


def download_images(image_urls, product_slug, base_path="/app/uploads"):
    """
    Baixa imagens do produto.
    Retorna o diretório e lista de arquivos baixados.
    """
    product_dir = Path(base_path) / product_slug
    product_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📥 Baixando {len(image_urls)} imagens...")
    
    downloaded = []
    total_size = 0
    
    for i, img_url in enumerate(image_urls, 1):
        try:
            response = requests.get(img_url, timeout=15)
            response.raise_for_status()
            
            # Salva a imagem
            img_filename = f"image_{i}.jpg"
            img_path = product_dir / img_filename
            
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            total_size += file_size
            downloaded.append(str(img_path))
            
            print(f"   ✅ [{i}/{len(image_urls)}] {img_filename} ({file_size / 1024:.1f} KB)")
        
        except Exception as e:
            print(f"   ❌ [{i}/{len(image_urls)}] Erro: {e}")
    
    print(f"\n📊 Total baixado: {total_size / 1024 / 1024:.2f} MB")
    print(f"📂 Diretório: {product_dir}")
    
    return str(product_dir), downloaded


def create_product_json(product_data, product_dir, original_url, tag="geral", subcategory=""):
    """
    Cria JSON do produto no formato padrão do sistema.
    Salva na pasta staging/TAG/SUBCATEGORY/
    """
    # Gera slug do nome do produto
    product_slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Nome do arquivo JSON
    json_filename = f"{product_slug}_{timestamp}.json"
    
    # Mapear tags para nomes de pasta
    tag_folders = {
        "E": "eletronicos",
        "CD": "casa-decoracao",
        "ME": "moda-estilo",
        "PET": "pet",
        "geral": "geral"
    }
    
    tag_folder = tag_folders.get(tag.upper(), "geral")
    
    # Determinar caminho do JSON
    if subcategory:
        staging_dir = Path(f"/app/staging/{tag_folder}/{subcategory}")
    else:
        staging_dir = Path(f"/app/staging/{tag_folder}")
    
    staging_dir.mkdir(parents=True, exist_ok=True)
    json_path = staging_dir / json_filename
    
    # External ID: shop_id-item_id
    external_id = f"{product_data.get('shop_id', '')}-{product_data.get('item_id', '')}"
    
    # Formatar preços no formato "R$ X"
    price_value = product_data['price']
    old_price_value = product_data.get('original_price', price_value)
    
    price_str = f"R$ {price_value:.0f}" if price_value == int(price_value) else f"R$ {price_value:.2f}"
    old_price_str = f"R$ {old_price_value:.0f}" if old_price_value == int(old_price_value) else f"R$ {old_price_value:.2f}"
    
    # Estrutura do JSON no formato padrão
    product_json = {
        "platform": "shopee",
        "external_id": external_id,
        "title": product_data['title'],
        "price": price_str,
        "oldPrice": old_price_str,
        "images_local": str(product_dir).replace('/app/', ''),
        "images": [],
        "link": original_url,
        "tag": tag.upper(),
        "subcategory": subcategory,
        "disponivel": product_data.get('stock', 0) > 0,
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    # Salvar JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(product_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 JSON salvo:")
    print(f"   📄 {json_path}")
    
    return json_path, product_json


def main():
    """
    Função principal: prepara produto da Shopee.
    """
    if len(sys.argv) < 2:
        print("❌ Uso: python shopee_prepare.py <URL_DO_PRODUTO>")
        sys.exit(1)
    
    original_url = sys.argv[1]
    
    print("="*70)
    print("🛍️  PREPARAÇÃO DE PRODUTO DA SHOPEE")
    print("="*70)
    
    # 1. Resolver link (se for afiliado ou encurtado)
    final_url = resolve_shopee_link(original_url)
    
    # 2. Extrair IDs do produto
    shop_id, item_id = extract_product_ids(final_url)
    
    # 3. Fazer scraping do produto
    product_data = scrape_shopee_product(final_url, shop_id, item_id)
    
    if not product_data or not product_data.get('title'):
        print("\n❌ Não foi possível coletar dados do produto!")
        print("💡 Verifique se a URL está correta e acessível.")
        sys.exit(1)
    
    # 4. Adicionar IDs ao product_data
    if shop_id and item_id:
        product_data['shop_id'] = shop_id
        product_data['item_id'] = item_id
    
    # ============================================================
    # MOSTRAR INFORMAÇÕES COLETADAS
    # ============================================================
    print("\n" + "="*70)
    print("📊 INFORMAÇÕES COLETADAS DO PRODUTO")
    print("="*70)
    print(f"\n📦 Título: {product_data.get('title', 'N/A')}")
    
    # Preço atual
    price = product_data.get('price', 0)
    if price > 0:
        print(f"💰 Preço Atual: R$ {price:.2f}")
    else:
        print(f"💰 Preço Atual: ❌ Não encontrado")
    
    # Preço promocional/antigo
    old_price = product_data.get('original_price', 0)
    if old_price > 0 and old_price > price:
        discount = ((old_price - price) / old_price) * 100
        print(f"🔥 Preço Antigo: R$ {old_price:.2f} (-{discount:.0f}%)")
    else:
        print(f"🔥 Preço Antigo: ❌ Não encontrado")
    
    # Estoque e disponibilidade
    stock = product_data.get('stock', 0)
    is_available = stock > 0
    print(f"📊 Disponibilidade: {'✅ Disponível' if is_available else '❌ Indisponível'}")
    if stock > 0:
        print(f"📦 Estoque: {stock} unidades")
    
    # Vendidos
    sold = product_data.get('sold', 0)
    if sold > 0:
        print(f"🛒 Vendidos: {sold} unidades")
    
    # Avaliações
    rating = product_data.get('rating', 0)
    rating_count = product_data.get('rating_count', 0)
    if rating > 0:
        stars = "⭐" * int(rating)
        print(f"⭐ Avaliação: {stars} ({rating}/5.0) - {rating_count} avaliações")
    
    # Imagens
    images_count = len(product_data.get('images', []))
    print(f"🖼️  Imagens: {images_count} encontradas")
    
    print("="*70)
    
    # ============================================================
    # PERGUNTAR SE OS PREÇOS ESTÃO CORRETOS
    # ============================================================
    print("\n" + "="*70)
    print("💰 VERIFICAÇÃO DE PREÇOS")
    print("="*70)
    
    # Se não encontrou preço, pedir manualmente
    if price <= 0:
        print("\n⚠️  O preço atual não foi encontrado automaticamente.")
        while True:
            price_input = input("💰 Digite o preço atual (ex: 49.99): ").strip()
            try:
                price = float(price_input.replace(',', '.'))
                if price > 0:
                    product_data['price'] = price
                    break
                else:
                    print("   ❌ Preço deve ser maior que zero!")
            except ValueError:
                print("   ❌ Preço inválido! Use formato: 49.99")
    else:
        # Perguntar se quer alterar o preço encontrado
        confirm = input(f"\nℹ️  O preço encontrado (R$ {price:.2f}) está correto? (s/n): ").strip().lower()
        if confirm == 'n':
            while True:
                price_input = input("💰 Digite o preço correto (ex: 49.99): ").strip()
                try:
                    price = float(price_input.replace(',', '.'))
                    if price > 0:
                        product_data['price'] = price
                        break
                    else:
                        print("   ❌ Preço deve ser maior que zero!")
                except ValueError:
                    print("   ❌ Preço inválido! Use formato: 49.99")
    
    # Se não encontrou preço antigo, perguntar se tem
    if old_price <= 0 or old_price <= price:
        old_price_input = input("\n🔥 Tem preço antigo/promocional? (deixe vazio se não): ").strip()
        if old_price_input:
            try:
                old_price = float(old_price_input.replace(',', '.'))
                if old_price > price:
                    product_data['original_price'] = old_price
                else:
                    print("   ⚠️  Preço antigo deve ser maior que o atual. Ignorando...")
                    old_price = 0
            except ValueError:
                print("   ⚠️  Preço antigo inválido. Ignorando...")
                old_price = 0
    else:
        # Perguntar se quer alterar o preço antigo encontrado
        confirm = input(f"\nℹ️  O preço antigo encontrado (R$ {old_price:.2f}) está correto? (s/n): ").strip().lower()
        if confirm == 'n':
            old_price_input = input("🔥 Digite o preço antigo correto (ou deixe vazio): ").strip()
            if old_price_input:
                try:
                    old_price = float(old_price_input.replace(',', '.'))
                    if old_price > price:
                        product_data['original_price'] = old_price
                    else:
                        print("   ⚠️  Preço antigo deve ser maior que o atual. Ignorando...")
                        old_price = 0
                except ValueError:
                    print("   ⚠️  Preço antigo inválido. Ignorando...")
                    old_price = 0
    
    # ============================================================
    # PERGUNTAR CATEGORIA
    # ============================================================
    print("\n" + "="*70)
    print("📂 CATEGORIZAÇÃO DO PRODUTO")
    print("="*70)
    print("\n📂 CATEGORIAS DISPONÍVEIS:")
    print("   1. E   - Eletrônicos")
    print("   2. CD  - Casa & Decoração")
    print("   3. ME  - Moda & Estilo")
    print("   4. PET - Pet Shop")
    print("   5. ES  - Esportes")
    
    # Mapear entrada para tag
    tag_map = {
        "1": "E",
        "2": "CD",
        "3": "ME",
        "4": "PET",
        "5": "ES",
        "E": "E",
        "CD": "CD",
        "ME": "ME",
        "PET": "PET",
        "ES": "ES"
    }
    
    # Pedir categoria
    while True:
        tag_input = input("\n🏷️  Digite a categoria (1/2/3/4/5 ou E/CD/ME/PET/ES): ").strip().upper()
        tag = tag_map.get(tag_input)
        if tag:
            break
        print("   ❌ Categoria inválida! Use: 1, 2, 3, 4, 5 ou E, CD, ME, PET, ES")
    
    print(f"\n✅ Categoria selecionada: {tag}")
    
    # Sugestões de subcategoria baseada na categoria
    subcategory_suggestions = {
        "CD": "area-servico, quarto, banheiro, cozinha, sala, organizacao",
        "E": "eletrodomesticos, informatica, celulares, audio, games",
        "ME": "roupas, calcados, acessorios, bolsas, joias",
        "PET": "caes, gatos, aquarios, passaros, roedores",
        "ES": "futebol, corrida, academia, natacao, ciclismo, tenis, esportes-radicais, acessorios"
    }
    
    print(f"\n💡 Subcategorias sugeridas para {tag}:")
    print(f"   {subcategory_suggestions.get(tag, 'N/A')}")
    
    subcategory = input("\n📁 Digite a subcategoria: ").strip().lower()
    if subcategory:
        print(f"✅ Subcategoria: {subcategory}")
    else:
        subcategory = ""
        print("⚠️  Nenhuma subcategoria definida")
    
    # ============================================================
    # DOWNLOAD DE IMAGENS
    # ============================================================
    print("\n" + "="*70)
    print("🖼️  DOWNLOAD DE IMAGENS")
    print("="*70)
    
    if product_data.get('images'):
        product_slug = slugify(product_data['title'])
        product_dir, downloaded_images = download_images(
            product_data['images'],
            product_slug
        )
    else:
        print("\n⚠️  Nenhuma imagem encontrada!")
        product_dir = ""
        downloaded_images = []
    
    # ============================================================
    # CRIAR JSON
    # ============================================================
    print("\n" + "="*70)
    print("📝 CRIANDO ARQUIVO JSON")
    print("="*70)
    
    json_path, product_json = create_product_json(
        product_data,
        product_dir,
        original_url,
        tag,
        subcategory
    )
    
    # ============================================================
    # RESUMO FINAL
    # ============================================================
    print("\n" + "="*70)
    print("✅ PREPARAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)
    print(f"\n✅ JSON criado: {json_path.name}")
    print(f"📂 Categoria: {product_json['tag']} / {product_json.get('subcategory', 'N/A')}")
    print(f"📦 Produto: {product_json['title']}")
    print(f"💰 Preço: R$ {product_json['price']:.2f}")
    if product_json['oldPrice'] > product_json['price']:
        discount = ((product_json['oldPrice'] - product_json['price']) / product_json['oldPrice']) * 100
        print(f"🔥 Preço antigo: R$ {product_json['oldPrice']:.2f} (-{discount:.0f}%)")
    print(f"📊 Disponível: {'Sim' if product_json['disponivel'] else 'Não'}")
    print(f"🖼️  Imagens: {len(downloaded_images)} baixadas")
    print(f"🔗 Link: {original_url}")
    print(f"📁 Pasta: {json_path.parent}")
    print("\n" + "="*70)
    print("🎯 Próximo passo: Use 'make stage-product' para adicionar ao staging!")
    print("="*70)


if __name__ == "__main__":
    main()
