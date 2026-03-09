#!/usr/bin/env python3
"""
Script para tirar screenshot no HOST Ubuntu com browser REAL (headed).
Roda fora do Docker, usa o DISPLAY do Ubuntu (DISPLAY=:1).

Uso:
    python3 take_screenshot_host.py <URL> [output_path]

Saída:
    Imprime o caminho absoluto do screenshot para stdout (capturado pelo Makefile)
"""

import sys
import os
import tempfile
from urllib.parse import urlparse, urlunparse
from pathlib import Path

def _is_login_page(page) -> bool:
    try:
        current_url = page.url
        if any(x in current_url for x in ['/login', 'buyer/login', 'shopee.com.br/?']):
            return True
        body_text = page.inner_text('body')[:1500]
        has_price = 'R$' in body_text
        has_login_markers = any(x in body_text for x in [
            'Fazer login com SMS', 'Esqueci minha senha',
            'Fazer login com Facebook', 'Entrar com Google'
        ])
        return has_login_markers and not has_price
    except Exception:
        return False


def take_screenshot(url: str, output_path: str = None) -> str:
    """
    Abre browser REAL no Ubuntu (headed) e tira screenshot da URL.
    Remove query params de tracking antes de navegar.

    Args:
        url: URL do produto
        output_path: Caminho de saída opcional. Se None, salva em screenshots/

    Returns:
        Caminho absoluto do screenshot
    """
    from playwright.sync_api import sync_playwright

    # Remove query params de tracking que causam redirect para login
    parsed = urlparse(url)
    clean_url = urlunparse(parsed._replace(query=''))
    print(f"[host-screenshot] URL: {clean_url}", file=sys.stderr)

    # Salva em /tmp (host) — o Makefile faz docker cp para o container
    if output_path is None:
        import hashlib, time
        slug = hashlib.md5(clean_url.encode()).hexdigest()[:12]
        ts = int(time.time())
        output_path = f"/tmp/shopee_screenshot_{slug}_{ts}.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # REAL browser — sem headless
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
            ]
        )
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US'] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        print(f"[host-screenshot] Navegando...", file=sys.stderr)
        page.goto(clean_url, wait_until='domcontentloaded', timeout=40000)

        try:
            page.wait_for_load_state('networkidle', timeout=12000)
        except Exception:
            pass

        page.wait_for_timeout(3000)

        current_url = page.url
        print(f"[host-screenshot] URL atual: {current_url[:100]}", file=sys.stderr)

        if _is_login_page(page):
            print(f"[host-screenshot] ⚠️  Página de login detectada mesmo com browser real!", file=sys.stderr)
            browser.close()
            return None

        # Fechar popup LGPD/cookies
        try:
            page.keyboard.press('Escape')
            page.wait_for_timeout(800)
        except Exception:
            pass

        # Esperar elemento de preço
        try:
            page.wait_for_selector(
                '[class*="price" i], [class*="Price"], [class*="priceSale"], '
                '.pqTWkA, .HFf5M2, [class*="discount"]',
                timeout=8000
            )
            print(f"[host-screenshot] ✅ Elemento de preço encontrado", file=sys.stderr)
        except Exception:
            print(f"[host-screenshot] ⚠️  Seletor de preço não encontrado, continuando...", file=sys.stderr)

        # Scroll suave para carregar conteúdo lazy
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        page.wait_for_timeout(1200)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3)")
        page.wait_for_timeout(1200)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1200)

        page.screenshot(path=output_path, full_page=False)
        browser.close()

        print(f"[host-screenshot] ✅ Screenshot salvo: {output_path}", file=sys.stderr)
        return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 take_screenshot_host.py <URL> [output_path]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None

    result = take_screenshot(url, out)
    if result:
        # Imprime APENAS o path para stdout (capturado pelo Makefile via $(...))
        print(result)
        sys.exit(0)
    else:
        sys.exit(1)
