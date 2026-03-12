#!/usr/bin/env python3
"""
Preparação de produtos do Mercado Livre usando API OFICIAL como prioridade.
Scraping HTML apenas como fallback.
"""

import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime
from slugify import slugify

# Importa funções do auto_prepare_ml
sys.path.insert(0, os.path.dirname(__file__))
from auto_prepare_ml import (
    follow_affiliate_link,
    extract_ml_product_id,
    scrape_mercadolivre_product
)


def load_ml_token():
    """Carrega o token OAuth do Mercado Livre."""
    token_file = Path("/app/config/ml_tokens.json")
    
    if not token_file.exists():
        return None
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token')
    except Exception as e:
        print(f"❌ Erro ao ler token: {e}")
        return None


def get_product_from_api(item_id, token):
    """Busca produto na API oficial. Prioriza /items (tem preços)."""
    clean_id = item_id.replace('-', '')
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    # Tenta como ITEM primeiro (tem preços e descontos)
    url = f"https://api.mercadolibre.com/items/{clean_id}"
    print(f"   🌐 API: {url}")
    print(f"   🔑 {'✅ OAuth' if token else '❌ Público'}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Item encontrado!")
            return response.json()
        
        # Fallback: tenta catálogo
        url_cat = f"https://api.mercadolibre.com/products/{clean_id}"
        response = requests.get(url_cat, headers=headers, timeout=15)

        if response.status_code == 200:
            catalog = response.json()
            print(f"   ✅ Catálogo encontrado — buscando preço via buy_box_winner...")

            # Pega preço via buy_box_winner (item oficial/destaque do catálogo)
            bbw_id = (catalog.get('buy_box_winner') or {}).get('item_id')

            if bbw_id:
                # Enriquece com /items/{bbw_id} para obter original_price, shipping etc.
                item_url = f"https://api.mercadolibre.com/items/{bbw_id}"
                ir = requests.get(item_url, headers=headers, timeout=15)
                if ir.status_code == 200:
                    item = ir.json()
                    price     = float(item.get('price', 0) or 0)
                    old_price = float(item.get('original_price', 0) or 0)
                    catalog['price']              = price
                    catalog['original_price']     = old_price if old_price > price else 0
                    catalog['available_quantity'] = item.get('available_quantity', 50)
                    catalog['sold_quantity']       = item.get('sold_quantity', 0)
                    catalog['shipping']            = item.get('shipping', {})
                    # Usa imagens do item se catálogo não tiver
                    if not catalog.get('pictures') and item.get('pictures'):
                        catalog['pictures'] = item['pictures']
                    print(f"   💰 Preço via buy_box_winner {bbw_id}: R$ {price:.2f}" +
                          (f"  (de R$ {old_price:.2f})" if old_price > price else ""))
                else:
                    print(f"   ⚠️  Item {bbw_id} retornou {ir.status_code} — sem preço")
            else:
                print(f"   ⚠️  buy_box_winner não encontrado no catálogo — preço virá do OCR")

            return catalog

        print(f"   ❌ Não encontrado")
        return None
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return None


def get_sale_price_from_api(item_id, token):
    """Busca preço de venda oficial (com promoção) via /sale_price endpoint.
    Retorna: {'price': float, 'oldPrice': float, 'promotion_id': str}
    """
    if not token:
        print("   ⚠️  Token necessário para /sale_price")
        return None
    
    clean_id = item_id.replace('-', '')
    url = f"https://api.mercadolibre.com/items/{clean_id}/sale_price"
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   💰 API Preços: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            price = float(data.get('amount', 0))
            regular = float(data.get('regular_amount', 0))
            promo_id = data.get('metadata', {}).get('promotion_id')
            
            # Se tem regular_amount, é promoção
            if regular and regular > price:
                print(f"   🎉 Promoção detectada: R$ {regular:.2f} → R$ {price:.2f}")
                return {'price': price, 'oldPrice': regular, 'promotion_id': promo_id}
            else:
                print(f"   💵 Preço normal: R$ {price:.2f}")
                return {'price': price, 'oldPrice': 0, 'promotion_id': None}
        
        print(f"   ⚠️  Endpoint /sale_price não disponível")
        return None
    except Exception as e:
        print(f"   ❌ Erro ao buscar preços: {e}")
        return None


