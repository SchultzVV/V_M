#!/usr/bin/env python3
"""
Script para preparar produtos automaticamente do Mercado Livre.
Usa API oficial (com OAuth) para dados precisos + fallback para scraping.

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
from pathlib import Path
import re

# Caminho para arquivo de tokens OAuth
TOKEN_FILE = Path(__file__).parent.parent / "config" / "ml_tokens.json"

def load_ml_token():
    """Carrega o access token do Mercado Livre do arquivo de config."""
    try:
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                return tokens.get('access_token')
    except Exception as e:
        print(f"⚠️  Não foi possível carregar token OAuth: {e}")
    return None

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
    Coleta dados do produto do Mercado Livre usando API oficial (prioritário) ou scraping.
    Retorna dict com: title, price, old_price, images, videos, external_id
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
            return None
        
        # ===== TENTAR API OFICIAL DO MERCADO LIVRE =====
        print(f"\n🔑 Tentando usar API oficial do Mercado Livre...")
        
        # Carregar token OAuth (se disponível)
        access_token = load_ml_token()
        
        api_headers = {}
        if access_token:
            api_headers['Authorization'] = f'Bearer {access_token}'
            print(f"✅ Token OAuth encontrado - usando API autenticada")
        else:
            print(f"ℹ️  Token OAuth não encontrado - usando API pública")
        
        try:
            # Buscar dados do item
            api_url = f"https://api.mercadolibre.com/items/{external_id}"
            api_response = requests.get(api_url, headers=api_headers, timeout=10)
            
            if api_response.status_code == 200:
                data = api_response.json()
                
                # Extrair informações básicas
                title = data.get('title', '')
                price = data.get('price', 0)
                original_price = data.get('original_price')
                old_price = original_price if original_price else price
                
                # Detectar desconto
                has_discount = original_price and original_price > price
                discount_pct = 0
                if has_discount:
                    discount_pct = ((original_price - price) / original_price) * 100
                
                # Pegar TODAS as imagens em alta resolução
                images = []
                pictures = data.get('pictures', [])
                for pic in pictures:
                    # Preferir secure_url, fallback para url
                    img_url = pic.get('secure_url') or pic.get('url')
                    if img_url:
                        images.append(img_url)
                
                # Pegar vídeo (se houver)
                videos = []
                video_id = data.get('video_id')
                if video_id:
                    videos.append(f"https://www.youtube.com/watch?v={video_id}")
                
                # Informações adicionais úteis
                condition = data.get('condition', 'new')  # new, used
                available_quantity = data.get('available_quantity', 0)
                sold_quantity = data.get('sold_quantity', 0)
                permalink = data.get('permalink', product_url)
                
                print(f"\n✅ DADOS OBTIDOS COM SUCESSO VIA API!")
                print(f"{'='*60}")
                print(f"📦 Produto: {title}")
                print(f"💰 Preço atual: R$ {price:.2f}")
                if has_discount:
                    print(f"💰 Preço original: R$ {old_price:.2f}")
                    print(f"🎉 Desconto: {discount_pct:.1f}% OFF")
                print(f"📊 Condição: {'Novo' if condition == 'new' else 'Usado'}")
                print(f"📦 Disponível: {available_quantity} unidades")
                print(f"✅ Vendidos: {sold_quantity} unidades")
                print(f"🖼️  Imagens: {len(images)}")
                if videos:
                    print(f"🎥 Vídeos: {len(videos)}")
                print(f"{'='*60}\n")
                
                return {
                    'title': title,
                    'price': f"R$ {price:.2f}",
                    'old_price': f"R$ {old_price:.2f}",
                    'images': images,
                    'videos': videos,
                    'external_id': external_id,
                    'product_url': permalink,
                    'condition': condition,
                    'available_quantity': available_quantity,
                    'sold_quantity': sold_quantity,
                    'has_discount': has_discount,
                    'discount_percentage': round(discount_pct, 1) if has_discount else 0
                }
            else:
                print(f"⚠️  API retornou status {api_response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Erro ao consultar API: {e}")
        
        # ===== FALLBACK: SCRAPING HTML =====
        print(f"\n🔄 Fazendo fallback para scraping HTML...")
        response = requests.get(product_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Título
        title_tag = soup.find('h1', class_='ui-pdp-title')
        title = title_tag.text.strip() if title_tag else "Produto Mercado Livre"
        
        # ===== PREÇOS - Estratégia aprimorada =====
        print(f"\n🔍 Analisando preços...")
        
        # Procurar container principal de preços
        price_container = soup.find('div', class_='ui-pdp-price')
        
        price = None
        old_price = None
        
        if price_container:
            # Pegar todos os elementos de preço dentro do container
            all_prices = price_container.find_all('span', class_='andes-money-amount__fraction')
            
            # Procurar preço riscado (preço original antes do desconto)
            old_price_element = price_container.find('s', class_='andes-money-amount--previous')
            
            if old_price_element and len(all_prices) >= 1:
                # Tem desconto: primeiro preço é o promocional
                price_text = all_prices[0].text.strip().replace('.', '').replace(',', '.')
                price = f"R$ {price_text}"
                
                # Preço riscado é o original
                old_price_fraction = old_price_element.find('span', class_='andes-money-amount__fraction')
                if old_price_fraction:
                    old_price_text = old_price_fraction.text.strip().replace('.', '').replace(',', '.')
                    old_price = f"R$ {old_price_text}"
                else:
                    old_price = price
            elif len(all_prices) > 0:
                # Sem desconto
                price_text = all_prices[0].text.strip().replace('.', '').replace(',', '.')
                price = f"R$ {price_text}"
                old_price = price
        
        # Fallback: buscar em toda página se não encontrou no container
        if not price:
            all_prices = soup.find_all('span', class_='andes-money-amount__fraction')
            if len(all_prices) > 0:
                price_text = all_prices[0].text.strip().replace('.', '').replace(',', '.')
                price = f"R$ {price_text}"
                old_price = price
            else:
                price = "R$ 0.00"
                old_price = "R$ 0.00"
        
        print(f"💰 Preços detectados:")
        print(f"   Preço atual (promocional): {price}")
        print(f"   Preço original: {old_price}")
        if price != old_price:
            print(f"   🎉 Produto com desconto!")
        
        # ===== IMAGENS E VÍDEOS =====
        print(f"\n🖼️  Coletando mídias...")
        
        images = []
        videos = []
        
        # Estratégia 1: Pegar de todos os thumbnails e galeria
        img_tags = soup.find_all('img')
        for img in img_tags:
            img_url = img.get('src') or img.get('data-src') or img.get('data-zoom')
            if img_url and 'http' in img_url and 'mlstatic.com' in img_url:
                # Filtrar apenas imagens de produto (não logos, ícones, etc)
                if any(x in img_url for x in ['/D_', '/I/', '/O/', '/W/', '/F/']):
                    # Forçar alta resolução
                    img_url = img_url.split('?')[0]  # Remover query params
                    img_url = re.sub(r'-[IOWF]\.', '-O.', img_url)  # Trocar para -O (original)
                    images.append(img_url)
        
        # Estratégia 2: Extrair de scripts JSON-LD (dados estruturados)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'image' in data:
                    img_data = data['image']
                    if isinstance(img_data, list):
                        images.extend(img_data)
                    elif isinstance(img_data, str):
                        images.append(img_data)
            except:
                pass
        
        # Estratégia 3: Vídeos
        video_tags = soup.find_all('video')
        for video in video_tags:
            video_url = video.get('src')
            if video_url:
                videos.append(video_url)
        
        # Vídeos em source tags
        source_tags = soup.find_all('source')
        for source in source_tags:
            video_url = source.get('src')
            if video_url and ('video' in video_url or '.mp4' in video_url):
                videos.append(video_url)
        
        # Remover duplicatas mantendo ordem
        images = list(dict.fromkeys(images))
        videos = list(dict.fromkeys(videos))
        
        # Adicionar vídeos à lista de imagens (para download)
        all_media = images + videos
        
        print(f"   📸 Imagens: {len(images)}")
        print(f"   🎥 Vídeos: {len(videos)}")
        print(f"   📦 Total de mídias: {len(all_media)}")
        
        print(f"\n✅ Dados obtidos com sucesso via HTML!")
        print(f"📦 Produto: {title}")
        print(f"💰 Preço: {price}")
        
        return {
            'title': title,
            'price': price,
            'old_price': old_price,
            'images': all_media,  # Incluir imagens e vídeos
            'external_id': external_id,
            'product_url': product_url
        }
        
    except Exception as e:
        print(f"❌ Erro ao fazer scraping: {e}")
        import traceback
        traceback.print_exc()
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
    IMPORTANTE: Usa o link de afiliado original para garantir comissão!
    Nunca usar permalink ou URL limpa - isso quebra o tracking de afiliado.
    """
    # Detectar se está rodando dentro do container ou na raiz do projeto
    if os.path.exists('/app/staging'):
        staging_dir = '/app/staging'
    elif os.path.exists('services/site/staging'):
        staging_dir = 'services/site/staging'
    else:
        staging_dir = 'staging'
    
    os.makedirs(staging_dir, exist_ok=True)
    
    slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{staging_dir}/{slug}_{timestamp}.json"
    
    # SEMPRE usar link de afiliado original - garante comissão!
    # Mesmo que tenha página intermediária, preserva tracking de afiliado
    
    data = {
        "platform": "mercadolivre",
        "external_id": product_data.get('external_id'),
        "title": product_data['title'],
        "price": product_data['price'],
        "oldPrice": product_data['old_price'],
        "images_local": images_dir,
        "images": [],
        "link": original_affiliate_link,  # Link de afiliado original!
        "tag": tag,
        "disponivel": True,
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    # Adicionar campos extras se vieram da API
    if product_data.get('videos'):
        data['videos'] = product_data['videos']
    
    if product_data.get('condition'):
        data['condition'] = product_data['condition']
    
    if product_data.get('available_quantity') is not None:
        data['available_quantity'] = product_data['available_quantity']
    
    if product_data.get('sold_quantity') is not None:
        data['sold_quantity'] = product_data['sold_quantity']
    
    if product_data.get('has_discount'):
        data['has_discount'] = product_data['has_discount']
        data['discount_percentage'] = product_data.get('discount_percentage', 0)

    
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
