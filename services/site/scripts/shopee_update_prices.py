#!/usr/bin/env python3
"""
Script para atualizar preços e disponibilidade de produtos da Shopee.
Usa Playwright para renderizar JavaScript e extrair dados atualizados.

Uso:
    python3 shopee_update_prices.py <URL_SHOPEE>
    
Exemplo:
    python3 shopee_update_prices.py "https://s.shopee.com.br/8Uy0Bqs7ap"
"""

import sys
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def extract_product_data(page):
    """
    Extrai preço atual, preço antigo, disponibilidade e imagens da página renderizada.
    
    Returns:
        dict com: price, oldPrice, available, images
    """
    data = {
        "price": None,
        "oldPrice": None,
        "available": True,
        "images": []
    }
    
    try:
        # Aguardar um pouco para JavaScript carregar
        page.wait_for_timeout(3000)
        
        # Estratégia 1: Buscar por seletores comuns de preço
        selectors_price = [
            '[class*="pqTWkA"]',  # Classe comum do Shopee para preço
            '[class*="price-main"]',
            '[class*="product-price"]',
            '[data-testid="product-price"]',
            'div[class*="price"]:not([class*="before"])',
        ]
        
        for selector in selectors_price:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text()
                    # Extrair valor numérico
                    match = re.search(r'R\$?\s*(\d+[.,]\d+)', text.replace('.', '').replace(',', '.'))
                    if match:
                        data["price"] = f"R$ {match.group(1)}"
                        print(f"   ✅ Preço atual: {data['price']}")
                        break
            except:
                continue
        
        # Estratégia 2: Preço antigo (desconto)
        selectors_old_price = [
            '[class*="discount"]',
            '[class*="before"]',
            '[class*="original"]',
            '[class*="line-through"]',
            'div[style*="text-decoration: line-through"]',
        ]
        
        for selector in selectors_old_price:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text()
                    match = re.search(r'R\$?\s*(\d+[.,]\d+)', text.replace('.', '').replace(',', '.'))
                    if match:
                        data["oldPrice"] = f"R$ {match.group(1)}"
                        print(f"   ✅ Preço antigo: {data['oldPrice']}")
                        break
            except:
                continue
        
        # Estratégia 3: Verificar disponibilidade
        unavailable_texts = ['esgotado', 'sold out', 'indisponível', 'sem estoque']
        page_content = page.content().lower()
        
        for text in unavailable_texts:
            if text in page_content:
                data["available"] = False
                print(f"   ⚠️ Produto indisponível")
                break
        
        if data["available"]:
            print(f"   ✅ Produto disponível")
        
        # Estratégia 4: Extrair URLs de imagens
        selectors_images = [
            'img[class*="product"]',
            'img[class*="gallery"]',
            '[class*="image-gallery"] img',
            'img[src*="shopee"]',
        ]
        
        for selector in selectors_images:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:10]:  # Limitar a 10 imagens
                    src = element.get_attribute('src')
                    if src and 'shopee' in src and src not in data["images"]:
                        # Pegar versão de alta qualidade
                        if '_tn' in src:
                            src = src.replace('_tn', '')
                        data["images"].append(src)
                
                if data["images"]:
                    print(f"   ✅ {len(data['images'])} imagens encontradas")
                    break
            except:
                continue
        
        # Fallback: Buscar no HTML usando regex se não encontrou preço
        print(f"   ⚠️ Tentando extrair dados do HTML renderizado...")
        html = page.content()
        
        # Extrair título se não tiver
        if not data.get("title"):
            title_match = re.search(r'"title":"([^"]+)"', html)
            if title_match:
                data["title"] = title_match.group(1)
                print(f"   ✅ Título: {data['title'][:50]}...")
        
        # Procurar stock
        stock_match = re.search(r'"stock":(\d+)', html)
        if stock_match:
            stock = int(stock_match.group(1))
            data["available"] = stock > 0
            data["stock"] = stock
            print(f"   ✅ Estoque: {stock} unidades")
        
        # Extrair imagens
        image_pattern = r'"image":"([a-z0-9\-]+)"'
        image_matches = re.findall(image_pattern, html)
        if image_matches:
            base_url = "https://down-br.img.susercontent.com/file/"
            # Pegar apenas imagens únicas
            unique_images = list(dict.fromkeys(image_matches))[:10]
            data["images"] = [f"{base_url}{img}" for img in unique_images]
            print(f"   ✅ {len(data['images'])} imagens extraídas")
        
        # Procurar por PDP_BFF_DATA no HTML (dados renderizados)
        pdp_match = re.search(r'"PDP_BFF_DATA".*?"cachedMap"', html, re.DOTALL)
        if pdp_match:
            try:
                # Salvar para debug
                debug_json_path = Path("/tmp/shopee_pdp_data.txt")
                with open(debug_json_path, 'w', encoding='utf-8') as f:
                    f.write(pdp_match.group(0)[:5000])
                print(f"   🐛 PDP_BFF_DATA salvo em: {debug_json_path}")
                
                json_text = pdp_match.group(0)
                
                # Tentar múltiplos padrões de preço
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
                            price_reais = price_cents / 100000  # Shopee usa price * 100000
                            data["price"] = f"R$ {price_reais:.2f}"
                            print(f"   ✅ Preço atual ({name}): {data['price']}")
                            break
                
                # Procurar preço antigo
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
                            price_reais = price_cents / 100000
                            data["oldPrice"] = f"R$ {price_reais:.2f}"
                            print(f"   ✅ Preço antigo: {data['oldPrice']}")
                            break
                
                # Se achou preço atual mas não o antigo, tentar calcular pelo desconto
                if data.get("price") and not data.get("oldPrice"):
                    show_discount_match = re.search(r'"show_discount":(\d+)', json_text)
                    if show_discount_match:
                        discount_pct = int(show_discount_match.group(1))
                        if discount_pct > 0:
                            current_price = float(data["price"].replace("R$ ", "").replace(",", "."))
                            old_price = current_price / (1 - discount_pct/100)
                            data["oldPrice"] = f"R$ {old_price:.2f}"
                            print(f"   ✅ Preço antigo calculado ({discount_pct}% off): {data['oldPrice']}")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao parsear PDP_BFF_DATA: {str(e)}")
            
            # Fallback adicional: procurar padrões gerais se ainda não encontrou
            if not data["price"]:
                price_patterns = [
                    r'"price_min":(\d+)',
                    r'"current_price":(\d+)',
                    r'"price":(\d+)',
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, html)
                    if matches:
                        price_cents = int(matches[0])
                        price_reais = price_cents / 100000
                        data["price"] = f"R$ {price_reais:.2f}"
                        print(f"   ✅ Preço extraído: {data['price']}")
                        break
    
    except PlaywrightTimeout:
        print("   ⚠️ Timeout ao carregar página")
    except Exception as e:
        print(f"   ⚠️ Erro ao extrair dados: {str(e)}")
    
    return data


