#!/usr/bin/env python3
"""
update_ml_prices_right.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Atualiza preços (normal + promocional) e informações do produto
para todos os produtos Mercado Livre do banco.

FONTES (em ordem de confiança):
  1. ML API Oficial  — title, disponível, estoque, frete, preço "de"
  2. Catálogo ML     — seller mais barato (real_price, permalink)
  3. DOM via Playwright — preço exibido na página (regex, sem screenshot,
                          sem info-scrap/OCR)

O preço final é decidido pela função _decide_prices(), que combina as
três fontes sem depender de imagem/OCR.

USO:
    python3 scripts/update_ml_prices_right.py               # todos
    python3 scripts/update_ml_prices_right.py --dry-run     # simula
    python3 scripts/update_ml_prices_right.py --id MLB123   # único
    python3 scripts/update_ml_prices_right.py --no-browser  # só API

MAKE:
    make update-prices-ml-right
    make update-prices-ml-right DRY=1
    make update-prices-ml-right ID=MLB…
    make update-prices-ml-right NO_BROWSER=1
"""

import sys
import re
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models.product import Product
from scripts.price_validator.ml_api import get_item, get_catalog_listings
from scripts.price_validator.price_service import parse_catalog_listings, find_cheapest
from scripts.price_validator.affiliate import generate_affiliate_link

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ─── Formatação / normalização ────────────────────────────────────────────────

def _normalize_price(raw: str) -> float:
    """
    Converte string de preço BR → float.
    Suporta: '1.099,00', '1.099', '1099,00', '1099.00', '1099'
    """
    s = raw.strip().replace(' ', '').replace('\xa0', '')
    if not s:
        return 0.0
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    elif re.match(r'^\d{1,3}\.\d{3}$', s):
        # 1.099 → separador de milhar BR (3 dígitos após ponto)
        s = s.replace('.', '')
    elif s.count('.') > 1:
        s = s.replace('.', '', s.count('.') - 1)
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


def _parse_prices_from_text(text: str) -> list[float]:
    """
    Extrai preços BRL de texto DOM limpo (sem artefatos OCR).
    Retorna lista de floats ordenada, filtrada para [50, 100000].
    """
    prices: list[float] = []

    # Padrão 0 — número puro de meta tag (já foi extraído antes — passado como texto)
    # apenas normaliza se vier como "1299.00" ou "1099,00"

    # Padrão 1 — R$ completo na mesma linha
    # Captura: R$ 1.299,00 | R$1.299 | R$ 1299,00 | R$ 999,90
    for m in re.finditer(
        r'R\$\s{0,3}([\d]{1,3}(?:[.\s]?\d{3})*(?:[,\.]\d{1,2})?)',
        text, re.IGNORECASE
    ):
        v = _normalize_price(m.group(1))
        if v:
            prices.append(v)

    # Padrão 2 — preço riscado / original explícito
    # Captura: "De R$ 1.299" | "era R$ 999" | "antes R$ 1.099,00"
    for m in re.finditer(
        r'\b(?:de|era|antes|por)\s+R\$\s{0,3}([\d]{1,3}(?:[.\s]?\d{3})*(?:[,\.]\d{1,2})?)',
        text, re.IGNORECASE
    ):
        v = _normalize_price(m.group(1))
        if v:
            prices.append(v)

    # Padrão 3 — número isolado no formato milhar BR (1.099 ou 1.099,90)
    # OCR às vezes lê "R$" como "RS", "R8", etc.; texto DOM pode omitir símbolo
    for m in re.finditer(
        r'(?<![\d,\.])(\d{1,3}\.\d{3}(?:,\d{2})?)(?![\d,\.])',
        text
    ):
        v = _normalize_price(m.group(1))
        if v >= 100:
            prices.append(v)

    prices = [p for p in prices if 50.0 <= p <= 100_000.0]
    return sorted(set(prices))


def _fmt(price: float) -> str:
    """float → 'R$ 1.234,56'"""
    s = f"{price:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_price_str(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace('R$', '').replace('\xa0', '').strip()
    return _normalize_price(s)


# ─── Extração DOM via Playwright ──────────────────────────────────────────────

