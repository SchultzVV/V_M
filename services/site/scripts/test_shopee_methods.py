#!/usr/bin/env python3
"""
Testa diferentes métodos de scraping da Shopee para ver qual funciona.
"""
import sys
import requests
from playwright.sync_api import sync_playwright
import re

url = "https://shopee.com.br/opaanlp/1103946075/22597120770"

print("="*70)
print("TESTE 1: Requests simples + regex")
print("="*70)
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9',
    }
    response = requests.get(url, headers=headers, timeout=15)
    html = response.text
    
    print(f"Status: {response.status_code}")
    print(f"Tamanho HTML: {len(html)} bytes")
    
    # Buscar PDP_BFF_DATA
    if 'PDP_BFF_DATA' in html:
        print("✅ PDP_BFF_DATA encontrado!")
        pdp_match = re.search(r'"PDP_BFF_DATA".*?"cachedMap"', html, re.DOTALL)
        if pdp_match:
            json_text = pdp_match.group(0)
            
            # Extrair título
            title_match = re.search(r'"title":"([^"]+)"', json_text)
            if title_match:
                print(f"✅ Título: {title_match.group(1)[:60]}...")
            
            # Extrair preço
            price_match = re.search(r'"price_min":(\d+)', json_text)
            if price_match:
                price = int(price_match.group(1)) / 100000
                print(f"✅ Preço: R$ {price:.2f}")
            
            # Extrair estoque
            stock_match = re.search(r'"stock":(\d+)', json_text)
            if stock_match:
                print(f"✅ Estoque: {stock_match.group(1)}")
    else:
        print("❌ PDP_BFF_DATA não encontrado")
        
        # Verificar se tem captcha/bloqueio
        if 'captcha' in html.lower():
            print("🚫 CAPTCHA detectado")
        if 'robot' in html.lower():
            print("🚫 Detecção de robô")
            
        # Buscar qualquer JSON
        title_match = re.search(r'"title":"([^"]+)"', html)
        if title_match:
            print(f"⚠️ Encontrou título em outro lugar: {title_match.group(1)[:60]}")
        
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "="*70)
print("TESTE 2: Playwright com browser headless")
print("="*70)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='pt-BR',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Remover webdriver detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.new_page()
        
        print("Carregando página...")
        response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
        print(f"Status: {response.status}")
        
        # Aguardar JS
        page.wait_for_timeout(5000)
        
        html = page.content()
        print(f"Tamanho HTML: {len(html)} bytes")
        
        # Buscar dados
        if 'PDP_BFF_DATA' in html:
            print("✅ PDP_BFF_DATA encontrado!")
            pdp_match = re.search(r'"PDP_BFF_DATA".*?"cachedMap"', html, re.DOTALL)
            if pdp_match:
                json_text = pdp_match.group(0)[:2000]
                
                title_match = re.search(r'"title":"([^"]+)"', json_text)
                if title_match:
                    print(f"✅ Título: {title_match.group(1)[:60]}...")
                
                price_match = re.search(r'"price_min":(\d+)', json_text)
                if price_match:
                    price = int(price_match.group(1)) / 100000
                    print(f"✅ Preço: R$ {price:.2f}")
        else:
            print("❌ PDP_BFF_DATA não encontrado")
            
            # Testar seletores CSS
            print("\nTestando seletores CSS...")
            selectors = [
                ('h1', 'Título H1'),
                ('[class*="title"]', 'Class title'),
                ('[class*="product-name"]', 'Product name'),
                ('[class*="price"]', 'Preço'),
            ]
            
            for selector, desc in selectors:
                try:
                    el = page.query_selector(selector)
                    if el:
                        text = el.inner_text()[:100]
                        print(f"  ✅ {desc}: {text}")
                except:
                    print(f"  ❌ {desc}: não encontrado")
        
        # Salvar HTML
        with open('/tmp/shopee_test.html', 'w') as f:
            f.write(html)
        print("\n💾 HTML salvo em /tmp/shopee_test.html")
        
        browser.close()
        
except Exception as e:
    print(f"❌ Erro Playwright: {e}")

print("\n" + "="*70)
print("RESUMO")
print("="*70)
print("Se o Teste 1 funcionar: usar requests + regex")
print("Se o Teste 2 funcionar: usar Playwright")
print("Se nenhum funcionar: Shopee bloqueou completamente")
