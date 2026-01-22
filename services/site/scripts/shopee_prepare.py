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


def scrape_shopee_product(url, shop_id=None, item_id=None):
    """
    Faz scraping da página do produto na Shopee usando Playwright.
    Extrai: título, preço, descrição, imagens, estoque, etc.
    """
    print(f"\n📥 Fazendo scraping do produto com Playwright...")
    
    try:
        with sync_playwright() as p:
            # Lançar navegador headless
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Navegar para a URL
            print(f"   🌐 Carregando página...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Aguardar JavaScript renderizar
            page.wait_for_timeout(3000)
            
            print(f"   ✅ Página carregada com sucesso")
            
            # Extrair dados da página renderizada
            product_data = extract_from_playwright_page(page)
            
            # Salvar HTML para debug
            html_content = page.content()
            debug_html_path = Path("/tmp/shopee_playwright_debug.html")
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   🐛 HTML renderizado salvo em: {debug_html_path}")
            
            browser.close()
            
            if product_data and product_data.get('title'):
                return product_data
            else:
                print("   ⚠️ Não foi possível extrair dados completos")
                return product_data
                
    except Exception as e:
        print(f"   ❌ Erro no Playwright: {e}")
        print(f"   💡 Tentando scraping HTML simples como fallback...")
        return scrape_shopee_product_fallback(url, shop_id, item_id)


def extract_from_playwright_page(page):
    """
    Extrai dados do produto da página renderizada pelo Playwright.
    Baseado na lógica do shopee_update_prices.py que funciona.
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
        # Aguardar JavaScript carregar
        page.wait_for_timeout(3000)
        
        # Obter HTML renderizado
        html_content = page.content()
        
        print(f"   📊 Extraindo dados do HTML...")
        
        # Estratégia 1: Extrair título
        title_match = re.search(r'"title":"([^"]+)"', html_content)
        if title_match:
            product_data['title'] = title_match.group(1)
            print(f"   ✅ Título: {product_data['title'][:60]}...")
        
        # Estratégia 2: Extrair estoque
        stock_match = re.search(r'"stock":(\d+)', html_content)
        if stock_match:
            product_data['stock'] = int(stock_match.group(1))
            print(f"   ✅ Estoque: {product_data['stock']}")
        
        # Estratégia 3: Extrair vendidos
        sold_patterns = [
            r'"sold":(\d+)',
            r'"historical_sold":(\d+)',
        ]
        for pattern in sold_patterns:
            sold_match = re.search(pattern, html_content)
            if sold_match:
                product_data['sold'] = int(sold_match.group(1))
                print(f"   ✅ Vendidos: {product_data['sold']}")
                break
        
        # Estratégia 4: Extrair imagens
        image_pattern = r'"image":"([a-z0-9\-]+)"'
        image_matches = re.findall(image_pattern, html_content)
        if image_matches:
            base_url = "https://down-br.img.susercontent.com/file/"
            # Pegar apenas imagens únicas
            unique_images = list(dict.fromkeys(image_matches))[:10]
            product_data['images'] = [f"{base_url}{img}" for img in unique_images]
            print(f"   ✅ {len(product_data['images'])} imagens encontradas")
        
        # Estratégia 5: Verificar disponibilidade
        unavailable_texts = ['esgotado', 'sold out', 'indisponível', 'faça login']
        page_text = html_content.lower()
        is_available = not any(text in page_text for text in unavailable_texts)
        
        if not is_available:
            product_data['stock'] = 0
            print(f"   ⚠️ Produto indisponível ou acesso bloqueado")
        
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
        print("❌ Uso: python shopee_prepare.py <URL_DO_PRODUTO> [PRECO] [PRECO_ANTIGO] [TAG] [SUBCATEGORY]")
        sys.exit(1)
    
    original_url = sys.argv[1]
    
    # Preços manuais (opcionais)
    manual_price = None
    manual_old_price = None
    tag = "geral"
    subcategory = ""
    
    if len(sys.argv) > 2 and sys.argv[2].strip():
        try:
            manual_price = float(sys.argv[2].replace(',', '.'))
            print(f"💰 Preço manual informado: R$ {manual_price:.2f}")
        except ValueError:
            print(f"⚠️  Preço inválido: {sys.argv[2]}")
    
    if len(sys.argv) > 3 and sys.argv[3].strip():
        try:
            manual_old_price = float(sys.argv[3].replace(',', '.'))
            print(f"💸 Preço antigo manual informado: R$ {manual_old_price:.2f}")
        except ValueError:
            print(f"⚠️  Preço antigo inválido: {sys.argv[3]}")
    
    if len(sys.argv) > 4 and sys.argv[4].strip():
        tag_input = sys.argv[4].strip().upper()
        
        # Converter número para tag
        tag_map = {
            "1": "E",
            "2": "CD",
            "3": "ME",
            "4": "PET"
        }
        
        tag = tag_map.get(tag_input, tag_input)
        
        # Validar tag
        if tag not in ["E", "CD", "ME", "PET"]:
            print(f"⚠️  Tag inválida: {tag_input}")
            print(f"💡 Use: 1/E (Eletrônicos), 2/CD (Casa), 3/ME (Moda), 4/PET")
            tag = "E"  # Padrão
        
        print(f"🏷️  Tag: {tag}")
    
    if len(sys.argv) > 5 and sys.argv[5].strip():
        subcategory = sys.argv[5].strip().lower()
        print(f"📁 Subcategoria: {subcategory}")
    
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
    
    # Substituir preços com valores manuais se fornecidos
    if manual_price is not None:
        product_data['price'] = manual_price
    
    if manual_old_price is not None:
        product_data['original_price'] = manual_old_price
    
    # Se temos old_price mas não temos price normal, avisar
    if product_data.get('price', 0) == 0 and manual_price is None:
        print("\n⚠️  ATENÇÃO: Preço atual não foi encontrado e não foi informado manualmente!")
        print("💡 O produto será criado com preço R$ 0.00")
    
    # 4. Adicionar IDs ao product_data
    if shop_id and item_id:
        product_data['shop_id'] = shop_id
        product_data['item_id'] = item_id
    
    # 5. Download de imagens
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
    
    # 6. Criar JSON
    json_path, product_json = create_product_json(
        product_data,
        product_dir,
        original_url,
        tag,
        subcategory
    )
    
    # 7. Resumo final
    print("\n" + "="*70)
    print("✅ PREPARAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)
    print(f"\n✅ JSON criado: {json_path.name}")
    print(f"📂 Categoria: {product_json['tag']} / {product_json.get('subcategory', 'N/A')}")
    print(f"📦 Produto: {product_json['title']}")
    print(f"💰 Preço: {product_json['price']}")
    if product_json['oldPrice'] != product_json['price']:
        print(f"🔥 Preço antigo: {product_json['oldPrice']}")
    print(f"📊 Disponível: {'Sim' if product_json['disponivel'] else 'Não'}")
    print(f"🖼️  Imagens: {product_dir} ({len(downloaded_images)} imagens)")
    print(f"🔗 Link: {original_url}")
    print(f"📁 Pasta: {json_path.parent}")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
