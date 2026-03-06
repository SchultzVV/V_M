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
from pathlib import Path
from playwright.sync_api import sync_playwright

# Importar funções do auto_prepare_ml
sys.path.insert(0, os.path.dirname(__file__))
from auto_prepare_ml import (
    follow_affiliate_link,
    scrape_mercadolivre_product,
    download_images,
    detect_product_category,
    ask_user_category,
    generate_staging_json
)


def take_screenshot(url: str) -> str:
    """
    Tira um screenshot da página do produto usando Playwright.
    
    Args:
        url: URL da página do produto
        
    Returns:
        Caminho do arquivo de screenshot temporário
    """
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
            
            # Aguarda um pouco para garantir que conteúdo dinâmico carregou
            page.wait_for_timeout(2000)
            
            # Cria arquivo temporário para screenshot
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            screenshot_path = temp_file.name
            temp_file.close()
            
            print(f"   📷 Capturando imagem...")
            page.screenshot(path=screenshot_path, full_page=True)
            
            print(f"   ✅ Screenshot salvo: {screenshot_path}")
            
            return screenshot_path
            
        except Exception as e:
            print(f"   ❌ Erro ao tirar screenshot: {e}")
            return None
            
        finally:
            browser.close()


def extract_info_from_screenshot(screenshot_path: str) -> dict:
    """
    Envia screenshot para o serviço info-scrap e extrai informações.
    
    Args:
        screenshot_path: Caminho do arquivo de screenshot
        
    Returns:
        Dicionário com dados extraídos via OCR
    """
    print(f"\n🔍 Extraindo informações do screenshot via OCR...")
    
    # Endpoint do serviço info-scrap
    url = "http://info-scrap:8000/extract"
    
    try:
        with open(screenshot_path, 'rb') as f:
            files = {'file': (os.path.basename(screenshot_path), f, 'image/png')}
            
            print(f"   📤 Enviando para serviço de extração...")
            response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"   ✅ Extração realizada com sucesso!")
            print(f"   📄 Linhas extraídas: {result.get('line_count', 0)}")
            
            return result
        else:
            print(f"   ❌ Erro na extração: Status {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Não foi possível conectar ao serviço info-scrap")
        print(f"   💡 Verifique se o container está rodando: docker ps | grep info-scrap")
        return None
        
    except Exception as e:
        print(f"   ❌ Erro inesperado: {e}")
        return None


def enrich_product_data(html_data: dict, ocr_data: dict) -> dict:
    """
    Enriquece dados do scraping HTML com informações extraídas via OCR.
    
    O OCR pode capturar informações que o HTML não mostra facilmente,
    como preços em banners, descontos especiais, etc.
    
    Args:
        html_data: Dados extraídos via scraping HTML
        ocr_data: Dados extraídos via OCR do screenshot
        
    Returns:
        Dados enriquecidos combinando HTML + OCR
    """
    print(f"\n🔄 Enriquecendo dados com informações do OCR...")
    
    enriched_data = html_data.copy()
    
    if not ocr_data or not ocr_data.get('success'):
        print(f"   ⚠️  Dados OCR não disponíveis, usando apenas HTML")
        return enriched_data
    
    ocr_text = ocr_data.get('text', '')
    ocr_lines = ocr_data.get('lines', [])
    
    # Tentar extrair informações adicionais do OCR
    
    # 1. Procurar por preços que podem ter sido perdidos
    import re
    price_pattern = r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
    prices_found = re.findall(price_pattern, ocr_text)
    
    if prices_found:
        print(f"   💰 Preços encontrados no OCR: {len(prices_found)}")
        # Aqui você pode implementar lógica para validar/comparar preços
    
    # 2. Procurar por percentuais de desconto
    discount_pattern = r'(\d{1,2})%\s*OFF'
    discounts_found = re.findall(discount_pattern, ocr_text)
    
    if discounts_found:
        print(f"   🎉 Descontos encontrados no OCR: {discounts_found}")
        # Se o HTML não capturou desconto mas OCR encontrou, adicionar
        if not enriched_data.get('has_discount') and discounts_found:
            try:
                discount_pct = int(discounts_found[0])
                enriched_data['has_discount'] = True
                enriched_data['discount_percentage'] = discount_pct
                print(f"   ✨ Desconto adicionado: {discount_pct}% OFF")
            except:
                pass
    
    # 3. Procurar por informações de envio
    if 'FULL' in ocr_text or 'grátis' in ocr_text.lower():
        enriched_data['free_shipping'] = True
        print(f"   📦 Frete grátis detectado via OCR")
    
    # 4. Adicionar texto OCR completo para referência
    enriched_data['ocr_text'] = ocr_text
    enriched_data['ocr_lines'] = ocr_lines
    
    print(f"   ✅ Dados enriquecidos com sucesso!")
    
    return enriched_data


