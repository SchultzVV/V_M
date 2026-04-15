#!/usr/bin/env python3
"""
Preparação COMPLETA de produtos da Amazon.
Combina scraping HTML + screenshot + OCR para dados mais precisos.

Fluxo:
1. Resolve link de afiliado da Amazon
2. Faz scraping HTML com Playwright
3. Tira screenshot da página
4. Usa OCR para complementar dados faltantes (preços, descontos, Prime)
5. Baixa imagens do produto
6. Gera JSON de staging

Uso:
    python scripts/amazon_prepare_best.py https://amzn.to/ABC123
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
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import sys as _sys; _sys.path.insert(0, __import__('os').path.dirname(__file__))
from category_selector import ask_user_category, ask_user_subcategory, detect_product_category


def resolve_amazon_link(url: str) -> str:
    """
    Resolve links de afiliado ou encurtados da Amazon.
    
    Exemplos:
    - https://amzn.to/ABC123 (encurtado)
    - https://www.amazon.com.br/dp/B08X123456
    - https://amazon.com.br/product-name/dp/B08X123456
    """
    print(f"\n🔗 Resolvendo link da Amazon...")
    print(f"   URL original: {url}")
    
    try:
        # Se for link encurtado, seguir redirecionamentos
        if 'amzn.to' in url or 'amzn.eu' in url:
            print(f"   📍 Link encurtado detectado, seguindo redirecionamentos...")
            response = requests.get(url, allow_redirects=True, timeout=15)
            final_url = response.url
            print(f"   ✅ URL final: {final_url}")
            return final_url
        
        return url
    
    except Exception as e:
        print(f"   ⚠️  Erro ao resolver link: {e}")
        return url


def extract_amazon_asin(url: str) -> str:
    """
    Extrai o ASIN (Amazon Standard Identification Number) da URL.
    
    Formato: /dp/B08X123456 ou /product/B08X123456
    """
    print(f"\n🔍 Extraindo ASIN...")
    
    # Padrões comuns de ASIN na URL
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            asin = match.group(1)
            print(f"   ✅ ASIN encontrado: {asin}")
            return asin
    
    print(f"   ⚠️  ASIN não encontrado na URL")
    return None


def scrape_amazon_with_playwright(url: str) -> dict:
    """
    Faz scraping da Amazon usando Playwright.
    Extrai: título, preço, descrição, imagens, avaliações, etc.
    """
    print(f"\n🌐 Fazendo scraping da Amazon com Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='pt-BR'
        )
        page = context.new_page()
        
        try:
            print(f"   🌐 Carregando página...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            
            product_data = {
                'title': '',
                'price': 0,
                'original_price': 0,
                'discount_percent': 0,
                'rating': 0,
                'rating_count': 0,
                'description': '',
                'images': [],
                'prime': False,
                'in_stock': True,
                'asin': ''
            }
            
            # Título
            title_selectors = ['#productTitle', 'h1.product-title', 'span#title']
            for selector in title_selectors:
                try:
                    title_elem = page.query_selector(selector)
                    if title_elem:
                        product_data['title'] = title_elem.inner_text().strip()
                        print(f"   ✅ Título: {product_data['title'][:60]}...")
                        break
                except:
                    continue
            
            # Preços
            # Amazon tem várias estruturas de preço
            price_selectors = [
                '.a-price .a-offscreen',
                '#priceblock_ourprice',
                '#priceblock_dealprice',
                '.a-price-whole',
                'span.priceToPay .a-offscreen'
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = page.query_selector(selector)
                    if price_elem:
                        price_text = price_elem.inner_text().strip()
                        # Limpar e converter: "R$ 1.234,56" -> 1234.56
                        price_clean = price_text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        product_data['price'] = float(price_clean)
                        print(f"   ✅ Preço: R$ {product_data['price']:.2f}")
                        break
                except:
                    continue
            
            # Preço antigo (riscado)
            old_price_selectors = [
                '.a-text-price .a-offscreen',
                'span.a-price.a-text-price',
                '#priceblock_saleprice',
            ]
            
            for selector in old_price_selectors:
                try:
                    old_price_elem = page.query_selector(selector)
                    if old_price_elem:
                        old_price_text = old_price_elem.inner_text().strip()
                        old_price_clean = old_price_text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        old_price_value = float(old_price_clean)
                        if old_price_value > product_data['price']:
                            product_data['original_price'] = old_price_value
                            discount = ((old_price_value - product_data['price']) / old_price_value) * 100
                            product_data['discount_percent'] = round(discount, 0)
                            print(f"   ✅ Preço antigo: R$ {old_price_value:.2f} (-{discount:.0f}%)")
                            break
                except:
                    continue
            
            # Amazon Prime
            try:
                prime_elem = page.query_selector('i.a-icon-prime')
                if prime_elem:
                    product_data['prime'] = True
                    print(f"   ✅ Amazon Prime disponível")
            except:
                pass
            
            # Avaliação
            try:
                rating_elem = page.query_selector('span.a-icon-alt')
                if rating_elem:
                    rating_text = rating_elem.inner_text()
                    rating_match = re.search(r'(\d+[,.]?\d*)', rating_text)
                    if rating_match:
                        product_data['rating'] = float(rating_match.group(1).replace(',', '.'))
                        print(f"   ✅ Avaliação: {product_data['rating']} estrelas")
            except:
                pass
            
            # Número de avaliações
            try:
                ratings_count_elem = page.query_selector('#acrCustomerReviewText')
                if ratings_count_elem:
                    count_text = ratings_count_elem.inner_text()
                    count_match = re.search(r'(\d+(?:\.\d+)*)', count_text)
                    if count_match:
                        count_str = count_match.group(1).replace('.', '')
                        product_data['rating_count'] = int(count_str)
                        print(f"   ✅ Avaliações: {product_data['rating_count']}")
            except:
                pass
            
            # Imagens
            try:
                # Amazon tem imagens em vários formatos
                image_selectors = [
                    '#landingImage',
                    '#imgBlkFront',
                    'img.a-dynamic-image'
                ]
                
                images_found = set()
                for selector in image_selectors:
                    img_elems = page.query_selector_all(selector)
                    for img in img_elems:
                        src = img.get_attribute('src') or img.get_attribute('data-old-hires')
                        if src and 'amazon' in src:
                            # Tentar obter imagem em alta resolução
                            src_hires = re.sub(r'\._.*?_\.', '._AC_SL1500_.', src)
                            images_found.add(src_hires)
                
                if images_found:
                    product_data['images'] = list(images_found)[:10]
                    print(f"   ✅ Imagens: {len(product_data['images'])} encontradas")
            except Exception as e:
                print(f"   ⚠️  Erro ao extrair imagens: {e}")
            
            # Disponibilidade
            try:
                availability_elem = page.query_selector('#availability')
                if availability_elem:
                    avail_text = availability_elem.inner_text().lower()
                    if 'indisponível' in avail_text or 'fora de estoque' in avail_text:
                        product_data['in_stock'] = False
                        print(f"   ⚠️  Produto indisponível")
            except:
                pass
            
            browser.close()
            return product_data
            
        except Exception as e:
            print(f"   ❌ Erro no scraping: {e}")
            browser.close()
            return None


def take_screenshot_amazon(url: str) -> str:
    """Tira screenshot da página da Amazon."""
    print(f"\n📸 Tirando screenshot da página...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='pt-BR'
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


def take_and_ocr_affiliate_full(affiliate_url: str) -> dict:
    """
    ETAPA 5B — Segundo scraping mandatório para confirmação de preço.

    Tira screenshot COMPLETO do link curto de afiliado, envia ao OCR e extrai
    preço atual + preço antigo de forma autoritativa (sem recorte de ROI).

    - Screenshot salvo em /app/fotos/affiliate_full_YYYYMMDD_HHMMSS.png
    - Toda a saída OCR é impressa para debug
    """
    result = {'price': 0.0, 'old_price': 0.0, 'raw_prices': [], 'raw_text': '', 'source': 'none'}

    print(f"\n📸 [ETAPA 5B] Screenshot completo do link de afiliado...")
    print(f"   🔗 {affiliate_url}")

    tmp_path = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1440, 'height': 900},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            page.goto(affiliate_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='_affiliate_full.png')
            tmp.close()
            page.screenshot(path=tmp.name, full_page=False)
            tmp_path = tmp.name
            print(f"   ✅ Screenshot capturado")
            browser.close()
    except Exception as e:
        print(f"   ⚠️  Erro ao capturar screenshot do afiliado: {e}")
        return result

    # Salvar cópia permanente para debug
    try:
        import shutil as _shutil
        debug_dir = Path('/app/fotos')
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = debug_dir / f'affiliate_full_{ts}.png'
        _shutil.copy2(tmp_path, dest)
        os.chmod(dest, 0o644)
        print(f"   💾 Screenshot salvo: {dest}")
    except Exception as e:
        print(f"   ⚠️  Não foi possível salvar screenshot: {e}")

    # OCR no screenshot completo
    try:
        with open(tmp_path, 'rb') as f:
            files = {'file': (os.path.basename(tmp_path), f, 'image/png')}
            response = requests.post('http://info-scrap:8000/extract', files=files, timeout=60)

        if response.status_code != 200:
            print(f"   ⚠️  OCR retornou status {response.status_code}")
            return result

        ocr = response.json()
        raw_text = ocr.get('text', '')
        result['raw_text'] = raw_text
        lines = [ln for ln in raw_text.strip().splitlines() if ln.strip()]

        print(f"\n   ┌─── [DEBUG OCR AFILIADO — {len(lines)} linhas] ───────────────────")
        for ln in lines:
            print(f"   │ {ln}")
        print(f"   └───────────────────────────────────────────────────────────")

        # Parser de preços BR
        raw_matches = re.findall(
            r'R\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)',
            raw_text, re.IGNORECASE
        )
        prices = []
        for m in raw_matches:
            s = m.strip()
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')
            elif re.match(r'^\d{1,3}\.\d{3}$', s):
                s = s.replace('.', '')
            try:
                v = round(float(s), 2)
                if 50.0 <= v <= 100_000.0:
                    prices.append(v)
            except ValueError:
                pass
        prices = sorted(set(prices))
        result['raw_prices'] = prices
        print(f"\n   💰 Preços detectados: {prices}")

        if len(prices) >= 2:
            result['price']     = min(prices)
            result['old_price'] = max(prices)
            result['source']    = 'affiliate_ocr'
            disc = round((result['old_price'] - result['price']) / result['old_price'] * 100)
            print(f"   ✅ Preço atual  : R$ {result['price']:.2f}")
            print(f"   ✅ Preço antigo : R$ {result['old_price']:.2f}  ({disc}% OFF)")
        elif len(prices) == 1:
            result['price']  = prices[0]
            result['source'] = 'affiliate_ocr'
            print(f"   ✅ Preço detectado: R$ {prices[0]:.2f}")
        else:
            print(f"   ℹ️  Nenhum preço encontrado no screenshot do afiliado")

    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  Serviço info-scrap não disponível (OCR do afiliado ignorado)")
    except Exception as e:
        print(f"   ⚠️  Erro no OCR do afiliado: {e}")
    finally:
        try:
            if tmp_path:
                os.remove(tmp_path)
        except Exception:
            pass

    return result


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


def enrich_amazon_data_with_ocr(scraping_data: dict, ocr_data: dict) -> dict:
    """
    Enriquece dados do scraping com OCR.
    OCR complementa dados faltantes ou confirma preços.
    """
    print(f"\n🔄 Enriquecendo dados com OCR...")
    
    enriched_data = scraping_data.copy()
    
    if not ocr_data or not ocr_data.get('success'):
        print(f"   ⚠️  OCR não disponível")
        return enriched_data
    
    ocr_text = ocr_data.get('text', '')
    
    # 1. Procurar preços
    price_pattern = r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
    prices_found = re.findall(price_pattern, ocr_text)
    
    if prices_found:
        print(f"   💰 Preços no OCR: {len(prices_found)}")
        
        # Se não temos preço, pegar do OCR
        if enriched_data['price'] == 0 and prices_found:
            try:
                price_str = prices_found[0].replace('.', '').replace(',', '.')
                price_value = float(price_str)
                enriched_data['price'] = price_value
                print(f"   ✨ Preço via OCR: R$ {price_value:.2f}")
            except:
                pass
        
        # Múltiplos preços = possível desconto
        if len(prices_found) >= 2 and enriched_data['original_price'] == 0:
            try:
                prices_values = [float(p.replace('.', '').replace(',', '.')) for p in prices_found[:2]]
                prices_values.sort(reverse=True)
                if prices_values[0] > prices_values[1]:
                    enriched_data['original_price'] = prices_values[0]
                    print(f"   ✨ Preço antigo via OCR: R$ {prices_values[0]:.2f}")
            except:
                pass
    
    # 2. Descontos
    discount_pattern = r'(\d{1,2})%\s*(?:OFF|off|desconto)'
    discounts_found = re.findall(discount_pattern, ocr_text)
    
    if discounts_found:
        try:
            discount_pct = int(discounts_found[0])
            enriched_data['discount_percent'] = discount_pct
            print(f"   🎉 Desconto via OCR: {discount_pct}%")
            
            # Calcular preço antigo se necessário
            if enriched_data['price'] > 0 and enriched_data['original_price'] == 0:
                enriched_data['original_price'] = enriched_data['price'] / (1 - discount_pct / 100)
        except:
            pass
    
    # 3. Amazon Prime
    if not enriched_data['prime']:
        if 'prime' in ocr_text.lower() or 'frete grátis' in ocr_text.lower():
            enriched_data['prime'] = True
            print(f"   ✨ Prime detectado via OCR")
    
    # 4. Cupons
    cupom_pattern = r'(?:cupom|código)\s*[:-]?\s*([A-Z0-9]{4,})'
    cupons_found = re.findall(cupom_pattern, ocr_text, re.IGNORECASE)
    if cupons_found:
        enriched_data['cupons'] = cupons_found
        print(f"   🎫 Cupons: {', '.join(cupons_found)}")
    
    enriched_data['ocr_text'] = ocr_text
    enriched_data['ocr_lines'] = ocr_data.get('lines', [])
    
    print(f"   ✅ Enriquecimento concluído!")
    
    return enriched_data


def download_amazon_images(image_urls: list, product_slug: str) -> tuple:
    """Baixa imagens do produto."""
    print(f"\n📥 Baixando imagens...")
    
    # Determinar diretório
    if os.path.exists('/app'):
        base_dir = Path('/app/uploads')
    else:
        base_dir = Path('services/site/uploads')
    
    product_dir = base_dir / product_slug
    product_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    total_size = 0
    
    for idx, img_url in enumerate(image_urls[:10], 1):
        try:
            response = requests.get(img_url, timeout=15)
            if response.status_code == 200:
                # Detectar extensão
                content_type = response.headers.get('content-type', '')
                ext = '.jpg'
                if 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                
                filename = f"image_{idx:02d}{ext}"
                filepath = product_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                size = len(response.content)
                total_size += size
                downloaded.append(str(filepath))
                
                print(f"   ✅ {filename} ({size/1024:.1f} KB)")
        
        except Exception as e:
            print(f"   ❌ Erro na imagem {idx}: {e}")
    
    print(f"\n📊 Total: {total_size / 1024 / 1024:.2f} MB")
    print(f"📂 Diretório: {product_dir}")
    
    return str(product_dir), downloaded


def ask_user_category_amazon() -> tuple:
    """Delegado para category_selector (módulo compartilhado)."""
    tag        = ask_user_category()
    subcategory = ask_user_subcategory(tag)
    return tag, subcategory


def create_amazon_json(product_data: dict, product_dir: str, original_url: str, tag: str, subcategory: str) -> tuple:
    """Cria JSON de staging para Amazon."""
    
    product_slug = slugify(product_data['title'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    tag_folders = {"E": "eletronicos", "CD": "casa-decoracao", "ME": "moda-estilo", "PET": "petshop", "geral": "geral"}
    tag_folder = tag_folders.get(tag.upper(), "geral")
    
    if subcategory:
        staging_dir = Path(f"/app/staging/{tag_folder}/{subcategory}")
    else:
        staging_dir = Path(f"/app/staging/{tag_folder}")
    
    staging_dir.mkdir(parents=True, exist_ok=True)
    json_filename = f"{product_slug}_{timestamp}.json"
    json_path = staging_dir / json_filename
    
    price_value = product_data['price']
    old_price_value = product_data.get('original_price', price_value)
    
    price_str = f"R$ {price_value:.2f}"
    old_price_str = f"R$ {old_price_value:.2f}"
    
    product_json = {
        "platform": "amazon",
        "external_id": product_data.get('asin', ''),
        "title": product_data['title'],
        "price": price_str,
        "oldPrice": old_price_str,
        "images_local": str(product_dir).replace('/app/', ''),
        "images": [],
        "link": original_url,
        "tag": tag.upper(),
        "subcategory": subcategory,
        "disponivel": product_data.get('in_stock', True),
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    if product_data.get('prime'):
        product_json['prime'] = True
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(product_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 JSON salvo: {json_path}")
    
    return json_path, product_json


def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python amazon_prepare_best.py <URL_AMAZON>")
        sys.exit(1)
    
    original_url = sys.argv[1]
    screenshot_path = None
    
    try:
        print("=" * 70)
        print("🚀 PREPARAÇÃO COMPLETA - AMAZON")
        print("   (Scraping + Screenshot + OCR)")
        print("=" * 70)
        
        # ETAPA 1: Resolver link
        print("\n" + "━"*70)
        print("ETAPA 1: Resolvendo link")
        print("━"*70)
        final_url = resolve_amazon_link(original_url)
        
        # ETAPA 2: Extrair ASIN
        print("\n" + "━"*70)
        print("ETAPA 2: Extraindo ASIN")
        print("━"*70)
        asin = extract_amazon_asin(final_url)
        
        # ETAPA 3: Scraping
        print("\n" + "━"*70)
        print("ETAPA 3: Scraping HTML")
        print("━"*70)
        product_data = scrape_amazon_with_playwright(final_url)
        
        if not product_data or not product_data.get('title'):
            print("\n❌ Falha ao obter dados")
            sys.exit(1)
        
        if asin:
            product_data['asin'] = asin
        
        # ETAPA 4: Screenshot
        print("\n" + "━"*70)
        print("ETAPA 4: Screenshot")
        print("━"*70)
        screenshot_path = take_screenshot_amazon(final_url)
        
        # ETAPA 5: OCR
        ocr_data = None
        if screenshot_path:
            print("\n" + "━"*70)
            print("ETAPA 5: Extração OCR")
            print("━"*70)
            ocr_data = extract_info_from_screenshot(screenshot_path)

        # ETAPA 5B: Screenshot completo do link de afiliado — preço mandatório
        print("\n" + "━"*70)
        print("ETAPA 5B: OCR mandatório — screenshot completo do link de afiliado")
        print("━"*70)
        affiliate_ocr = take_and_ocr_affiliate_full(original_url)
        if affiliate_ocr['source'] == 'affiliate_ocr' and affiliate_ocr['price'] > 0:
            print(f"\n   🔒 Preços do afiliado sobrescrevem dados anteriores (mandatório):")
            product_data['price'] = affiliate_ocr['price']
            if affiliate_ocr['old_price'] > affiliate_ocr['price']:
                product_data['original_price'] = affiliate_ocr['old_price']
                print(f"      price         : R$ {affiliate_ocr['price']:.2f}")
                print(f"      original_price: R$ {affiliate_ocr['old_price']:.2f}")
            else:
                print(f"      price         : R$ {affiliate_ocr['price']:.2f}")
        else:
            print(f"   ⚠️  OCR do afiliado sem preços — mantendo dados anteriores")

        # ETAPA 6: Enriquecer
        print("\n" + "━"*70)
        print("ETAPA 6: Enriquecimento")
        print("━"*70)
        product_data = enrich_amazon_data_with_ocr(product_data, ocr_data)
        
        # ETAPA 7: Categoria
        print("\n" + "━"*70)
        print("ETAPA 7: Categorização")
        print("━"*70)
        _force_cat = os.environ.get("FORCE_CATEGORY", "").strip()
        _force_sub = os.environ.get("FORCE_SUBCATEGORY", "").strip()
        if _force_cat and _force_cat.upper() == "AUTO":
            tag = detect_product_category(product_data.get('title', ''))
            subcategory = _force_sub
            print(f"  📦 Categoria (regex auto): {tag}" + (f" / {subcategory}" if subcategory else ""))
        elif _force_cat:
            tag = _force_cat.upper()
            subcategory = _force_sub
            print(f"  📦 Categoria (forçada): {tag}" + (f" / {subcategory}" if subcategory else ""))
        else:
            tag, subcategory = ask_user_category_amazon()
        
        # ETAPA 8: Download de imagens
        print("\n" + "━"*70)
        print("ETAPA 8: Download de imagens")
        print("━"*70)
        product_slug = slugify(product_data['title'])
        if product_data.get('images'):
            product_dir, downloaded = download_amazon_images(product_data['images'], product_slug)
        else:
            product_dir = f"uploads/{product_slug}"
            downloaded = []
        
        # ETAPA 9: JSON
        print("\n" + "━"*70)
        print("ETAPA 9: Geração do JSON")
        print("━"*70)
        json_path, product_json = create_amazon_json(product_data, product_dir, original_url, tag, subcategory)
        
        # RESUMO
        print("\n" + "=" * 70)
        print("✅ PREPARAÇÃO CONCLUÍDA!")
        print("=" * 70)
        print(f"\n📝 Arquivo: {json_path}")
        print(f"📦 Produto: {product_data['title']}")
        print(f"💰 Preço: R$ {product_data['price']:.2f}")
        if product_data.get('discount_percent', 0) > 0:
            print(f"🔥 Desconto: {product_data['discount_percent']:.0f}% OFF")
        if product_data.get('prime'):
            print(f"⚡ Amazon Prime")
        print(f"🖼️  Imagens: {len(downloaded)} baixadas")
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
                dest = fotos_dir / f'amazon_{timestamp}.png'
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