def _extract_price_from_page(url: str) -> dict:
    """
    Abre a página do produto ML no Playwright headless e extrai preços
    sem tirar screenshot e sem enviar imagem ao info-scrap.

    Estratégia em 3 camadas (da mais para menos específica):
      Camada 1 — meta tags og:price:amount / product:price:amount
      Camada 2 — CSS selectors DOM do ML (.andes-money-amount__fraction)
      Camada 3 — fallback: page.inner_text('body') + regex

    Retorna:
        price        (float) — preço principal (menor / promo)
        old_price    (float) — preço riscado / original
        discount_pct (int)   — badge de desconto na página
        free_shipping (bool)
        source       (str)   — "meta_tag" | "dom_selector" | "page_text" | "none"
    """
    result = {
        'price': 0.0,
        'old_price': 0.0,
        'discount_pct': 0,
        'free_shipping': False,
        'source': 'none',
    }

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("   ⚠️  playwright não instalado — etapa DOM ignorada")
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1440, 'height': 900},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until='networkidle', timeout=30_000)
                page.wait_for_timeout(2_000)
            except PWTimeout:
                # Página carregou mas JS ainda rodando — tenta mesmo assim
                pass

            # ── Camada 1 — meta tags ──────────────────────────────────────
            for prop in ('og:price:amount', 'product:price:amount'):
                el = page.query_selector(f'meta[property="{prop}"]')
                if el:
                    raw = el.get_attribute('content') or ''
                    v = _normalize_price(raw)
                    if v >= 50:
                        result['price'] = v
                        result['source'] = 'meta_tag'
                        print(f"   🏷️  meta[{prop}] → R$ {v:.2f}")
                        break

            # ── Camada 2 — CSS selectors do ML ───────────────────────────
            def _money_from_selectors(fraction_sel: str, cents_sel: str) -> float:
                frac_el = page.query_selector(fraction_sel)
                if not frac_el:
                    return 0.0
                frac = (frac_el.inner_text() or '').strip()
                cents_el = page.query_selector(cents_sel)
                cents = (cents_el.inner_text() or '00').strip() if cents_el else '00'
                cents = re.sub(r'\D', '', cents)[:2] or '00'
                return _normalize_price(f"{frac},{cents}")

            # Seletor do preço principal (com desconto / preço atual)
            dom_price = _money_from_selectors(
                '.ui-pdp-price__main-price .andes-money-amount__fraction',
                '.ui-pdp-price__main-price .andes-money-amount__cents',
            )
            # Seletor alternativo (listagem de catálogo)
            if not dom_price:
                dom_price = _money_from_selectors(
                    '.andes-money-amount--cents-superscript .andes-money-amount__fraction',
                    '.andes-money-amount--cents-superscript .andes-money-amount__cents',
                )

            # Preço riscado (original)
            dom_old = _money_from_selectors(
                '.ui-pdp-price__original-value .andes-money-amount__fraction',
                '.ui-pdp-price__original-value .andes-money-amount__cents',
            )

            if dom_price >= 50:
                result['price'] = dom_price
                result['source'] = 'dom_selector'
                print(f"   🎯 DOM selector → preço: R$ {dom_price:.2f}")
            if dom_old >= 50 and dom_old > dom_price:
                result['old_price'] = dom_old
                print(f"   🎯 DOM selector → original: R$ {dom_old:.2f}")

            # ── Camada 3 — fallback inner_text + regex ────────────────────
            if result['price'] == 0.0:
                body_text = page.inner_text('body') or ''
                found = _parse_prices_from_text(body_text)
                if found:
                    result['price'] = found[0]
                    result['source'] = 'page_text'
                    print(f"   📄 page_text regex → preço: R$ {found[0]:.2f}")
                    if len(found) >= 2:
                        result['old_price'] = found[-1]
                        print(f"   📄 page_text regex → original: R$ {found[-1]:.2f}")

            # ── Desconto badge ─────────────────────────────────────────────
            disc_match = re.search(
                r'(\d{1,2})\s*%\s*(?:de\s+)?(?:OFF|DESCONTO|off|desconto)',
                page.inner_text('body') if result['source'] == 'none' else '',
                re.IGNORECASE,
            )
            if disc_match:
                result['discount_pct'] = int(disc_match.group(1))

            # Desconto badge via selector
            badge_el = page.query_selector('.ui-pdp-price__discounts .ui-pdp-media__badge')
            if not badge_el:
                badge_el = page.query_selector('[class*="price__discount"]')
            if badge_el:
                badge_text = badge_el.inner_text() or ''
                bm = re.search(r'(\d{1,2})\s*%', badge_text)
                if bm:
                    result['discount_pct'] = int(bm.group(1))
                    print(f"   🎉 badge desconto: {result['discount_pct']}% OFF")

            # ── Frete grátis ───────────────────────────────────────────────
            free_ship_el = page.query_selector('[class*="free-shipping"], [class*="frete-gratis"]')
            if not free_ship_el:
                # texto fallback
                page_snippet = (page.inner_text('.ui-pdp-container__col--right') or '')[:500]
                if re.search(r'frete\s+gr[aá]ti', page_snippet, re.IGNORECASE):
                    result['free_shipping'] = True
            else:
                result['free_shipping'] = True

            if result['free_shipping']:
                print(f"   🚚 frete grátis detectado")

            browser.close()

    except Exception as e:
        print(f"   ⚠️  Playwright erro: {e}")

    return result


