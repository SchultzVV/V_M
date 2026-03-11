#!/usr/bin/env python3
"""
Preparação COMPLETA de produtos do Mercado Livre.
Combina API Oficial + Screenshot + OCR para preço promocional.

ESTRATÉGIA:
1. Resolve link de afiliado → ID do produto
2. Busca dados completos via API Oficial (OAuth) ou fallback scraping
3. IMAGENS: vêm EXCLUSIVAMENTE da API oficial (alta qualidade, sem duplicatas)
   - Se a API retornou imagens, NÃO usa imagens de nenhuma outra fonte
4. Tira screenshot da página do produto
5. OCR na screenshot para ler o PREÇO PROMOCIONAL que aparece na tela
   (preço dinâmico: cupom relâmpago, promoção de hora, etc.)
   - Se OCR encontrar preço menor que o da API → usa como preço final
   - Preço da API vai para old_price (preço original)
6. Combina dados API + preço OCR
7. Gera JSON de staging

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
    get_sale_price_from_api,
    download_images_hq
)
from auto_prepare_ml import (
    follow_affiliate_link,
    extract_ml_product_id,
    scrape_mercadolivre_product,
)
from category_selector import (
    detect_product_category,
    ask_user_category,
    ask_user_subcategory,
)


# ROI da área de preço na página do Mercado Livre (viewport 1440x900)
# Cobre a coluna direita: título, preço principal, preço riscado, desconto
ML_PRICE_ROI = (596, 206, 1303, 820)   # (x1, y1, x2, y2)


def take_screenshot_ml(url: str) -> str:
    """
    Tira screenshot da página do Mercado Livre no viewport 1440×900.
    Viewport fixo garante que o ROI de preço esteja sempre na mesma posição.
    """
    print(f"\n📸 Capturando screenshot da página (viewport 1440×900)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            print(f"   🌐 Carregando página...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            # Aguarda JS dinâmico (preços que mudam com cupom/promoção relâmpago)
            page.wait_for_timeout(3000)

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            screenshot_path = temp_file.name
            temp_file.close()

            page.screenshot(path=screenshot_path, full_page=False)
            print(f"   ✅ Screenshot capturado: {screenshot_path}")
            browser.close()
            return screenshot_path

        except Exception as e:
            print(f"   ⚠️  Erro no screenshot: {e}")
            try:
                browser.close()
            except Exception:
                pass
            return None


def _crop_roi(screenshot_path: str, roi: tuple) -> str:
    """
    Recorta a região de interesse (ROI) do screenshot usando Pillow.
    Salva o crop em arquivo temporário e retorna o caminho.
    roi = (x1, y1, x2, y2)
    """
    from PIL import Image
    x1, y1, x2, y2 = roi
    try:
        with Image.open(screenshot_path) as img:
            w, h = img.size
            # Ajusta se o ROI ultrapassar as dimensões reais da imagem
            x2 = min(x2, w)
            y2 = min(y2, h)
            crop = img.crop((x1, y1, x2, y2))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            crop.save(tmp.name)
            tmp.close()
            print(f"   ✂️  ROI ({x1},{y1})→({x2},{y2}) — "
                  f"original {w}×{h}px, crop {x2-x1}×{y2-y1}px")
            return tmp.name
    except Exception as e:
        print(f"   ⚠️  Crop ROI falhou: {e} — usando screenshot completo")
        return screenshot_path


def _parse_ml_prices(ocr_text: str) -> list[float]:
    """
    Extrai preços do texto OCR com os padrões do Mercado Livre.

    O OCR do ML pode gerar vários formatos conforme o layout:
      • R$ 1.099,00       (completo numa linha)
      • R$ 1.099          (sem centavos)
      • R$\n1.099\n00     (Real, inteiro e centavos em linhas separadas — layout ML grande)
      • 1.099             (só número, perto de "R$" na linha anterior)
      • 1099,00 / 1099.00 (sem separador de milhar)
    """
    prices = []

    # ── Padrão 1: R$ completo numa linha ────────────────────────────────────
    # Captura: R$ 1.299,00 | R$1.299 | R$ 1299,00 | R$ 999,90
    for m in re.finditer(
        r'R\$\s*([\d]{1,3}(?:[.\s]?\d{3})*(?:[,\.]\d{1,2})?)',
        ocr_text, re.IGNORECASE
    ):
        prices.append(_normalize_price(m.group(1)))

    # ── Padrão 2: ML split format — "R$" seguido de número na próxima linha ─
    # Ex: "R$\n1.099\n00" ou "R$\n1.099,00"
    for m in re.finditer(
        r'R\$[\s\n]+([\d]{1,3}(?:[.\s]?\d{3})*)[\s\n]+(\d{2})\b',
        ocr_text, re.IGNORECASE
    ):
        integer_part = m.group(1).replace('.', '').replace(' ', '')
        cents_part   = m.group(2)
        prices.append(float(f"{integer_part}.{cents_part}"))

    # ── Padrão 3: preço riscado — "De R$ X" ou "era R$ X" ──────────────────
    for m in re.finditer(
        r'(?:de|era|antes|por|De|Era)\s+R\$\s*([\d]{1,3}(?:[.\s]?\d{3})*(?:[,\.]\d{1,2})?)',
        ocr_text, re.IGNORECASE
    ):
        prices.append(_normalize_price(m.group(1)))

    # ── Padrão 4: número standalone no formato milhar BR ───────────────────
    # OCR frequentemente lê "R$" como "ESSO", "R8", "RS", etc.
    # Neste padrão buscamos qualquer número no formato milhar BR (1.099 ou
    # 1.099,90) que apareça no texto, mesmo sem "R$" na frente.
    # Roda SEMPRE (não apenas quando os padrões anteriores falham) para
    # garantir que o preço real não seja perdido por false-positives leves.
    for m in re.finditer(
        r'(?<![\d,\.])'
        r'(\d{1,3}\.\d{3}(?:,\d{2})?)'
        r'(?![\d,\.])',
        ocr_text
    ):
        v = _normalize_price(m.group(1))
        if v >= 100:          # produto válido (não pega decimais soltos)
            prices.append(v)

    # Filtra zeros, duplicatas e valores irreais (< R$ 50 ou > R$ 100.000).
    # Mínimo R$ 50: elimina leituras espúrias de parcelas, fretes, etc.
    prices = [p for p in prices if 50.0 <= p <= 100_000.0]
    return sorted(set(prices))


def _normalize_price(raw: str) -> float:
    """
    Converte string de preço BR para float.

    Casos tratados:
      '1.099,00'  → 1099.00  (milhar + decimal BR)
      '1.099'     → 1099.00  (milhar BR sem centavos — caso mais comum no OCR do ML)
      '1099,00'   → 1099.00  (sem milhar, decimal com vírgula)
      '1099.00'   → 1099.00  (decimal com ponto — formato EN)
      '1.099.00'  → 1099.00  (raro, dois pontos)
    """
    s = raw.strip().replace(' ', '')

    if ',' in s and '.' in s:
        # 1.099,00 → separador de milhar (ponto) + decimal (vírgula) — BR completo
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        # 1099,00 → só vírgula decimal
        s = s.replace(',', '.')
    elif re.match(r'^\d{1,3}\.\d{3}$', s):
        # 1.099 → ponto seguido de EXATAMENTE 3 dígitos = separador de milhar BR
        # NUNCA é decimal (decimal teria 1 ou 2 dígitos após o ponto)
        s = s.replace('.', '')
    elif s.count('.') > 1:
        # 1.099.00 (raro)
        s = s.replace('.', '', s.count('.') - 1)
    # else: 1099 ou 1099.00 — converte direto

    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


def extract_promo_price_from_screenshot(screenshot_path: str) -> dict:
    """
    Recorta o ROI de preço do screenshot, envia ao serviço info-scrap (OCR)
    e extrai o preço promocional via regex otimizado para o layout do ML.

    ROI fixo (viewport 1440×900):
        x1=596, y1=206 → x2=1303, y2=820
    Cobre a coluna de preço/desconto/título da página do produto.

    Retorna:
        price       (float) – menor preço encontrado (promo) ou 0
        old_price   (float) – maior preço encontrado (original) ou 0
        discount_pct (int)  – % de desconto exibido na página ou 0
        raw_prices  (list)  – todos os valores extraídos
        source      (str)   – "ocr" | "none"
    """
    print(f"\n🔍 OCR na área de preço (ROI {ML_PRICE_ROI})...")

    result = {
        'price': 0.0,
        'old_price': 0.0,
        'discount_pct': 0,
        'raw_prices': [],
        'source': 'none'
    }

    if not screenshot_path or not os.path.exists(screenshot_path):
        print("   ⚠️  Screenshot não disponível para OCR")
        return result

    # ── Recortar ROI antes de enviar — salva cópia de debug ────────────────
    crop_path = _crop_roi(screenshot_path, ML_PRICE_ROI)
    crop_is_temp = (crop_path != screenshot_path)
    # Salva debug permanente para inspeção visual
    try:
        import shutil
        from datetime import datetime as _dt
        debug_dir = Path('/app/fotos')
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_name = f"roi_crop_{_dt.now().strftime('%Y%m%d_%H%M%S')}.png"
        shutil.copy2(crop_path, debug_dir / debug_name)
        print(f"   💾 Crop salvo: /app/fotos/{debug_name}")
    except Exception:
        pass

    ocr_service_url = "http://info-scrap:8000/extract"
    try:
        with open(crop_path, 'rb') as f:
            files = {'file': (os.path.basename(crop_path), f, 'image/png')}
            response = requests.post(ocr_service_url, files=files, timeout=60)

        if response.status_code != 200:
            print(f"   ⚠️  OCR retornou status {response.status_code}")
            return result

        ocr = response.json()
        ocr_text = ocr.get('text', '')
        lines = ocr_text.strip().splitlines()
        line_count = len(lines)
        print(f"   📄 Texto OCR: {line_count} linhas")
        if ocr_text.strip():
            print("   📝 OCR completo:")
            for ln in lines:
                if ln.strip():
                    print(f"      {ln}")

        # ── Extrair preços com regex otimizado ──────────────────────────────
        prices = _parse_ml_prices(ocr_text)
        result['raw_prices'] = prices
        print(f"   💰 Preços extraídos: {prices}")

        # ── Desconto percentual exibido na badge ──────────────────────────────
        disc_match = re.search(
            r'(\d{1,2})\s*%\s*(?:de\s+)?(?:OFF|DESCONTO|desconto|off)',
            ocr_text, re.IGNORECASE
        )
        if disc_match:
            result['discount_pct'] = int(disc_match.group(1))
            print(f"   🎉 Desconto badge: {result['discount_pct']}% OFF")

        # ── Estoque disponível ───────────────────────────────────────────
        if re.search(r'estoque\s+dispon', ocr_text, re.IGNORECASE):
            result['stock_available'] = True
            # Tenta capturar quantidade: "+50 disponiv" ou "50 disponiv"
            qty_m = re.search(r'\+?(\d+)\s+dispon', ocr_text, re.IGNORECASE)
            if qty_m:
                result['available_quantity'] = int(qty_m.group(1))
                print(f"   📦 Estoque: {result['available_quantity']}+ unidades disponíveis")
            else:
                result['available_quantity'] = 1
                print(f"   📦 Estoque: disponível")
        elif re.search(r'sem\s+estoque|esgotado|indispon', ocr_text, re.IGNORECASE):
            result['stock_available'] = False
            result['available_quantity'] = 0
            print(f"   📦 Estoque: esgotado")

        # ── Frete grátis ───────────────────────────────────────────────
        if re.search(r'frete\s+gr[aá]ti', ocr_text, re.IGNORECASE):
            result['free_shipping'] = True
            print(f"   🚚 Frete grátis detectado")

        # ── Identificar preço promo vs original ─────────────────────────────
        # No ML: preço PRINCIPAL (maior destaque visual) é o preço com desconto
        # O preço RISCADO (menor, acima) é o original
        # → OCR captura riscado antes do principal → menor índice = original, maior = promo
        # MAS: o preço riscado é numericamente MAIOR => menor valor = promo
        if len(prices) >= 2:
            result['price']     = prices[0]   # menor = promocional
            result['old_price'] = prices[-1]  # maior = original (riscado)
            result['source']    = 'ocr'
            disc_pct = round((prices[-1] - prices[0]) / prices[-1] * 100)
            print(f"   ✨ Promo: R$ {prices[0]:.2f}  ←  original: R$ {prices[-1]:.2f}  ({disc_pct}% OFF)")
        elif len(prices) == 1:
            result['price']  = prices[0]
            result['source'] = 'ocr'
            print(f"   ✨ Preço OCR: R$ {prices[0]:.2f}")
        else:
            print(f"   ℹ️  Nenhum preço identificado no ROI")

        return result

    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  Serviço info-scrap não disponível (OCR ignorado)")
        return result
    except Exception as e:
        print(f"   ⚠️  Erro no OCR: {e}")
        return result
    finally:
        if crop_is_temp and os.path.exists(crop_path):
            try:
                os.remove(crop_path)
            except Exception:
                pass


def merge_api_with_ocr_price(api_data: dict, ocr_result: dict) -> dict:
    """
    Combina dados da API com preço do OCR.

    REGRAS:
    - Imagens: vêm SEMPRE da API (já foram baixadas antes, não altera)
    - Preço: se OCR encontrou preço e é MENOR que o da API → é o preço promocional
             Nesse caso: price = ocr_price, old_price = api_price
    - Se OCR não encontrou nada útil → mantém preços da API
    - Frete grátis, Mercado Pontos, cupons: complementados pelo OCR se ausentes na API
    """
    merged = api_data.copy()

    if ocr_result.get('source') not in ('ocr', 'affiliate_ocr') or not ocr_result.get('price', 0):
        print("   ℹ️  OCR não encontrou preço — mantendo dados da API")
        return merged

    def to_float(val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            s = val.replace('R$', '').replace('\xa0', '').strip()
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')
            try:
                return float(s)
            except ValueError:
                return 0.0
        return 0.0

    api_price = to_float(merged.get('price', 0))
    raw_prices: list = ocr_result.get('raw_prices', [])
    ocr_price = ocr_result['price']
    ocr_old   = ocr_result.get('old_price', 0)

    # ── Descarta parcelas: se o "preço OCR" < API/4, é provável que seja
    # uma parcela (ex: "10x R$ 109,90") e não o preço real.
    # Procura nos raw_prices um candidato melhor (mais próximo do API).
    if api_price > 0 and ocr_price > 0 and ocr_price < api_price / 4:
        # Candidatos com valor >= api_price / 2 (descontos reais raramente > 50%)
        candidates = [p for p in raw_prices if p >= api_price / 2]
        if candidates:
            # Pega o valor mais próximo do api_price
            best = min(candidates, key=lambda p: abs(p - api_price))
            print(f"   ⚠️  Descartando parcela R$ {ocr_price:.2f} — "
                  f"usando candidato R$ {best:.2f} dos raw_prices")
            ocr_price = best
            # Recalcula: se tinha old_price e era o melhor, mantém
            others = [p for p in raw_prices if p != best and p > best]
            ocr_old = others[0] if others else ocr_old

    print(f"\n   📊 Comparando preços:")
    print(f"      API:  R$ {api_price:.2f}")
    print(f"      OCR:  R$ {ocr_price:.2f}" + (f"  (era R$ {ocr_old:.2f})" if ocr_old else ""))
    print(f"      raw_prices: {raw_prices}")

    # ── CASO 1: API sem preço (catálogo) → OCR é a única fonte ──────────
    if api_price == 0 and ocr_price > 0:
        merged['price']         = f"R$ {ocr_price:.2f}"
        merged['old_price']     = f"R$ {ocr_old:.2f}" if ocr_old > ocr_price else f"R$ {ocr_price:.2f}"
        merged['_price_source'] = 'ocr'
        print(f"   📸 API sem preço — usando preço do OCR: R$ {ocr_price:.2f}")

    # ── CASO 2: OCR menor que API (promoção) ────────────────────────
    elif ocr_price > 0 and ocr_price < api_price * 0.98:
        merged['price']         = f"R$ {ocr_price:.2f}"
        merged['old_price']     = f"R$ {api_price:.2f}"
        merged['_price_source'] = 'ocr_promo'
        discount_pct = round((api_price - ocr_price) / api_price * 100)
        print(f"   🔥 Promoção detectada via OCR: {discount_pct}% OFF!")
        print(f"      De: R$ {api_price:.2f} → Por: R$ {ocr_price:.2f}")

    # ── CASO 3: OCR viu dois preços e o old_price é maior ────────────
    elif ocr_price > 0 and ocr_old > 0 and ocr_old > ocr_price:
        current_old = to_float(merged.get('old_price', 0))
        if ocr_old > current_old:
            merged['old_price'] = f"R$ {ocr_old:.2f}"
            print(f"   📝 old_price atualizado pelo OCR: R$ {ocr_old:.2f}")

    else:
        print(f"   ✅ Preço da API mantido (OCR não detectou promoção mais baixa)")

    # ── Frete grátis do OCR ────────────────────────────────────────────
    if ocr_result.get('free_shipping') and not merged.get('free_shipping'):
        merged['free_shipping'] = True
        print(f"   🚚 Frete grátis confirmado pelo OCR")

    # ── Estoque do OCR (só sobrescreve se API não retornou ou retornou 0) ───
    ocr_aq = ocr_result.get('available_quantity')
    if ocr_aq is not None:
        current_aq = merged.get('available_quantity')
        if not current_aq:  # API retornou None ou 0
            merged['available_quantity'] = ocr_aq
            print(f"   📦 Estoque atualizado pelo OCR: {ocr_aq}")

    return merged


def take_and_ocr_affiliate_full(affiliate_url: str) -> dict:
    """
    ETAPA 5B — Segundo scraping mandatório para confirmação de preço.

    Tira screenshot COMPLETO (sem recorte de ROI) do link curto de afiliado,
    envia ao OCR e extrai preço atual + preço antigo de forma autoritativa.

    - Screenshot salvo em /app/fotos/affiliate_full_YYYYMMDD_HHMMSS.png
    - Toda a saída OCR é impressa para debug
    - Resultado é mandatório: sobrescreve preços anteriores se encontrar valores
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

    # OCR no screenshot completo (sem ROI)
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

        # Parser de preços BR (igual ao _parse_ml_prices)
        prices = _parse_ml_prices(raw_text)
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
        print("   (API Oficial + Screenshot + OCR Preço Promo)")
        print("=" * 70)
        print(f"\n🔗 URL: {url}\n")

        # ─────────────────────────────────────────────────────────
        # ETAPA 1: Resolver link de afiliado
        # ─────────────────────────────────────────────────────────
        print("━" * 70)
        print("ETAPA 1: Resolvendo link de afiliado")
        print("━" * 70)
        product_url = follow_affiliate_link(url)
        if not product_url:
            print("❌ Falha ao resolver link")
            sys.exit(1)

        product_id = extract_ml_product_id(product_url)
        print(f"   🆔 Product ID: {product_id}")

        # ─────────────────────────────────────────────────────────
        # ETAPA 2: API Oficial (dados + preços + imagens HQ)
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 2: API Oficial do Mercado Livre")
        print("━" * 70)

        token = load_ml_token()
        product_data = None
        api_images = []         # imagens vindas da API — fonte autoritativa
        images_from_api = False  # flag: se True, NÃO busca imagens de outra fonte

        if product_id:
            api_data = get_product_from_api(product_id, token)

            if api_data:
                print(f"   ✅ Dados obtidos via API!")

                # ── Preços ────────────────────────────────────────
                api_price = float(api_data.get('price', 0) or 0)
                api_old   = float(api_data.get('original_price', 0) or 0)

                # Tentar endpoint /sale_price (mais preciso para promoções)
                # Para catalog IDs, usa o item mais barato encontrado em /products/{id}/items
                sale_id = api_data.get('_cheapest_item_id') or product_id
                if token and sale_id:
                    sale = get_sale_price_from_api(sale_id, token)
                    if sale:
                        api_price = sale.get('price', api_price)
                        api_old   = sale.get('oldPrice', api_old) or api_old

                # ── Imagens da API (URLs de alta qualidade -O.) ───
                for pic in api_data.get('pictures', []):
                    img_url = (
                        pic.get('secure_url') or pic.get('url', '')
                    ).replace('-I.', '-O.')  # força resolução máxima
                    if img_url:
                        api_images.append(img_url)

                images_from_api = len(api_images) > 0
                print(f"   🖼️  Imagens da API: {len(api_images)}")

                product_data = {
                    'title':              api_data.get('title') or api_data.get('name', ''),
                    'price':              f"R$ {api_price:.2f}",
                    'old_price':          f"R$ {api_old:.2f}" if api_old else f"R$ {api_price:.2f}",
                    'images':             api_images,
                    'external_id':        api_data.get('id', product_id),
                    'condition':          api_data.get('condition', 'new'),
                    'available_quantity': api_data.get('available_quantity', 0),
                    'sold_quantity':      api_data.get('sold_quantity', 0),
                    'free_shipping':      (api_data.get('shipping', {}) or {}).get('free_shipping', False),
                    '_image_source':      'api',
                }
                if api_data.get('video_id'):
                    product_data['videos'] = [f"https://www.youtube.com/watch?v={api_data['video_id']}"]

                print(f"   📦 Título : {product_data['title'][:65]}...")
                print(f"   💰 Preço  : {product_data['price']}")
                if api_old and api_old > api_price:
                    disc = round((api_old - api_price) / api_old * 100)
                    print(f"   🔥 De     : {product_data['old_price']} ({disc}% OFF)")

        # ─────────────────────────────────────────────────────────
        # ETAPA 3: Fallback Scraping (sem OAuth ou API falhou)
        # ─────────────────────────────────────────────────────────
        if not product_data or not product_data.get('title'):
            print("\n" + "━" * 70)
            print("ETAPA 3: Scraping HTML (fallback — API não disponível)")
            print("━" * 70)
            product_data = scrape_mercadolivre_product(product_url)
            if not product_data or not product_data.get('title'):
                print("❌ Falha ao obter dados via API/Scraping")
                sys.exit(1)
            # ⚠️  Scraping pode retornar stock=0 mesmo produto disponível
            # Se available_quantity não foi extraído de forma confiável → assumir disponível
            if product_data.get('available_quantity', 0) == 0:
                product_data['available_quantity'] = None  # indefinido → disponivel=True no JSON
                print("   ⚠️  Estoque não obtido via scraping — definido como disponível por padrão")
            # Scraping retorna imagens — serão usadas SOMENTE se API não deu imagens
            images_from_api = False

        # ─────────────────────────────────────────────────────────
        # ETAPA 4: Screenshot para leitura de preço via OCR
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 4: Screenshot da página (OCR de preço promocional)")
        print("━" * 70)
        screenshot_path = take_screenshot_ml(product_url)

        # ─────────────────────────────────────────────────────────
        # ETAPA 5: OCR → preço promocional
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 5: OCR — lendo preço promocional da screenshot")
        print("━" * 70)
        ocr_result = extract_promo_price_from_screenshot(screenshot_path)

        # ─────────────────────────────────────────────────────────
        # ETAPA 5B: Screenshot completo do link de afiliado — preço mandatório
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 5B: OCR mandatório — screenshot completo do link de afiliado")
        print("━" * 70)
        affiliate_ocr = take_and_ocr_affiliate_full(url)
        if affiliate_ocr['source'] == 'affiliate_ocr' and affiliate_ocr['price'] > 0:
            print(f"\n   🔒 Preços do afiliado substituem OCR de ROI (mandatório):")
            ocr_result['price']      = affiliate_ocr['price']
            ocr_result['raw_prices'] = affiliate_ocr['raw_prices']
            ocr_result['source']     = 'affiliate_ocr'
            if affiliate_ocr['old_price'] > affiliate_ocr['price']:
                ocr_result['old_price'] = affiliate_ocr['old_price']
                print(f"      price    : R$ {affiliate_ocr['price']:.2f}")
                print(f"      old_price: R$ {affiliate_ocr['old_price']:.2f}")
            else:
                print(f"      price    : R$ {affiliate_ocr['price']:.2f}")
        else:
            print(f"   ⚠️  OCR do afiliado sem preços — mantendo OCR de ROI")

        # ─────────────────────────────────────────────────────────
        # ETAPA 6: Combinar API + OCR (preço promo)
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 6: Combinando dados API + preço OCR")
        print("━" * 70)
        product_data = merge_api_with_ocr_price(product_data, ocr_result)

        # ─────────────────────────────────────────────────────────
        # ETAPA 7: Download de imagens (SOMENTE da API)
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 7: Download de imagens" + (" — fonte: API Oficial ✅" if images_from_api else " — fonte: Scraping ⚠️"))
        print("━" * 70)

        product_slug = slugify(product_data['title'])
        img_source_urls = product_data.get('images', [])

        if images_from_api:
            print(f"   🖼️  Usando {len(img_source_urls)} imagens da API oficial (alta qualidade)")
            print(f"   🚫 Imagens de scraping/OCR descartadas")
        else:
            print(f"   ⚠️  API sem imagens — usando imagens do scraping ({len(img_source_urls)} URLs)")

        if img_source_urls:
            images_dir, downloaded = download_images_hq(img_source_urls, product_slug)
        else:
            images_dir = f"uploads/{product_slug}"
            downloaded = []
            print("   ⚠️  Nenhuma imagem disponível")

        # ─────────────────────────────────────────────────────────
        # ETAPA 8: Resumo e seleção de categoria
        # ─────────────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("📌 RESUMO DO PRODUTO")
        print("=" * 70)
        price_v = product_data.get('price', 'N/A')
        old_v   = product_data.get('old_price', '')
        print(f"  📝 Título      : {product_data.get('title', 'N/A')}")
        print(f"  💰 Preço final : {price_v}")
        if old_v and old_v != price_v:
            print(f"  🏷️  Preço antigo: {old_v}")
        price_src = product_data.get('_price_source', 'api')
        src_label = {
            'ocr_promo': 'OCR — promoção detectada na tela',
            'ocr':       'OCR — única fonte (API sem preço)',
        }.get(price_src, 'API Oficial')
        print(f"  📡 Fonte preço : {src_label}")
        img_src = product_data.get('_image_source', 'api' if images_from_api else 'scraping')
        print(f"  🖼️  Fonte imagens: {'API Oficial ✅' if img_src == 'api' else 'Scraping ⚠️'}")
        print(f"  🖼️  Imagens DL  : {len(downloaded)}")
        aq = product_data.get('available_quantity')
        if aq is not None:
            status = "✅ Disponível" if aq > 0 else "❌ Sem estoque"
            print(f"  📊 Estoque     : {aq} — {status}")
        sq = product_data.get('sold_quantity')
        if sq:
            print(f"  🛒 Vendidos    : {sq}")
        if product_data.get('free_shipping'):
            print(f"  📦 Frete grátis")
        print("=" * 70)

        suggested_category = detect_product_category(product_data['title'])
        print(f"\n📦 Produto: {product_data['title']}")

        # Permite bypass não-interativo via env vars (usado por reprepare_all_ml.py)
        force_cat  = os.environ.get("FORCE_CATEGORY", "").strip()
        force_sub  = os.environ.get("FORCE_SUBCATEGORY", "").strip()
        if force_cat:
            selected_category    = force_cat.upper()
            selected_subcategory = force_sub
            print(f"  📦 Categoria (auto): {selected_category}" + (f" / {selected_subcategory}" if selected_subcategory else ""))
        else:
            selected_category    = ask_user_category(suggested_category)
            selected_subcategory = ask_user_subcategory(selected_category)

        # ─────────────────────────────────────────────────────────
        # ETAPA 9: Gerar JSON de staging
        # ─────────────────────────────────────────────────────────
        print("\n" + "━" * 70)
        print("ETAPA 9: Gerando JSON de staging")
        print("━" * 70)

        json_file, json_data = generate_staging_json(
            product_data,
            images_dir,
            url,
            selected_category,
            selected_subcategory
        )

        # ─────────────────────────────────────────────────────────
        # RESUMO FINAL
        # ─────────────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("✅ PREPARAÇÃO CONCLUÍDA!")
        print("=" * 70)
        print(f"  📄 Arquivo  : {json_file}")
        print(f"  📦 Título   : {product_data['title'][:65]}")
        print(f"  🏷️  Categoria: {selected_category}" + (f" / {selected_subcategory}" if selected_subcategory else ""))
        print(f"  💰 Preço    : {json_data.get('price', 'N/A')}")
        if json_data.get('oldPrice') and json_data['oldPrice'] != json_data.get('price'):
            print(f"  🔥 De       : {json_data['oldPrice']}")
        print(f"  🖼️  Imagens  : {len(downloaded)} baixadas ({img_src})")
        print(f"\n  📋 Próximo: make stage\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Salvar screenshot para referência e limpar /tmp
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                import shutil
                fotos_dir = Path('/app/fotos')
                fotos_dir.mkdir(parents=True, exist_ok=True)
                ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
                dest = fotos_dir / f'ml_promo_{ts}.png'
                shutil.copy2(screenshot_path, dest)
                os.chmod(dest, 0o644)
                print(f"\n💾 Screenshot salvo: {dest}")
            except Exception as e:
                print(f"⚠️  Não foi possível salvar screenshot: {e}")
            try:
                os.remove(screenshot_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
