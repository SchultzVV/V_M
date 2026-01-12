#!/usr/bin/env python3
"""
Script para preparar produtos automaticamente do Mercado Livre.
Faz scraping do link, baixa imagens e gera o JSON de staging.

Uso:
    python scripts/auto_prepare_ml.py https://mercadolivre.com/sec/ABC123
"""

import os
import sys
import json
import requests
from datetime import datetime
from slugify import slugify
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re

def extract_ml_product_id(url):
    """Extrai o ID do produto do Mercado Livre da URL."""
    # Tenta pegar da URL direta: https://produto.mercadolivre.com.br/MLB-123456789-...
    match = re.search(r'ML[A-Z]-(\d+)', url)
    if match:
        return f"ML{match.group(0)[2]}-{match.group(1)}"
    
    # Tenta seguir redirect de link curto
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        final_url = response.url
        match = re.search(r'ML[A-Z]-(\d+)', final_url)
        if match:
            return match.group(0)
    except:
        pass
    
    return None

def scrape_mercadolivre_product(url):
    """
    Faz scraping dos dados do produto no Mercado Livre.
    Retorna dict com: title, price, old_price, images, external_id
    """
    print(f"🔍 Buscando informações do produto...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Seguir redirects para pegar a URL final
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Extrair ID do produto
        external_id = extract_ml_product_id(response.url)
        
        # Tentar usar a API do Mercado Livre se tivermos o ID
        if external_id:
            try:
                api_url = f"https://api.mercadolibre.com/items/{external_id}"
                api_response = requests.get(api_url, timeout=10)
                if api_response.status_code == 200:
                    data = api_response.json()
                    
                    title = data.get('title', '')
                    price = data.get('price', 0)
                    old_price = data.get('original_price') or price
                    
                    # Pegar imagens
                    images = []
                    pictures = data.get('pictures', [])
                    for pic in pictures:
                        img_url = pic.get('secure_url') or pic.get('url')
                        if img_url:
                            images.append(img_url)
                    
                    print(f"✅ Dados obtidos via API do Mercado Livre")
                    print(f"📦 Produto: {title}")
                    print(f"💰 Preço: R$ {price}")
                    print(f"🖼️  Imagens encontradas: {len(images)}")
                    
                    return {
                        'title': title,
                        'price': f"R$ {price:.2f}",
                        'old_price': f"R$ {old_price:.2f}",
                        'images': images,
                        'external_id': external_id
                    }
            except Exception as e:
                print(f"⚠️  Falha na API, tentando scraping HTML: {e}")
        
        # Fallback: scraping HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Título
        title_tag = soup.find('h1', class_='ui-pdp-title')
        title = title_tag.text.strip() if title_tag else "Produto Mercado Livre"
        
        # Preço
        price_tag = soup.find('span', class_='andes-money-amount__fraction')
        price_text = price_tag.text.strip() if price_tag else "0.00"
        price = f"R$ {price_text}"
        
        # Preço antigo (se houver)
        old_price_tag = soup.find('s', class_='andes-money-amount--previous')
        if old_price_tag:
            old_price_fraction = old_price_tag.find('span', class_='andes-money-amount__fraction')
            old_price = f"R$ {old_price_fraction.text.strip()}" if old_price_fraction else price
        else:
            old_price = price
        
        # Imagens
        images = []
        img_tags = soup.find_all('img', class_='ui-pdp-image')
        for img in img_tags:
            img_url = img.get('src') or img.get('data-src')
            if img_url and img_url.startswith('http'):
                # Pegar versão em alta resolução
                img_url = img_url.replace('-I.jpg', '-O.jpg')
                images.append(img_url)
        
        # Remover duplicatas mantendo ordem
        images = list(dict.fromkeys(images))
        
        print(f"✅ Dados obtidos via scraping HTML")
        print(f"📦 Produto: {title}")
        print(f"💰 Preço: {price}")
        print(f"🖼️  Imagens encontradas: {len(images)}")
        
        return {
            'title': title,
            'price': price,
            'old_price': old_price,
            'images': images,
            'external_id': external_id
        }
        
    except Exception as e:
        print(f"❌ Erro ao fazer scraping: {e}")
        return None

def download_images(images, product_slug):
    """
    Baixa as imagens do produto e salva localmente.
    Retorna o caminho da pasta onde as imagens foram salvas.
    """
    if not images:
        print("⚠️  Nenhuma imagem para baixar")
        return None
    
    # Criar pasta para as imagens
    images_dir = f"uploads/{product_slug}"
    os.makedirs(images_dir, exist_ok=True)
    
    print(f"\n📥 Baixando {len(images)} imagens...")
    
    downloaded_count = 0
    for idx, img_url in enumerate(images, 1):
        try:
            response = requests.get(img_url, timeout=15)
            response.raise_for_status()
            
            # Determinar extensão
            content_type = response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                ext = 'jpg'  # default
            
            # Salvar imagem
            filename = f"img_{idx:02d}.{ext}"
            filepath = os.path.join(images_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"  ✅ {filename} ({len(response.content) / 1024:.1f} KB)")
            downloaded_count += 1
            
        except Exception as e:
            print(f"  ❌ Falha ao baixar imagem {idx}: {e}")
    
    print(f"\n✅ {downloaded_count}/{len(images)} imagens baixadas com sucesso")
    return images_dir

def detect_product_category(title):
    """
    Detecta automaticamente a categoria do produto baseado no título.
    """
    title_lower = title.lower()
    
    # PET - palavras-chave relacionadas a animais
    pet_keywords = ['ração', 'racao', 'gato', 'cachorro', 'pet', 'animal', 
                    'coleira', 'comedouro', 'areia', 'petisco', 'aquario', 
                    'hamster', 'passaro', 'peixe']
    
    # Eletrônicos
    eletro_keywords = ['celular', 'smartphone', 'notebook', 'computador', 
                       'tablet', 'fone', 'mouse', 'teclado', 'monitor', 
                       'tv', 'televisão', 'camera', 'câmera', 'drone',
                       'console', 'playstation', 'xbox', 'switch', 
                       'airfryer', 'fritadeira', 'aspirador', 'robô']
    
    # Casa & Decoração
    casa_keywords = ['pote', 'vaso', 'quadro', 'cortina', 'tapete', 
                     'almofada', 'luminária', 'espelho', 'organizador',
                     'estante', 'prateleira', 'cozinha', 'banheiro']
    
    # Moda & Estilo
    moda_keywords = ['roupa', 'camisa', 'camiseta', 'calça', 'vestido', 
                     'sapato', 'tênis', 'bolsa', 'relógio', 'óculos',
                     'jaqueta', 'casaco', 'short', 'saia']
    
    for keyword in pet_keywords:
        if keyword in title_lower:
            return 'PET'
    
    for keyword in eletro_keywords:
        if keyword in title_lower:
            return 'E'
    
    for keyword in casa_keywords:
        if keyword in title_lower:
            return 'CD'
    
    for keyword in moda_keywords:
        if keyword in title_lower:
            return 'ME'
    
    return 'geral'

def generate_staging_json(product_data, images_dir, affiliate_link):
    """
    Gera o JSON de staging com os dados do produto.
    """
    os.makedirs("staging", exist_ok=True)
    
    slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"staging/{slug}_{timestamp}.json"
    
    # Detectar categoria automaticamente
    tag = detect_product_category(product_data['title'])
    
    data = {
        "platform": "mercadolivre",
        "external_id": product_data.get('external_id'),
        "title": product_data['title'],
        "price": product_data['price'],
        "oldPrice": product_data['old_price'],
        "images_local": images_dir,
        "images": [],  # será preenchido pelo stage_products.py
        "link": affiliate_link,
        "tag": tag,
        "disponivel": True,
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON de staging gerado: {filename}")
    print(f"🏷️  Categoria detectada: {tag}")
    print(f"📦 Produto: {data['title']}")
    print(f"💰 Preço: {data['price']}")
    print(f"🔗 Link: {data['link']}")
    if data['external_id']:
        print(f"🆔 External ID: {data['external_id']}")
    
    return filename

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python auto_prepare_ml.py <URL_DO_MERCADO_LIVRE>")
        print("\nExemplo:")
        print("  python scripts/auto_prepare_ml.py https://mercadolivre.com/sec/ABC123")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("=" * 60)
    print("🤖 PREPARAÇÃO AUTOMÁTICA DE PRODUTO - MERCADO LIVRE")
    print("=" * 60)
    print(f"\n🔗 URL: {url}\n")
    
    # 1. Fazer scraping do produto
    product_data = scrape_mercadolivre_product(url)
    if not product_data:
        print("❌ Falha ao obter dados do produto")
        sys.exit(1)
    
    # 2. Baixar imagens
    product_slug = slugify(product_data['title'])
    images_dir = download_images(product_data['images'], product_slug)
    if not images_dir:
        print("⚠️  Continuando sem imagens...")
        images_dir = "uploads/fallback_img"
    
    # 3. Gerar JSON de staging
    staging_file = generate_staging_json(product_data, images_dir, url)
    
    print("\n" + "=" * 60)
    print("✅ PREPARAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print(f"\n📝 Próximo passo: execute 'make stage' para enviar ao MinIO e adicionar ao banco\n")

if __name__ == "__main__":
    main()