def download_images_hq(image_urls, product_slug, base_path="/app/uploads"):
    """Baixa imagens em alta qualidade, descartando imagens pequenas (< 20KB ou < 300x300px).
    SEMPRE limpa a pasta antes de baixar para evitar mistura com imagens antigas.
    """
    from PIL import Image
    import io
    import glob

    MIN_SIZE_KB = 20        # descarta < 20 KB
    MIN_DIMENSION = 300    # descarta se largura ou altura < 300px

    product_dir = Path(base_path) / product_slug
    product_dir.mkdir(parents=True, exist_ok=True)

    # ── Limpar imagens antigas antes de baixar novas ──────────────────────
    old_images = list(product_dir.glob('image_*.jpg')) + list(product_dir.glob('image_*.png'))
    if old_images:
        print(f"   🧹 Removendo {len(old_images)} imagem(ns) antiga(s) da pasta...")
        for old in old_images:
            try:
                old.unlink()
            except Exception:
                pass

    print(f"\n📥 Baixando {len(image_urls)} imagens HQ (filtrando imagens pequenas)...")
    
    downloaded = []
    skipped = 0
    saved_index = 1
    for i, img_url in enumerate(image_urls, 1):
        try:
            response = requests.get(img_url, timeout=15)
            response.raise_for_status()
            
            content = response.content
            size_kb = len(content) / 1024

            # Filtro 1: tamanho do arquivo
            if size_kb < MIN_SIZE_KB:
                print(f"   ⏩ {i}/{len(image_urls)} - {size_kb:.1f}KB — muito pequena, ignorada")
                skipped += 1
                continue

            # Filtro 2: dimensões da imagem
            try:
                img = Image.open(io.BytesIO(content))
                w, h = img.size
                if w < MIN_DIMENSION or h < MIN_DIMENSION:
                    print(f"   ⏩ {i}/{len(image_urls)} - {w}x{h}px — dimensões insuficientes, ignorada")
                    skipped += 1
                    continue
            except Exception:
                pass  # se não conseguir ler, deixa passar

            img_filename = f"image_{saved_index}.jpg"
            img_path = product_dir / img_filename
            
            with open(img_path, 'wb') as f:
                f.write(content)
            
            downloaded.append(img_filename)
            print(f"   ✅ {i}/{len(image_urls)} → image_{saved_index}.jpg ({size_kb:.1f}KB)")
            saved_index += 1
        except Exception as e:
            print(f"   ⚠️  Erro imagem {i}: {e}")

    if skipped:
        print(f"   🗑️  {skipped} imagem(s) descartada(s) por serem muito pequenas")
    
    return str(product_dir.relative_to(Path(base_path).parent)), downloaded