def scrape_shopee_with_playwright(url):
    """
    Usa Playwright para renderizar a página e extrair dados.
    """
    print(f"\n🌐 Acessando: {url}")
    
    with sync_playwright() as p:
        # Lançar navegador headless
        browser = p.chromium.launch(headless=True)
        
        # Criar contexto com user agent brasileiro
        context = browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        
        page = context.new_page()
        
        try:
            # Navegar para a URL
            print("   ⏳ Carregando página...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            print("   ✅ Página carregada")
            
            # Extrair dados
            print("   📊 Extraindo dados...")
            
            # Debug: Salvar HTML renderizado
            html_content = page.content()
            debug_path = Path("/tmp/shopee_rendered.html")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   🐛 HTML renderizado salvo em: {debug_path}")
            
            data = extract_product_data(page)
            
            return data
            
        except PlaywrightTimeout:
            print("   ❌ Timeout ao carregar página")
            return None
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")
            return None
        finally:
            browser.close()


def update_product_json(json_path, updated_data):
    """
    Atualiza o JSON do produto com os novos dados.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            product = json.load(f)
        
        # Atualizar campos
        if updated_data.get('price'):
            product['price'] = updated_data['price']
        
        if updated_data.get('oldPrice'):
            product['oldPrice'] = updated_data['oldPrice']
        
        product['available'] = updated_data.get('available', True)
        
        # Atualizar imagens se necessário
        if updated_data.get('images') and not product.get('images'):
            product['images'] = updated_data['images']
        
        # Salvar
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ JSON atualizado: {json_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao atualizar JSON: {str(e)}")
        return False


def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python3 shopee_update_prices.py <URL_SHOPEE> [JSON_PATH]")
        print("\nExemplo:")
        print('   python3 shopee_update_prices.py "https://s.shopee.com.br/8Uy0Bqs7ap"')
        print('   python3 shopee_update_prices.py "https://s.shopee.com.br/8Uy0Bqs7ap" "staging/product.json"')
        sys.exit(1)
    
    url = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 60)
    print("🛒 SHOPEE - Atualização de Preços e Disponibilidade")
    print("=" * 60)
    
    # Fazer scraping
    data = scrape_shopee_with_playwright(url)
    
    if not data:
        print("\n❌ Não foi possível acessar o produto")
        sys.exit(1)
    
    # Mostrar dados extraídos (mesmo parciais)
    print("\n" + "=" * 60)
    print("📦 DADOS EXTRAÍDOS:")
    print("=" * 60)
    if data.get('title'):
        print(f"📝 Título:         {data['title'][:60]}...")
    if data.get('price'):
        print(f"💰 Preço atual:    {data['price']}")
    else:
        print(f"💰 Preço atual:    ⚠️  NÃO ENCONTRADO")
    if data.get('oldPrice'):
        print(f"💸 Preço antigo:   {data['oldPrice']}")
    print(f"📦 Disponível:     {'Sim' if data.get('available') else 'Não'}")
    if data.get('stock'):
        print(f"📊 Estoque:        {data['stock']} unidades")
    if data.get('images'):
        print(f"🖼️  Imagens:        {len(data['images'])} encontradas")
    
    # Atualizar JSON se fornecido
    if json_path:
        json_file = Path(json_path)
        if json_file.exists():
            update_product_json(json_file, data)
        else:
            print(f"\n⚠️ Arquivo não encontrado: {json_path}")
    else:
        # Mostrar JSON de saída
        print("\n" + "=" * 60)
        print("📄 JSON OUTPUT:")
        print("=" * 60)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    
    print("\n✅ Concluído!")
    
    # Retornar status baseado se conseguiu extrair dados essenciais
    if data.get('title') or data.get('stock') is not None:
        sys.exit(0)  # Sucesso parcial
    else:
        sys.exit(1)  # Falha total


if __name__ == "__main__":
    main()
