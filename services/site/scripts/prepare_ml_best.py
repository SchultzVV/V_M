#!/usr/bin/env python3
"""
Preparação COMPLETA de produtos do Mercado Livre.
Combina API/Scraping + screenshot + OCR para dados mais precisos.

ESTRATÉGIA OTIMIZADA:
1. Tenta API oficial primeiro (se houver OAuth) - DADOS PRECISOS
2. Faz scraping HTML como fallback  
3. Usa OCR apenas para complementar dados faltantes (preços promocionais, banners)

Fluxo:
1. Segue link de afiliado até página do produto
2. Tenta API oficial do Mercado Livre (OAuth)
3. Faz scraping HTML se API não disponível
4. Tira screenshot da página
5. Usa OCR para complementar dados faltantes
6. Combina todos os dados
7. Baixa imagens do produto
8. Gera JSON de staging

Uso:
    python scripts/prepare_ml_best.py https://mercadolivre.com/sec/ABC123
"""

import os
import sys
import json
import requests
import tempfile
import re
from pathlib import Path
from datetime import datetime
from slugify import slugify
from playwright.sync_api import sync_playwright

# Importar funções de api_prepare_ml e auto_prepare_ml
sys.path.insert(0, os.path.dirname(__file__))
from api_prepare_ml import (
    load_ml_token,
    get_product_from_api,
    download_images_hq
)
from auto_prepare_ml import (
    follow_affiliate_link,
    extract_ml_product_id,
    scrape_mercadolivre_product,
    detect_product_category,
    ask_user_category
)


