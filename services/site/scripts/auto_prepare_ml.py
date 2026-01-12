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
    # Formato permalink: /p/MLB123456789
    match = re.search(r'/p/(ML[A-Z]\d+)', url)
    if match:
        return match.group(1)
    
    # Formato padrão: MLB-123456789 ou MLB123456789
    match = re.search(r'(ML[A-Z])[\-]?(\d+)', url)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    return None

def follow_affiliate_link(url):
    """
    Segue o link de afiliado até chegar na página final do produto.
    Retorna a URL final do produto.
    """
    print(f"🔗 Seguindo link de afiliado...")
    print(f"   URL inicial: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Seguir todos os redirects
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        final_url = response.url
        
        print(f"   URL final: {final_url}")
        
        # Verificar se é uma página de perfil (não produto direto)
        if '/social/' in final_url or '/perfil/' in final_url:
            print(f"\n🔄 Detectada página de perfil. Procurando link do produto...")
            
            # Tentar extrair o link do produto do botão "ir para produto"
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procurar por links que contenham /p/ (permalink de produto)
            product_links = soup.find_all('a', href=re.compile(r'/p/MLB\d+'))
            
            if product_links:
                product_url = product_links[0].get('href')
                
                # Se for URL relativa, completar com domínio
                if product_url.startswith('/'):
                    product_url = f"https://www.mercadolivre.com.br{product_url}"
                
                print(f"   ✅ Link do produto encontrado: {product_url}")
                
                # Extrair apenas a parte antes dos parâmetros
                if '#' in product_url:
                    product_url = product_url.split('#')[0]
                if '?' in product_url:
                    product_url = product_url.split('?')[0]
                
                return product_url
            else:
                print(f"\n❌ ERRO: Não foi possível encontrar o link do produto na página de perfil.")
                print(f"   Por favor, use um link direto do produto.")
                print(f"   Exemplo: https://produto.mercadolivre.com.br/MLB-123456789-...")
                return None
        
        # Verificar se chegamos em uma página de produto
        if 'mercadolivre.com' in final_url or 'mercadolibre.com' in final_url:
            return final_url
        else:
            print(f"⚠️  URL não parece ser do Mercado Livre: {final_url}")
            return url
            
    except Exception as e:
        print(f"⚠️  Erro ao seguir redirect: {e}")
        return url

def scrape_mercadolivre_product(url):
    """
    Faz scraping dos dados do produto no Mercado Livre.
    Retorna dict com: title, price, old_price, images, external_id
    """
    print(f"\n{'='*60}")
    print(f"📥 COLETANDO DADOS DO PRODUTO")
    print(f"{'='*60}\n")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Primeiro, seguir o link de afiliado até a página do produto
        product_url = follow_affiliate_link(url)
        
        # Se não conseguiu obter URL válida, abortar
        if not product_url:
            return None
        
        # Extrair ID do produto da URL final
        external_id = extract_ml_product_id(product_url)
        
        if external_id:
            print(f"\n🆔 ID do produto encontrado: {external_id}")
        else:
            print(f"\n⚠️  Não foi possível extrair o ID do produto")
        
        # Tentar usar a API do Mercado Livre se tivermos o ID
        if external_id:
            try:
                print(f"🌐 Consultando API do Mercado Livre...")
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
                    
                    print(f"\n✅ Dados obtidos com sucesso via API!")
                    print(f"📦 Produto: {title}")
                    print(f"💰 Preço: R$ {price:.2f}")
                    print(f"🖼️  Imagens encontradas: {len(images)}")
                    print(f"🖼️  Imagens encontradas: {len(images)}")
                    
                    return {
                        'title': title,
                        'price': f"R$ {price:.2f}",
                        'old_price': f"R$ {old_price:.2f}",
                        'images': images,
                        'external_id': external_id,
                        'product_url': product_url
                    }
            except Exception as e:
                print(f"⚠️  Falha na API, tentando scraping HTML: {e}")
        
        # Fallback: scraping HTML
        print(f"\n🔄 Tentando scraping HTML da página...")
        response = requests.get(product_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Título
        title_tag = soup.find('h1', class_='ui-pdp-title')
        title = title_tag.text.strip() if title_tag else "Produto Mercado Livre"
        
        # Estratégia para pegar preços corretamente
        # 1. Procurar por todos os preços na página
        all_prices = soup.find_all('span', class_='andes-money-amount__fraction')
        
        # 2. Procurar especificamente por preço riscado (preço antigo)
        old_price_tag = soup.find('s', class_='andes-money-amount--previous')
        
        price = None
        old_price = None
        
        if old_price_tag and len(all_prices) >= 2:
            # Se há preço riscado, significa que há promoção
            # O primeiro preço visível é o promocional, o riscado é o antigo
            price_text = all_prices[0].text.strip().replace('.', '').replace(',', '.')
            price = f"R$ {price_text}"
            
            old_price_fraction = old_price_tag.find('span', class_='andes-money-amount__fraction')
            if old_price_fraction:
                old_price_text = old_price_fraction.text.strip().replace('.', '').replace(',', '.')
                old_price = f"R$ {old_price_text}"
            else:
                old_price = price
                
        elif len(all_prices) > 0:
            # Sem promoção, ambos preços iguais
            price_text = all_prices[0].text.strip().replace('.', '').replace(',', '.')
            price = f"R$ {price_text}"
            old_price = price
        else:
            # Fallback
            price = "R$ 0.00"
            old_price = "R$ 0.00"
        
        print(f"\n💰 Preços detectados:")
        print(f"   Preço atual (promocional): {price}")
        print(f"   Preço original: {old_price}")
        if price != old_price:
            print(f"   🎉 Produto com desconto!")
        
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
        
        print(f"\n✅ Dados obtidos com sucesso via HTML!")
        print(f"📦 Produto: {title}")
        print(f"💰 Preço: {price}")
        print(f"🖼️  Imagens encontradas: {len(images)}")
        
        return {
            'title': title,
            'price': price,
            'old_price': old_price,
            'images': images,
            'external_id': external_id,
            'product_url': product_url
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
    Retorna uma sugestão, mas não a categoria final.
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

def ask_user_category(suggested_category):
    """
    Pergunta ao usuário qual categoria usar, mostrando sugestão.
    """
    print("\n" + "=" * 60)
    print("🏷️  ESCOLHA A CATEGORIA DO PRODUTO")
    print("=" * 60)
    print("\n📋 Categorias disponíveis:")
    print("  1. PET - PetShop")
    print("  2. E - Eletrônicos")
    print("  3. CD - Casa & Decoração")
    print("  4. ME - Moda & Estilo")
    print("  5. geral - Categoria Geral")
    
    category_map = {
        "1": "PET",
        "2": "E",
        "3": "CD",
        "4": "ME",
        "5": "geral",
        "PET": "PET",
        "E": "E",
        "CD": "CD",
        "ME": "ME",
        "geral": "geral"
    }
    
    # Encontrar número da sugestão
    suggested_number = "5"
    for num, cat in category_map.items():
        if cat == suggested_category and num.isdigit():
            suggested_number = num
            break
    
    print(f"\n💡 Sugestão baseada no título: {suggested_category} (opção {suggested_number})")
    
    choice = input(f"\nDigite o número da categoria [pressione Enter para usar a sugestão]: ").strip()
    
    if not choice:
        choice = suggested_number
    
    selected = category_map.get(choice, suggested_category)
    print(f"✅ Categoria selecionada: {selected}")
    
    return selected

def generate_staging_json(product_data, images_dir, original_affiliate_link, tag):
    """
    Gera o JSON de staging com os dados do produto.
    Usa o link completo do produto (não o link curto de afiliado).
    """
    os.makedirs("staging", exist_ok=True)
    
    slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"staging/{slug}_{timestamp}.json"
    
    # Usar o link completo do produto obtido durante o scraping
    product_link = product_data.get('product_url', original_affiliate_link)
    
    data = {
        "platform": "mercadolivre",
        "external_id": product_data.get('external_id'),
        "title": product_data['title'],
        "price": product_data['price'],
        "oldPrice": product_data['old_price'],
        "images_local": images_dir,
        "images": [],  # será preenchido pelo stage_products.py
        "link": product_link,  # Link completo do produto, não o de afiliado
        "tag": tag,
        "disponivel": True,
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("✅ JSON DE STAGING GERADO COM SUCESSO")
    print("=" * 60)
    print(f"\n📄 Arquivo: {filename}")
    print(f"🏷️  Categoria: {tag}")
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
    
    # 3. Detectar categoria sugerida e perguntar ao usuário
    suggested_category = detect_product_category(product_data['title'])
    selected_category = ask_user_category(suggested_category)
    
    # 4. Gerar JSON de staging
    staging_file = generate_staging_json(product_data, images_dir, url, selected_category)
    
    print("\n" + "=" * 60)
    print("✅ PREPARAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print(f"\n📝 Próximo passo: execute 'make stage' para enviar ao MinIO e adicionar ao banco\n")

if __name__ == "__main__":
    main()