def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python prepare_full.py <URL_DO_MERCADO_LIVRE>")
        print("\nExemplo:")
        print("  python scripts/prepare_full.py https://mercadolivre.com/sec/ABC123")
        sys.exit(1)
    
    url = sys.argv[1]
    screenshot_path = None
    
    try:
        print("=" * 70)
        print("🚀 PREPARAÇÃO COMPLETA DE PRODUTO - MERCADO LIVRE")
        print("   (Scraping HTML + Screenshot + OCR)")
        print("=" * 70)
        print(f"\n🔗 URL: {url}\n")
        
        # 1. Seguir link de afiliado até página do produto
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 1: Resolvendo link de afiliado")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        product_url = follow_affiliate_link(url)
        
        if not product_url:
            print("❌ Falha ao resolver link do produto")
            sys.exit(1)
        
        # 2. Tirar screenshot da página
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 2: Capturando screenshot")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        screenshot_path = take_screenshot(product_url)
        
        # 3. Extrair informações do screenshot via OCR
        ocr_data = None
        if screenshot_path:
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("ETAPA 3: Extração de informações via OCR")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            ocr_data = extract_info_from_screenshot(screenshot_path)
        else:
            print("\n⚠️  Screenshot não disponível, continuando sem OCR...")
        
        # 4. Fazer scraping HTML tradicional
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 4: Scraping HTML")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        html_data = scrape_mercadolivre_product(url)
        
        if not html_data:
            print("❌ Falha ao obter dados do produto via HTML")
            sys.exit(1)
        
        # 5. Enriquecer dados combinando HTML + OCR
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 5: Enriquecimento de dados")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        product_data = enrich_product_data(html_data, ocr_data)
        
        # 6. Baixar imagens do produto
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 6: Download de imagens")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        from slugify import slugify
        product_slug = slugify(product_data['title'])
        images_dir = download_images(product_data['images'], product_slug)
        
        if not images_dir:
            print("⚠️  Continuando sem imagens...")
            images_dir = "uploads/fallback_img"
        
        # 7. Detectar categoria e perguntar ao usuário
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 7: Seleção de categoria")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        suggested_category = detect_product_category(product_data['title'])
        selected_category = ask_user_category(suggested_category)
        
        # 8. Gerar JSON de staging
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("ETAPA 8: Geração do JSON de staging")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        staging_file = generate_staging_json(
            product_data, 
            images_dir, 
            url,  # Link de afiliado original
            selected_category
        )
        
        print("\n" + "=" * 70)
        print("✅ PREPARAÇÃO COMPLETA CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        print(f"\n📝 Arquivo gerado: {staging_file}")
        print(f"🎯 Dados utilizados: HTML + OCR")
        print(f"\n📋 Próximo passo: execute 'make stage' para publicar no site\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Erro durante a preparação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Limpar arquivo temporário de screenshot
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
                print(f"🧹 Screenshot temporário removido")
            except:
                pass


if __name__ == "__main__":
    main()