def save_staging_json(product_data, original_url):
    """Salva JSON de staging."""
    staging_dir = Path("/app/staging")
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    title = product_data['title']
    product_slug = slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Converte preços
    def parse_price(price):
        if isinstance(price, str):
            clean = price.replace('R$', '').replace(' ', '').strip()
            if ',' in clean:
                clean = clean.replace('.', '').replace(',', '.')
            return float(clean) if clean else 0
        return float(price) if price else 0
    
    price = parse_price(product_data.get('price', 0))
    old_price = parse_price(product_data.get('old_price', 0))
    
    # Debug
    print(f"\n🔍 Preços:")
    print(f"   price: {price}")
    print(f"   oldPrice: {old_price}")
    if old_price > price > 0:
        disc = ((old_price - price) / old_price) * 100
        print(f"   ✅ Desconto: {disc:.0f}%")
    
    data = {
        "platform": "mercadolivre",
        "external_id": product_data.get('external_id', ''),
        "title": title,
        "price": price,
        "oldPrice": old_price,
        "images_local": product_data.get('images_local', f"uploads/{product_slug}"),
        "images": [],
        "link": original_url,
        "tag": product_data.get('tag', 'geral'),
        "disponivel": product_data.get('available_quantity', 1) > 0 if 'available_quantity' in product_data else True,
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    json_filename = f"{product_slug}_{timestamp}.json"
    json_path = staging_dir / json_filename
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return json_path, data


def main():
    print("=" * 60)
    print("🚀 PREPARAÇÃO VIA API OFICIAL (OAuth)")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n❌ URL não fornecida!")
        print("Uso: python3 api_prepare_ml.py <URL>")
        sys.exit(1)
    
    original_url = sys.argv[1]
    print(f"\n🔗 URL: {original_url}\n")
    
    # PASSO 1: Resolver link
    print("=" * 60)
    print("📥 PASSO 1: RESOLVER LINK")
    print("=" * 60 + "\n")
    
    resolved_url = follow_affiliate_link(original_url)
    if not resolved_url:
        print("❌ Falha ao resolver link")
        sys.exit(1)
    
    item_id = extract_ml_product_id(resolved_url)
    if not item_id:
        print("❌ ID não encontrado")
        sys.exit(1)
    
    print(f"✅ ID: {item_id}\n")
    
    # PASSO 2: API
    print("=" * 60)
    print("🌐 PASSO 2: BUSCAR NA API")
    print("=" * 60 + "\n")
    
    token = load_ml_token()
    if not token:
        print("⚠️  Sem token OAuth - usando scraping")
        product_data = scrape_mercadolivre_product(original_url)
        if not product_data:
            sys.exit(1)
        final_data = product_data
    else:
        api_data = get_product_from_api(item_id, token)
        
        if api_data:
            # Verificar se é item ou catálogo
            is_catalog = 'name' in api_data and 'buy_box_winner' in api_data
            has_prices = api_data.get('price') is not None
            
            if is_catalog or not has_prices:
                # Catálogo não tem preços - usar scraping
                print(f"\n⚠️  Catálogo sem preços - buscando preços via scraping...")
                product_data = scrape_mercadolivre_product(original_url)
                if product_data:
                    # Combina dados: título/imagens da API + preços do scraping
                    final_data = {
                        'external_id': api_data.get('id'),
                        'title': api_data.get('name') or api_data.get('title', ''),
                        'price': product_data.get('price', 0),
                        'old_price': product_data.get('old_price', 0),
                        'available_quantity': product_data.get('available_quantity', 0),
                        'condition': 'new'
                    }
                    print(f"   ✅ Preços obtidos via scraping")
                else:
                    # Sem scraping, usa só API (sem preços)
                    final_data = {
                        'external_id': api_data.get('id'),
                        'title': api_data.get('name') or api_data.get('title', ''),
                        'price': 0,
                        'old_price': 0,
                        'available_quantity': 0,
                        'condition': 'new'
                    }
            else:
                # Item com preços - USAR /sale_price endpoint (oficial)
                print(f"\n📊 Buscando preços promocionais via API oficial...")
                sale_price = get_sale_price_from_api(item_id, token)
                
                if sale_price:
                    # Usa preços do endpoint oficial /sale_price
                    final_data = {
                        'external_id': api_data.get('id'),
                        'title': api_data.get('title', ''),
                        'price': sale_price['price'],
                        'old_price': sale_price['oldPrice'],
                        'available_quantity': api_data.get('available_quantity', 0),
                        'condition': api_data.get('condition', 'new'),
                        'promotion_id': sale_price.get('promotion_id')
                    }
                else:
                    # Fallback: usa campos price/original_price do /items
                    final_data = {
                        'external_id': api_data.get('id'),
                        'title': api_data.get('title', ''),
                        'price': api_data.get('price', 0),
                        'old_price': api_data.get('original_price', 0),
                        'available_quantity': api_data.get('available_quantity', 0),
                        'condition': api_data.get('condition', 'new')
                    }
            
            print(f"\n📦 {final_data['title'][:60]}...")
            print(f"💰 Preço: R$ {final_data['price']:.2f}" if isinstance(final_data['price'], (int, float)) else f"💰 Preço: {final_data['price']}")
            if final_data['old_price'] and final_data['old_price'] > final_data['price']:
                if isinstance(final_data['old_price'], str):
                    print(f"🏷️  Preço antigo: {final_data['old_price']}")
                else:
                    desc = ((final_data['old_price'] - final_data['price']) / final_data['old_price']) * 100
                    print(f"🏷️  De: R$ {final_data['old_price']:.2f} ({desc:.0f}% OFF)")
            
            # Imagens da API
            if api_data.get('pictures'):
                imgs = []
                for pic in api_data['pictures']:
                    url = (pic.get('secure_url') or pic.get('url', '')).replace('-I.', '-O.')
                    if url:
                        imgs.append(url)
                
                if imgs:
                    slug = slugify(final_data['title'])
                    dir, files = download_images_hq(imgs, slug)
                    final_data['images_local'] = dir
                    print(f"✅ {len(files)} imagens HQ")
        else:
            # Fallback scraping
            print("\n⚠️  API falhou - usando scraping")
            product_data = scrape_mercadolivre_product(original_url)
            if not product_data:
                sys.exit(1)
            final_data = product_data
    
    # PASSO 3: Verificar desconto e perguntar preço promocional se necessário
    print("\n" + "=" * 60)
    print("🏷️  PASSO 3: VERIFICAR DESCONTO")
    print("=" * 60)
    
    # Converte preços para float se forem strings
    def to_float(price):
        if isinstance(price, str):
            clean = price.replace('R$', '').replace(' ', '').strip()
            if ',' in clean:
                clean = clean.replace('.', '').replace(',', '.')
            return float(clean) if clean else 0
        return float(price) if price else 0
    
    current_price = to_float(final_data.get('price', 0))
    current_old_price = to_float(final_data.get('old_price', 0))
    
    # Se não tem desconto detectado (old_price = 0 ou igual ao price)
    if current_old_price == 0 or current_old_price == current_price:
        if current_price > 0:
            print(f"\n⚠️  Desconto não detectado automaticamente")
            print(f"   Preço obtido: R$ {current_price:.2f}")
            print(f"\n💡 O produto está em promoção?")
            promo_input = input("   Digite o preço PROMOCIONAL (ou Enter se não houver): R$ ").strip()
            
            if promo_input:
                try:
                    # Parse do preço promocional
                    promo_clean = promo_input.replace(',', '.')
                    promo_price = float(promo_clean)
                    
                    if promo_price > 0 and promo_price < current_price:
                        # INVERTE: preço promocional digitado vai para price
                        # Preço da API vai para old_price
                        final_data['old_price'] = current_price
                        final_data['price'] = promo_price
                        
                        discount = ((current_price - promo_price) / current_price) * 100
                        print(f"\n   ✅ Desconto configurado:")
                        print(f"      De: R$ {current_price:.2f}")
                        print(f"      Por: R$ {promo_price:.2f}")
                        print(f"      🎉 {discount:.0f}% OFF")
                    else:
                        print(f"\n   ⚠️  Preço promocional inválido (deve ser menor que R$ {current_price:.2f})")
                        print(f"   Mantendo sem desconto")
                except ValueError:
                    print(f"\n   ⚠️  Valor inválido, mantendo sem desconto")
    else:
        discount = ((current_old_price - current_price) / current_old_price) * 100
        print(f"\n✅ Desconto detectado automaticamente:")
        print(f"   De: R$ {current_old_price:.2f}")
        print(f"   Por: R$ {current_price:.2f}")
        print(f"   🎉 {discount:.0f}% OFF")
    
    # PASSO 4: Categoria
    print("\n" + "=" * 60)
    print("📂 PASSO 4: CATEGORIA")
    print("=" * 60)
    print("\n1. geral  2. E  3. CD  4. ME  5. PET\n")
    
    cat = input("🏷️  Categoria: ").strip() or 'geral'
    final_data['tag'] = cat if cat in ['geral', 'E', 'CD', 'ME', 'PET'] else 'geral'
    
    # Salvar
    print("\n" + "=" * 60)
    print("💾 SALVANDO")
    print("=" * 60)
    
    json_path, data = save_staging_json(final_data, original_url)
    
    print("\n✅ CONCLUÍDO!")
    print(f"📄 {json_path.name}")
    print(f"📂 {data['tag']}")
    print(f"💰 R$ {data['price']}")
    if data['oldPrice'] > 0:
        print(f"🏷️  R$ {data['oldPrice']} ({((data['oldPrice']-data['price'])/data['oldPrice']*100):.0f}% OFF)")
    print(f"\n📋 Próximo: make stage\n")


if __name__ == "__main__":
    main()