# ─── API ML ───────────────────────────────────────────────────────────────────

def _fetch_api_info(external_id: str) -> dict:
    """
    Combina /items/{id} + catálogo de sellers para obter dados canônicos.

    Retorna:
        title              (str)
        api_price          (float)  — preço do próprio item
        original_price     (float)  — preço "de" (antes do desconto) da API
        available_quantity (int | None)
        sold_quantity      (int | None)
        free_shipping      (bool)
        cheapest_price     (float)  — preço do vendedor mais barato do catálogo
        cheapest_permalink (str)
        cheapest_free_shipping (bool)
        catalog_id         (str)
    """
    info: dict = {
        'title': '',
        'api_price': 0.0,
        'original_price': 0.0,
        'available_quantity': None,
        'sold_quantity': None,
        'free_shipping': False,
        'cheapest_price': 0.0,
        'cheapest_permalink': '',
        'cheapest_free_shipping': False,
        'catalog_id': external_id,
    }

    # Dados do item individual
    item_data = get_item(external_id)
    if item_data:
        info['title']              = item_data.get('title', '') or ''
        info['api_price']          = float(item_data.get('price', 0) or 0)
        info['original_price']     = float(item_data.get('original_price', 0) or 0)
        info['available_quantity'] = item_data.get('available_quantity')
        info['sold_quantity']      = item_data.get('sold_quantity')
        info['free_shipping']      = bool((item_data.get('shipping') or {}).get('free_shipping', False))
        catalog_id = item_data.get('catalog_product_id') or external_id
        info['catalog_id'] = catalog_id
    else:
        catalog_id = external_id

    # Catálogo de sellers → vendedor mais barato
    raw_listings = get_catalog_listings(catalog_id)
    listings = parse_catalog_listings(raw_listings)
    if listings:
        cheapest = find_cheapest(listings)
        if cheapest:
            info['cheapest_price']         = cheapest.real_price
            info['cheapest_free_shipping'] = cheapest.free_shipping
            # permalink sob demanda se vazio
            permalink = cheapest.permalink
            if not permalink:
                item_d = get_item(cheapest.item_id)
                if item_d:
                    permalink = item_d.get('permalink', '') or ''
            if not permalink:
                permalink = f"https://www.mercadolivre.com.br/p/{catalog_id}"
            info['cheapest_permalink'] = permalink

    return info


# ─── Decisão de preços ────────────────────────────────────────────────────────

