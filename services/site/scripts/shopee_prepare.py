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
    
    print(f"   ⚠️  Não foi possível extrair IDs da URL")
    return None, None


def scrape_shopee_product(url):
    """
    Faz scraping da página do produto na Shopee.
    Extrai: título, preço, descrição, imagens, estoque, etc.
    """
    print(f"\n📥 Fazendo scraping do produto...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
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
        if not product_data:
            product_data = scrape_from_html(soup)
        
        return product_data
    
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro ao fazer scraping: {e}")
        return None


def find_item_in_json(data, depth=0, max_depth=5):
    """
    Procura recursivamente por dados do produto no JSON.
    """
    if depth > max_depth:
        return None
    
    if isinstance(data, dict):
        # Procurar por campos típicos de produto
        if 'itemid' in data and 'name' in data and 'price' in data:
            return data
        
        for key, value in data.items():
            result = find_item_in_json(value, depth + 1, max_depth)
            if result:
                return result
    
    elif isinstance(data, list):
        for item in data:
            result = find_item_in_json(item, depth + 1, max_depth)
            if result:
                return result
    
    return None


def parse_shopee_item(item):
    """
    Parse dos dados do item da Shopee extraídos do JSON.
    """
    print(f"   ✅ Dados encontrados no JSON da página!")
    
    product_data = {
        'title': item.get('name', ''),
        'price': item.get('price', 0) / 100000,  # Shopee armazena preço em centavos * 1000
        'original_price': item.get('price_before_discount', 0) / 100000,
        'description': item.get('description', ''),
        'stock': item.get('stock', 0),
        'sold': item.get('sold', 0),
        'rating': item.get('item_rating', {}).get('rating_star', 0),
        'rating_count': item.get('item_rating', {}).get('rating_count', [0])[0] if item.get('item_rating') else 0,
        'images': [],
        'shop_id': item.get('shopid', ''),
        'item_id': item.get('itemid', ''),
        'condition': 'new' if item.get('is_cc_installment_payment_eligible') else 'new',
    }
    
    # Extrair URLs das imagens
    images = item.get('images', [])
    if images:
        base_img_url = 'https://cf.shopee.com.br/file/'
        product_data['images'] = [f"{base_img_url}{img}" for img in images]
    
    # Calcular desconto
    if product_data['original_price'] > 0 and product_data['original_price'] > product_data['price']:
        discount_percent = ((product_data['original_price'] - product_data['price']) / product_data['original_price']) * 100
        product_data['discount_percent'] = round(discount_percent, 2)
    else:
        product_data['discount_percent'] = 0
    
    print(f"   📦 Produto: {product_data['title']}")
    print(f"   💰 Preço: R$ {product_data['price']:.2f}")
    if product_data['discount_percent'] > 0:
        print(f"   🔥 Desconto: {product_data['discount_percent']}%")
    print(f"   📊 Estoque: {product_data['stock']}")
    print(f"   🛒 Vendidos: {product_data['sold']}")
    print(f"   ⭐ Avaliação: {product_data['rating']} ({product_data['rating_count']} avaliações)")
    print(f"   🖼️  Imagens: {len(product_data['images'])}")
    
    return product_data


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
    }
    
    # Título geralmente está em meta tags
    title_meta = soup.find('meta', property='og:title')
    if title_meta:
        product_data['title'] = title_meta.get('content', '')
    
    # Preço em meta tags
    price_meta = soup.find('meta', property='product:price:amount')
    if price_meta:
        try:
            product_data['price'] = float(price_meta.get('content', 0))
        except ValueError:
            pass
    
    # Imagens
    image_metas = soup.find_all('meta', property='og:image')
    for img_meta in image_metas:
        img_url = img_meta.get('content')
        if img_url and img_url not in product_data['images']:
            product_data['images'].append(img_url)
    
    # Descrição
    desc_meta = soup.find('meta', property='og:description')
    if desc_meta:
        product_data['description'] = desc_meta.get('content', '')
    
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


def create_product_json(product_data, product_dir, original_url):
    """
    Cria JSON do produto no formato esperado pelo sistema.
    Similar ao formato usado para produtos do Mercado Livre.
    """
    # Gera slug do nome do produto
    product_slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Nome do arquivo JSON
    json_filename = f"{product_slug}_{timestamp}.json"
    json_path = Path("/app/list_to_prepare_and_stage/list_to_prepare.json")
    
    # Determinar categoria (pode ser melhorado com lógica mais sofisticada)
    category = "geral"
    
    # Estrutura do JSON
    product_json = {
        "nome_produto": product_data['title'],
        "descricao": product_data.get('description', ''),
        "preco": product_data['price'],
        "preco_original": product_data.get('original_price', product_data['price']),
        "desconto_percentual": product_data.get('discount_percent', 0),
        "estoque": product_data.get('stock', 0),
        "vendidos": product_data.get('sold', 0),
        "avaliacao": product_data.get('rating', 0),
        "total_avaliacoes": product_data.get('rating_count', 0),
        "categoria": category,
        "origem": "shopee",
        "shop_id": product_data.get('shop_id', ''),
        "item_id": product_data.get('item_id', ''),
        "condicao": product_data.get('condition', 'new'),
        "link_original": original_url,
        "pasta_imagens": str(product_dir),
        "timestamp": timestamp,
        "data_coleta": datetime.now().isoformat()
    }
    
    # Salvar JSON individual
    individual_json_path = Path("/app/list_to_prepare_and_stage") / json_filename
    individual_json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(individual_json_path, 'w', encoding='utf-8') as f:
        json.dump(product_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 JSON individual salvo:")
    print(f"   📄 {individual_json_path}")
    
    # Adicionar à lista de preparação (se o arquivo existir)
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                product_list = json.load(f)
            
            if not isinstance(product_list, list):
                product_list = []
        except Exception:
            product_list = []
    else:
        product_list = []
    
    product_list.append(product_json)
    
    # Salvar lista atualizada
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(product_list, f, indent=2, ensure_ascii=False)
    
    return individual_json_path, product_json


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
    product_data = scrape_shopee_product(final_url)
    
    if not product_data or not product_data.get('title'):
        print("\n❌ Não foi possível coletar dados do produto!")
        print("💡 Verifique se a URL está correta e acessível.")
        sys.exit(1)
    
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
        original_url
    )
    
    # 7. Resumo final
    print("\n" + "="*70)
    print("✅ PREPARAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)
    print(f"\n✅ JSON criado: {json_path.name}")
    print(f"📂 Categoria: {product_json['categoria']}")
    print(f"📦 Produto: {product_json['nome_produto']}")
    print(f"💰 Preço: R$ {product_json['preco']:.2f}")
    if product_json['desconto_percentual'] > 0:
        print(f"🔥 Desconto: {product_json['desconto_percentual']}%")
    print(f"📊 Estoque: {product_json['estoque']}")
    print(f"🛒 Vendidos: {product_json['vendidos']}")
    if product_json['avaliacao'] > 0:
        print(f"⭐ Avaliação: {product_json['avaliacao']}/5 ({product_json['total_avaliacoes']} avaliações)")
    print(f"🖼️  Imagens: {product_dir} ({len(downloaded_images)} imagens)")
    print(f"🔗 Link: {original_url}")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