def take_screenshot_ml(url: str) -> str:
    """Tira screenshot da página do Mercado Livre."""
    print(f"\n📸 Tirando screenshot da página...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            print(f"   🌐 Carregando página...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            screenshot_path = temp_file.name
            temp_file.close()
            
            print(f"   📷 Capturando imagem...")
            page.screenshot(path=screenshot_path, full_page=True)
            
            print(f"   ✅ Screenshot salvo")
            
            browser.close()
            return screenshot_path
            
        except Exception as e:
            print(f"   ❌ Erro ao tirar screenshot: {e}")
            browser.close()
            return None


def extract_info_from_screenshot(screenshot_path: str) -> dict:
    """Envia screenshot para o serviço info-scrap (OCR)."""
    print(f"\n🔍 Extraindo informações via OCR...")
    
    url = "http://info-scrap:8000/extract"
    
    try:
        with open(screenshot_path, 'rb') as f:
            files = {'file': (os.path.basename(screenshot_path), f, 'image/png')}
            response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Extração realizada! Linhas: {result.get('line_count', 0)}")
            return result
        else:
            print(f"   ❌ Erro na extração: Status {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Serviço info-scrap não disponível")
        return None
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return None


def enrich_ml_data_with_ocr(base_data: dict, ocr_data: dict) -> dict:
    """
    Enriquece dados do API/Scraping com informações via OCR.
    OCR é usado APENAS para complementar dados faltantes.
    
    Args:
        base_data: Dados da API ou scraping
        ocr_data: Dados extraídos via OCR
        
    Returns:
        Dados enriquecidos
    """
    print(f"\n🔄 Enriquecendo dados com OCR...")
    
    enriched_data = base_data.copy()
    
    if not ocr_data or not ocr_data.get('success'):
        print(f"   ⚠️  OCR não disponível, usando apenas API/Scraping")
        return enriched_data
    
    ocr_text = ocr_data.get('text', '')
    ocr_lines = ocr_data.get('lines', [])
    
    # 1. Procurar preços apenas se não temos preço confiável
    if enriched_data.get('price', 0) == 0:
        price_pattern = r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
        prices_found = re.findall(price_pattern, ocr_text)
        
        if prices_found:
            print(f"   💰 Preços no OCR: {len(prices_found)}")
            try:
                price_str = prices_found[0].replace('.', '').replace(',', '.')
                price_value = float(price_str)
                enriched_data['price'] = f"R$ {price_value:.2f}"
                print(f"   ✨ Preço complementado via OCR: R$ {price_value:.2f}")
            except:
                pass
    
    # 2. Procurar desconto apenas se não temos old_price
    if not enriched_data.get('old_price') or enriched_data.get('old_price') == enriched_data.get('price'):
        discount_pattern = r'(\d{1,2})%\s*OFF'
        discounts_found = re.findall(discount_pattern, ocr_text)
        
        if discounts_found:
            print(f"   🎉 Descontos encontrados no OCR: {discounts_found}")
            try:
                discount_pct = int(discounts_found[0])
                enriched_data['has_discount'] = True
                enriched_data['discount_percentage'] = discount_pct
                
                # Calcular old_price se temos preço atual
                if enriched_data.get('price'):
                    price_val = float(str(enriched_data['price']).replace('R$', '').replace(' ', '').replace(',', '.'))
                    old_price_val = price_val / (1 - discount_pct / 100)
                    enriched_data['old_price'] = f"R$ {old_price_val:.2f}"
                    print(f"   ✨ Preço antigo calculado: R$ {old_price_val:.2f} ({discount_pct}% OFF)")
            except:
                pass
    
    # 3. Verificar se tem frete grátis
    if 'frete grátis' in ocr_text.lower() or 'full' in ocr_text:
        enriched_data['free_shipping'] = True
        print(f"   📦 Frete grátis detectado via OCR")
    
    # 4. Verificar Mercado Ponto
    if 'mercado pontos' in ocr_text.lower() or 'pontos' in ocr_text.lower():
        enriched_data['mercado_pontos'] = True
        print(f"   ⭐ Mercado Pontos detectado via OCR")
    
    # 5. Buscar cupons
    cupom_pattern = r'(?:cupom|código)\s*[:-]?\s*([A-Z0-9]{4,})'
    cupons_found = re.findall(cupom_pattern, ocr_text, re.IGNORECASE)
    if cupons_found:
        enriched_data['cupons'] = cupons_found
        print(f"   🎫 Cupons detectados: {', '.join(cupons_found)}")
    
    # 6. Adicionar texto OCR para referência
    enriched_data['ocr_text'] = ocr_text
    enriched_data['ocr_lines'] = ocr_lines
    
    print(f"   ✅ Enriquecimento concluído!")
    
    return enriched_data


def generate_staging_json(product_data: dict, images_dir: str, original_url: str, tag: str, subcategory: str = "") -> tuple:
    """Gera JSON de staging no formato padrão."""

    slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def parse_price(val):
        """Converte qualquer formato de preço para float."""
        if not val:
            return 0.0
        s = str(val).replace('R$', '').replace('\xa0', '').strip()
        # formato brasileiro: 1.234,56 -> 1234.56
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            return float(s)
        except:
            return 0.0

    price_val = parse_price(product_data.get('price', 0))
    old_price_val = parse_price(product_data.get('old_price', 0))

    # Garante que oldPrice é sempre >= price (evita inversão de promoção)
    if old_price_val < price_val:
        old_price_val = price_val

    price_str = f"R$ {price_val:.2f}"
    old_price_str = f"R$ {old_price_val:.2f}"

    available_quantity = product_data.get('available_quantity', None)
    disponivel = (available_quantity > 0) if isinstance(available_quantity, int) else True

    # Mapeia tag → pasta staging (igual ao shopee_prepare.py)
    tag_folders = {
        "E":    "eletronicos",
        "CD":   "casa-decoracao",
        "ME":   "moda-estilo",
        "PET":  "petshop",
        "geral": "geral",
    }
    tag_folder = tag_folders.get(tag.upper(), "geral")

    if subcategory:
        staging_dir = Path(f"/app/staging/{tag_folder}/{subcategory}")
    else:
        staging_dir = Path(f"/app/staging/{tag_folder}")

    staging_dir.mkdir(parents=True, exist_ok=True)
    filename = str(staging_dir / f"{slug}_{timestamp}.json")

    data = {
        "platform": "mercadolivre",
        "external_id": product_data.get('external_id', ''),
        "title": product_data['title'],
        "price": price_str,
        "oldPrice": old_price_str,
        "images_local": images_dir,
        "images": [],
        "link": original_url,
        "tag": tag.upper(),
        "subcategory": subcategory,
        "disponivel": disponivel,
        "criado_em": timestamp,
        "via_webhook": False
    }

    # Estoque e vendidos — campos principais solicitados
    if available_quantity is not None:
        data['stock'] = available_quantity
    if product_data.get('sold_quantity') is not None:
        data['sold_quantity'] = product_data['sold_quantity']
    
    # Campos opcionais
    if product_data.get('videos'):
        data['videos'] = product_data['videos']
    
    if product_data.get('condition'):
        data['condition'] = product_data['condition']
    
    if product_data.get('free_shipping'):
        data['free_shipping'] = True
    
    if product_data.get('mercado_pontos'):
        data['mercado_pontos'] = True
    
    if product_data.get('cupons'):
        data['cupons'] = product_data['cupons']
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 JSON salvo: {filename}")
    
    return filename, data


def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python prepare_ml_best.py <URL_MERCADO_LIVRE>")
        sys.exit(1)
    
    url = sys.argv[1]
    screenshot_path = None
    selected_subcategory = ""
    
    try:
        print("=" * 70)
        print("🚀 PREPARAÇÃO COMPLETA - MERCADO LIVRE")
        print("   (API + Scraping + Screenshot + OCR)")
        print("=" * 70)
        print(f"\n🔗 URL: {url}\n")
        
        # ========================================
        # ETAPA 1: Resolver link de afiliado
        # ========================================
        print("━" * 70)
        print("ETAPA 1: Resolvendo link de afiliado")
        print("━" * 70)
        product_url = follow_affiliate_link(url)
        
        if not product_url:
            print("❌ Falha ao resolver link")
            sys.exit(1)
        
        # Extrair ID do produto
        product_id = extract_ml_product_id(product_url)
        print(f"   🆔 Product ID: {product_id}")
        
        # ========================================
        # ETAPA 2: Tentar API Oficial
        # ========================================
        print("\n" + "━" * 70)
        print("ETAPA 2: Tentando API Oficial do Mercado Livre")
        print("━" * 70)
        
        token = load_ml_token()
        product_data = None
        
        if product_id:
            api_data = get_product_from_api(product_id, token)
            
            if api_data:
                print(f"   ✅ Dados obtidos via API!")
                
                # Extrair dados da API
                product_data = {
                    'title': api_data.get('title', api_data.get('name', '')),
                    'price': f"R$ {api_data.get('price', 0):.2f}",
                    'old_price': f"R$ {api_data.get('original_price', api_data.get('price', 0)):.2f}",
                    'images': [pic['url'] for pic in api_data.get('pictures', [])],
                    'external_id': api_data.get('id', product_id),
                    'condition': api_data.get('condition', 'new'),
                    'available_quantity': api_data.get('available_quantity', 0),
                    'sold_quantity': api_data.get('sold_quantity', 0)
                }
                
                # Videos
                if api_data.get('video_id'):
                    product_data['videos'] = [f"https://www.youtube.com/watch?v={api_data['video_id']}"]
                
                print(f"   📦 Título: {product_data['title'][:60]}...")
                print(f"   💰 Preço: {product_data['price']}")
        
        # ========================================
        # ETAPA 3: Scraping HTML (fallback)
        # ========================================
        if not product_data or not product_data.get('title'):
            print("\n" + "━" * 70)
            print("ETAPA 3: Scraping HTML (API não disponível)")
            print("━" * 70)
            
            product_data = scrape_mercadolivre_product(url)
            
            if not product_data or not product_data.get('title'):
                print("❌ Falha ao obter dados via API/Scraping")
                sys.exit(1)
        
        # ========================================
        # ETAPA 4: Screenshot
        # ========================================
        print("\n" + "━" * 70)
        print("ETAPA 4: Capturando screenshot")
        print("━" * 70)
        screenshot_path = take_screenshot_ml(product_url)
        
        # ========================================
        # ETAPA 5: OCR (complementar dados)
        # ========================================
        ocr_data = None
        if screenshot_path:
            print("\n" + "━" * 70)
            print("ETAPA 5: Extração via OCR (dados complementares)")
            print("━" * 70)
            ocr_data = extract_info_from_screenshot(screenshot_path)
        
        # ========================================
        # ETAPA 6: Enriquecer dados com OCR
        # ========================================
        print("\n" + "━" * 70)
        print("ETAPA 6: Enriquecimento de dados")
        print("━" * 70)
        product_data = enrich_ml_data_with_ocr(product_data, ocr_data)
        
        # ========================================
        # ETAPA 7: Categoria
        # ========================================
        print("\n" + "━" * 70)
        print("ETAPA 7: Seleção de categoria")
        print("━" * 70)

        # Resumo do produto antes de perguntar categoria
        print("\n" + "=" * 70)
        print("📌 RESUMO DO PRODUTO")
        print("=" * 70)
        print(f"  📝 Título   : {product_data.get('title', 'N/A')}")
        price_v = product_data.get('price', 'N/A')
        old_v   = product_data.get('old_price')
        print(f"  💰 Preço    : {price_v}")
        if old_v and old_v != price_v:
            print(f"  🔥 De      : {old_v}")
        aq = product_data.get('available_quantity')
        if aq is not None:
            status = "✅ Disponível" if aq > 0 else "❌ Sem estoque"
            print(f"  📊 Estoque : {aq} unidades — {status}")
        sq = product_data.get('sold_quantity')
        if sq:
            print(f"  🛒 Vendidos: {sq}")
        if product_data.get('free_shipping'):
            print(f"  📦 Frete grátis")
        print("=" * 70)

        suggested_category = detect_product_category(product_data['title'])
        selected_category = ask_user_category(suggested_category)

        # Perguntar subcategoria com opções dinâmicas das pastas existentes
        tag_folders = {
            "E":    "eletronicos",
            "CD":   "casa-decoracao",
            "ME":   "moda-estilo",
            "PET":  "petshop",
            "geral": "geral",
        }
        tag_folder = tag_folders.get(selected_category.upper(), "geral")
        staging_base = Path("/app/staging")
        tag_path = staging_base / tag_folder
        existing_subs = sorted([d.name for d in tag_path.iterdir() if d.is_dir()]) if tag_path.exists() else []

        print(f"\n📁 Subcategorias existentes em '{tag_folder}':")
        for i, sub in enumerate(existing_subs, 1):
            print(f"   {i:2}. {sub}")
        print(f"\n   Digite o número de uma opção, ou o nome de uma NOVA subcategoria")
        print(f"   (Enter para não usar subcategoria)")

        sub_input = input("📁 Subcategoria: ").strip().lower()

        if not sub_input:
            selected_subcategory = ""
            print("⚠️  Nenhuma subcategoria definida")
        elif sub_input.isdigit():
            idx = int(sub_input) - 1
            if 0 <= idx < len(existing_subs):
                selected_subcategory = existing_subs[idx]
                print(f"✅ Subcategoria: {selected_subcategory}")
            else:
                print(f"⚠️  Número inválido, sem subcategoria")
                selected_subcategory = ""
        else:
            selected_subcategory = sub_input
            print(f"✅ Nova subcategoria: {selected_subcategory}")
        
        # ========================================
        # ETAPA 8: Download de imagens
        # ========================================
        print("\n" + "━" * 70)
        print("ETAPA 8: Download de imagens")
        print("━" * 70)
        
        product_slug = slugify(product_data['title'])
        if product_data.get('images'):
            images_dir, downloaded = download_images_hq(
                product_data['images'],
                product_slug
            )
        else:
            images_dir = f"uploads/{product_slug}"
            downloaded = []
        
        # ========================================
        # ETAPA 9: Gerar JSON
        # ========================================
        print("\n" + "━" * 70)
        print("ETAPA 9: Geração do JSON de staging")
        print("━" * 70)
        
        json_file, json_data = generate_staging_json(
            product_data,
            images_dir,
            url,
            selected_category,
            selected_subcategory
        )
        
        # ========================================
        # RESUMO
        # ========================================
        print("\n" + "=" * 70)
        print("✅ PREPARAÇÃO COMPLETA CONCLUÍDA!")
        print("=" * 70)
        print(f"\n📝 Arquivo: {json_file}")
        print(f"🎯 Fontes: API + Scraping + OCR")
        print(f"📦 Produto: {product_data['title']}")
        print(f"🏷️  Categoria: {selected_category}" + (f" / {selected_subcategory}" if selected_subcategory else ""))
        print(f"💰 Preço: {product_data.get('price', 'N/A')}")
        if product_data.get('old_price') and product_data['old_price'] != product_data.get('price'):
            print(f"🔥 Preço antigo: {product_data['old_price']}")
        if product_data.get('free_shipping'):
            print(f"📦 Frete grátis")
        aq = product_data.get('available_quantity')
        if aq is not None:
            status = "✅ Disponível" if aq > 0 else "❌ Sem estoque"
            print(f"📊 Estoque: {aq} unidades — {status}")
        sq = product_data.get('sold_quantity')
        if sq:
            print(f"🛒 Vendidos: {sq}")
        print(f"🖼️  Imagens válidas: {len(downloaded)} baixadas")
        print(f"\n📋 Próximo passo: make stage\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelado")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                fotos_dir = Path('/app/fotos')
                fotos_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dest = fotos_dir / f'ml_{timestamp}.png'
                import shutil
                shutil.copy2(screenshot_path, dest)
                os.chmod(dest, 0o644)
                print(f"💾 Screenshot salvo em: {dest}")
            except Exception as e:
                print(f"⚠️  Não foi possível salvar screenshot: {e}")
            try:
                os.remove(screenshot_path)
                print(f"🧹 Screenshot temporário removido do /tmp")
            except:
                pass


if __name__ == "__main__":
    main()