def _decide_prices(api: dict, dom: dict, current_price: float) -> dict:
    """
    Combina dados da API + DOM e decide preços finais.

    Lógica:
    • price (preço final) = menor entre (cheapest_price da API, dom_price),
      priorizando o mais confiável (dom_selector ou meta_tag > cheapest API).
    • old_price = dom.old_price se > price; senão api.original_price; senão current_price.
    • desconto = calculado quando old_price > price.
    • free_shipping = API ou DOM.

    Retorna: {price, old_price, desconto, free_shipping, title, source}
    """
    api_cheapest = api.get('cheapest_price', 0.0)
    dom_price    = dom.get('price', 0.0)
    dom_old      = dom.get('old_price', 0.0)
    dom_source   = dom.get('source', 'none')
    api_original = api.get('original_price', 0.0)

    # Escolhe preço principal
    candidates = []
    if api_cheapest >= 50:
        candidates.append(('api_cheapest', api_cheapest))
    if dom_price >= 50 and dom_source in ('meta_tag', 'dom_selector', 'page_text'):
        candidates.append((f'dom_{dom_source}', dom_price))

    if not candidates:
        final_price  = current_price
        price_source = 'unchanged'
    elif len(candidates) == 1:
        price_source, final_price = candidates[0]
    else:
        # Ambos disponíveis → usa DOM se a diferença for plausível (< 30% menor que API cheapest)
        dom_val = next(v for s, v in candidates if s.startswith('dom_'))
        api_val = next(v for s, v in candidates if s == 'api_cheapest')
        if dom_val >= api_val * 0.70:
            # DOM confirma um preço próximo do catálogo → confiável; usa o menor
            final_price  = min(dom_val, api_val)
            price_source = 'dom_confirmed' if dom_val < api_val else 'api_cheapest'
        else:
            # Grande discrepância → DOM pode ter pego parcela; confia na API
            final_price  = api_val
            price_source = 'api_cheapest_safe'

    # Escolhe old_price (preço "de")
    if dom_old >= 50 and dom_old > final_price:
        old_price = dom_old
    elif api_original >= 50 and api_original > final_price:
        old_price = api_original
    elif current_price > 0 and current_price > final_price:
        old_price = current_price
    else:
        old_price = final_price  # sem desconto detectável

    desconto = round((old_price - final_price) / old_price * 100) if old_price > final_price else 0
    free_ship = api.get('free_shipping', False) or dom.get('free_shipping', False) or (
        api.get('cheapest_free_shipping', False)
    )

    return {
        'price':        final_price,
        'old_price':    old_price,
        'desconto':     desconto,
        'free_shipping': free_ship,
        'title':        api.get('title', ''),
        'source':       price_source,
    }


# ─── Atualização do banco ─────────────────────────────────────────────────────

def _update_product(product: Product, final: dict, api: dict, session, dry_run: bool) -> dict:
    """
    Aplica os dados finais no produto do banco (ou simula se dry_run=True).

    Campos atualizados:
        price, old_price, link (afiliado do mais barato), title,
        disponivel, desconto, updated_at
    """
    report = {
        'external_id':   product.external_id,
        'title':         (product.title or '')[:55],
        'current_price': _parse_price_str(product.price),
        'new_price':     final['price'],
        'new_old_price': final['old_price'],
        'desconto':      final['desconto'],
        'source':        final['source'],
        'status':        'dry_run' if dry_run else 'updated',
    }

    if dry_run:
        return report

    # Preço
    product.price     = _fmt(final['price'])
    product.old_price = _fmt(final['old_price'])

    # Link (afiliado do seller mais barato)
    permalink = api.get('cheapest_permalink', '')
    if permalink:
        affiliate = generate_affiliate_link(permalink)
        product.link = affiliate or permalink

    # Título (só atualiza se API devolveu um título não-vazio)
    new_title = final.get('title', '').strip()
    if new_title:
        product.title = new_title
        # Aliases de compatibilidade
        product.nome = new_title

    # Disponibilidade
    aq = api.get('available_quantity')
    if aq is not None:
        product.disponivel = aq > 0

    # Desconto
    product.desconto = float(final['desconto'])

    product.updated_at = datetime.utcnow()
    session.commit()

    return report


# ─── Processamento principal ──────────────────────────────────────────────────

def _check_ml_token() -> bool:
    try:
        from services.ml_auth import ml_auth
        token = ml_auth.get_valid_access_token()
        if token:
            print(f"   🔑 Token OAuth: ✅ válido")
            return True
        print("\n❌ TOKEN OAUTH ML AUSENTE OU EXPIRADO")
        print("   Execute:  make serve-cloudflare  → autorize → rode novamente")
        return False
    except Exception as e:
        print(f"\n⚠️  Não foi possível verificar token: {e}")
        return False


def process_product(product: Product, session, dry_run: bool, use_browser: bool) -> dict:
    """Processa um produto: API + (opcional) DOM + decisão + atualização."""

    report = {
        'external_id': product.external_id,
        'title':       (product.title or '')[:55],
        'status':      'error',
        'error':       None,
    }

    if not product.external_id:
        report['error'] = 'external_id vazio'
        return report

    current_price = _parse_price_str(product.price)

    try:
        # ── Etapa A: API ──────────────────────────────────────────────────
        print(f"   🌐 API ML…")
        api_info = _fetch_api_info(product.external_id)

        if api_info['api_price'] == 0 and api_info['cheapest_price'] == 0:
            report['status'] = 'no_data'
            print(f"   ⚠️  API sem dados de preço")
            return report

        if api_info['api_price']:
            print(f"   💰 API item price : R$ {api_info['api_price']:.2f}")
        if api_info['cheapest_price']:
            ship = "🚚 grátis" if api_info['cheapest_free_shipping'] else "frete pago"
            print(f"   🏆 Cheapest seller: R$ {api_info['cheapest_price']:.2f} ({ship})")
        if api_info.get('title'):
            print(f"   📦 Título API     : {api_info['title'][:60]}")

        # ── Etapa B: DOM via Playwright ───────────────────────────────────
        dom_result: dict = {'price': 0.0, 'old_price': 0.0, 'source': 'none', 'free_shipping': False}
        if use_browser:
            page_url = api_info['cheapest_permalink'] or f"https://www.mercadolivre.com.br/p/{product.external_id}"
            print(f"   🖥️  Playwright DOM…")
            dom_result = _extract_price_from_page(page_url)

        # ── Etapa C: Decisão de preços ────────────────────────────────────
        final = _decide_prices(api_info, dom_result, current_price)
        print(f"   ✅ Preço final    : R$ {final['price']:.2f}  (fonte: {final['source']})")
        if final['old_price'] > final['price']:
            print(f"   🔥 Preço original : R$ {final['old_price']:.2f} ({final['desconto']}% OFF)")

        # ── Etapa D: Atualiza banco ───────────────────────────────────────
        result = _update_product(product, final, api_info, session, dry_run)
        result['status'] = 'dry_run' if dry_run else 'updated'
        return result

    except Exception as e:
        report['error'] = str(e)
        logger.exception(f"Erro ao processar {product.external_id}")
        return report


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="update-prices-ml-right: atualiza preços+promo+info via API+DOM (sem screenshot)"
    )
    parser.add_argument('--dry-run',    action='store_true',
                        help='Simula sem salvar no banco')
    parser.add_argument('--id',         dest='external_id', default=None,
                        help='Processa apenas o produto com este external_id (ex: MLB123)')
    parser.add_argument('--no-browser', action='store_true',
                        help='Ignora etapa Playwright DOM (usa apenas a ML API)')
    args = parser.parse_args()

    dry         = args.dry_run
    use_browser = not args.no_browser
    mode_parts  = []
    if dry:        mode_parts.append("DRY-RUN (sem alterações)")
    if not use_browser: mode_parts.append("NO-BROWSER (só API)")
    mode = " | ".join(mode_parts) if mode_parts else "LIVE (atualiza banco)"

    print()
    print("━" * 70)
    print("🔄 UPDATE PRICES ML RIGHT — API + DOM texto + regex (sem OCR/screenshot)")
    print(f"   Modo: {mode}")
    print("━" * 70)

    if not _check_ml_token():
        sys.exit(1)

    session = SessionLocal()
    try:
        q = session.query(Product).filter(
            Product.platform == 'mercadolivre',
            Product.disponivel == True,
            Product.external_id.isnot(None),
            Product.external_id != '',
        )
        if args.external_id:
            q = q.filter(Product.external_id == args.external_id)

        products = q.order_by(Product.created_at).all()
    except Exception:
        session.close()
        raise

    if not products:
        print("⚠️  Nenhum produto ML ativo encontrado.")
        session.close()
        sys.exit(0)

    total   = len(products)
    updated = errors = no_data = 0

    print(f"\n📦 {total} produto(s) encontrado(s)\n")

    for i, product in enumerate(products, 1):
        print(f"[{i:3d}/{total}] {(product.title or '')[:55]:<55} {product.external_id}")

        report = process_product(product, session, dry_run=dry, use_browser=use_browser)

        if report['status'] in ('updated', 'dry_run'):
            updated += 1
        elif report['status'] == 'no_data':
            no_data += 1
            print(f"        ⚠️  Sem dados")
        else:
            errors += 1
            print(f"        ❌ {report.get('error', 'erro desconhecido')}")

        print()

        # Pequena pausa entre produtos para não sobrecarregar a API
        if i < total:
            time.sleep(0.5)

    session.close()

    print("━" * 70)
    print("📊 RESUMO")
    print("━" * 70)
    print(f"  Total          : {total}")
    print(f"  {'Simulados' if dry else 'Atualizados':<15}: {updated}")
    print(f"  Sem dados      : {no_data}")
    print(f"  Erros          : {errors}")
    print()


if __name__ == '__main__':
    main()
