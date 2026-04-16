#!/usr/bin/env python3
"""
verify_prices.py — Verificador de preços com pipeline de 2 estratégias OCR.

Para cada produto com preço inválido (0, nulo, vazio) tenta recuperar o preço real:

  Estratégia 1 — OCR via Screenshot
      Tira screenshot da página → recorta ROI de preço → envia para info-scrap /extract
      (Tesseract OCR remoto) → classifica preços via regex.

  Estratégia 2 — Tesseract direto (pytesseract)
      Mesmo screenshot → pytesseract local como fallback se info-scrap falhar.
      Requer pytesseract + tesseract-ocr instalados no container.

Regras de classificação de preços:
  • Preços parcelados (NxM) são ignorados — aparecem menores mas são parcelas
  • Menor preço real = price (promocional)
  • Maior preço real = old_price (original/riscado)

Ação final:
  • Preço encontrado > 0  → salva no banco (price + old_price) e atualiza JSON de staging
  • Ambas as estratégias falharam → remove produto do banco e sinaliza o JSON de staging

Uso dentro do container:
    python3 scripts/verify_prices.py              # verifica apenas preço=0
    python3 scripts/verify_prices.py --all        # verifica todos os produtos
    python3 scripts/verify_prices.py --dry-run    # apenas reporta, não altera nada
    python3 scripts/verify_prices.py --id <uuid>  # verifica produto específico
"""

import os
import sys
import json
import re
import tempfile
import time
import argparse
from pathlib import Path
from datetime import datetime

# ── Compatibilidade com o ambiente Flask ────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

import requests as _req
from database import engine
from sqlalchemy.orm import Session
from models.product import Product

INFO_SCRAP_BASE = os.environ.get('INFO_SCRAP_URL', 'http://info-scrap:8000')

# ROIs de preço por plataforma (viewport 1440×900)
# Cada plataforma tem seu layout, mas usamos o ROI do ML para ML e um
# ROI "genérico" (metade inferior central) para as demais.
ROI_ML      = (596, 206, 1303, 820)
ROI_GENERIC = (300, 150, 1140, 750)   # cobre a área central da maioria dos layouts

# ── Utilitários de preço (mesma lógica do prepare_ml_best.py) ───────────────

def _normalize_price(raw: str) -> float:
    s = raw.strip().replace(' ', '')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    elif re.match(r'^\d{1,3}\.\d{3}$', s):
        s = s.replace('.', '')
    elif s.count('.') > 1:
        s = s.replace('.', '', s.count('.') - 1)
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


def _extract_all_price_candidates(text: str) -> list:
    """Extrai todos os candidatos a preço do texto OCR (sem filtrar parcelamentos)."""
    candidates = []
    # Padrão 1: R$ com formato BR completo — "R$ 1.099,00" ou "R$ 289,90"
    for m in re.finditer(r'R\$\s*([\d]{1,3}(?:[.\s]\d{3})*(?:[,\.]\d{1,2})?)', text, re.IGNORECASE):
        candidates.append(_normalize_price(m.group(1)))
    # Padrão 2: formato split ML — "R$\n1.099\n00"
    for m in re.finditer(r'R\$[\s\n]+([\d]{1,3}(?:[.\s]\d{3})*)[\s\n]+(\d{2})\b', text, re.IGNORECASE):
        integer_part = m.group(1).replace('.', '').replace(' ', '')
        candidates.append(float(f"{integer_part}.{m.group(2)}"))
    # Padrão 3: preço riscado — "De R$ 1.499,00" / "Era R$ ..."
    for m in re.finditer(r'(?:de|era|antes|por)\s+R\$\s*([\d]{1,3}(?:[.\s]\d{3})*(?:[,\.]\d{1,2})?)', text, re.IGNORECASE):
        candidates.append(_normalize_price(m.group(1)))
    # Padrão 4: milhar BR sem R$ — "1.099,00" isolado (OCR perdeu o símbolo)
    for m in re.finditer(r'(?<![\d,\.])(\d{1,3}\.\d{3}(?:,\d{2})?)(?![\d,\.])', text):
        v = _normalize_price(m.group(1))
        if v >= 50:
            candidates.append(v)
    return [p for p in candidates if 1.0 <= p <= 200_000.0]


def _extract_installment_values(text: str) -> set:
    """
    Detecta preços parcelados (ex: "12x 91,58" ou "em 10x R$ 79,90").
    Retorna conjunto com o valor da parcela E o total acumulado (ambos a descartar).
    Regra: parcelamento N×M — parcela menor que o main price, N entre 2 e 72.
    """
    discard = set()
    pat = re.compile(
        r'\b(\d{1,2})\s*[xX\xd7]\s*(?:de\s+)?(?:R\$\s*)?' 
        r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)',
        re.IGNORECASE
    )
    for m in pat.finditer(text):
        parcelas = int(m.group(1))
        valor = _normalize_price(m.group(2))
        if 2 <= parcelas <= 72 and 0 < valor < 2000:
            # Descarta apenas o valor da parcela — o total (valor*N) não é descartado
            # porque o preço principal pode coincidir com o total parcelado
            discard.add(round(valor, 2))
    return discard


def classify_prices(ocr_text: str) -> dict:
    """
    Classifica preços extraídos do OCR conforme as regras do negócio:
      - Preços parcelados (NxM) são descartados (aparecem menores mas são parcelas)
      - Menor preço real = price  (promocional/atual)
      - Maior preço real = old_price  (original/riscado)

    Retorna: {'price': float, 'old_price': float}
    """
    all_candidates = _extract_all_price_candidates(ocr_text)
    installments = _extract_installment_values(ocr_text)

    def is_installment(v: float) -> bool:
        return any(abs(v - iv) <= 0.05 for iv in installments)

    real_prices = sorted(set(p for p in all_candidates if not is_installment(p)))

    if not real_prices:
        return {'price': 0.0, 'old_price': 0.0}
    if len(real_prices) == 1:
        return {'price': real_prices[0], 'old_price': 0.0}
    # Múltiplos preços: menor = promo, maior = original/riscado
    return {'price': real_prices[0], 'old_price': real_prices[-1]}


def _price_is_zero(price_str: str) -> bool:
    """Retorna True se o preço armazenado é inválido (0, vazio ou nulo)."""
    if not price_str:
        return True
    # Extrai dígitos — se todos são zeros, o preço é zero
    digits = re.sub(r'[^0-9]', '', price_str)
    return not digits or int(digits) == 0


def _format_price(value: float) -> str:
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ── Screenshots ──────────────────────────────────────────────────────────────

def _take_screenshot(url: str) -> str | None:
    """Captura screenshot da URL via Playwright. Retorna caminho do arquivo PNG."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("   ⚠️  Playwright não disponível")
        return None

    print(f"   📸 Screenshot: {url[:80]}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1440, 'height': 900},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            page.screenshot(path=tmp.name, full_page=False)
            tmp.close()
            browser.close()
            print(f"   ✅ Screenshot salvo: {tmp.name}")
            return tmp.name
    except Exception as e:
        print(f"   ⚠️  Screenshot falhou: {e}")
        return None


def _crop_roi(screenshot_path: str, roi: tuple) -> str:
    """Recorta o ROI do screenshot. Retorna caminho do crop."""
    try:
        from PIL import Image
        x1, y1, x2, y2 = roi
        with Image.open(screenshot_path) as img:
            w, h = img.size
            crop = img.crop((x1, y1, min(x2, w), min(y2, h)))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            crop.save(tmp.name)
            tmp.close()
            return tmp.name
    except Exception as e:
        print(f"   ⚠️  Crop falhou: {e} — usando screenshot completo")
        return screenshot_path


# ── Estratégia 1: OCR via info-scrap /extract ────────────────────────────────

def strategy_ocr_infoscrap(url: str, platform: str) -> dict:
    """
    Screenshot → recorta ROI → envia PNG para info-scrap /extract → parseia preços.
    """
    print("   🔍 Estratégia 1: OCR via info-scrap /extract")
    roi = ROI_ML if platform == 'mercadolivre' else ROI_GENERIC

    screenshot = _take_screenshot(url)
    if not screenshot:
        return {'price': 0.0, 'old_price': 0.0, 'source': 'failed'}

    crop_path = _crop_roi(screenshot, roi)
    is_tmp_crop = (crop_path != screenshot)

    try:
        with open(crop_path, 'rb') as f:
            resp = _req.post(f"{INFO_SCRAP_BASE}/extract", files={'file': f}, timeout=30)
        resp.raise_for_status()
        ocr_text = resp.json().get('text', '')
        print(f"   📄 OCR texto (primeiros 200 chars): {ocr_text[:200].strip()!r}")
    except Exception as e:
        print(f"   ⚠️  info-scrap /extract falhou: {e}")
        ocr_text = ''
    finally:
        try:
            if is_tmp_crop:
                os.remove(crop_path)
            os.remove(screenshot)
        except Exception:
            pass

    result = classify_prices(ocr_text)
    if not result['price']:
        print("   ⚠️  Nenhum preço encontrado no OCR")
        return {'price': 0.0, 'old_price': 0.0, 'source': 'ocr_no_match'}

    print(f"   ✅ OCR encontrou: preço={result['price']} old_price={result['old_price']}")
    return {**result, 'source': 'ocr_infoscrap'}


# ── Estratégia 2: Tesseract direto (pytesseract) ─────────────────────────────

def strategy_pytesseract(url: str, platform: str) -> dict:
    """
    Screenshot → pytesseract local → parseia preços.
    Requer: pytesseract + tesseract-ocr no sistema.
    """
    print("   🔍 Estratégia 2: Tesseract direto (pytesseract)")
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("   ⚠️  pytesseract/Pillow não disponível — pulando estratégia 2")
        return {'price': 0.0, 'old_price': 0.0, 'source': 'unavailable'}

    roi = ROI_ML if platform == 'mercadolivre' else ROI_GENERIC
    screenshot = _take_screenshot(url)
    if not screenshot:
        return {'price': 0.0, 'old_price': 0.0, 'source': 'failed'}

    crop_path = _crop_roi(screenshot, roi)
    is_tmp_crop = (crop_path != screenshot)

    try:
        img = Image.open(crop_path)
        # Pré-processamento: escala 2× melhora acurácia do Tesseract
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        ocr_text = pytesseract.image_to_string(
            img,
            lang='por',   # Português BR para melhor leitura de R$/vírgulas
            config='--psm 6 --oem 3'  # PSM 6 = bloco uniforme de texto
        )
        print(f"   📄 Tesseract (primeiros 200 chars): {ocr_text[:200].strip()!r}")
    except Exception as e:
        print(f"   ⚠️  pytesseract falhou: {e}")
        ocr_text = ''
    finally:
        try:
            if is_tmp_crop:
                os.remove(crop_path)
            os.remove(screenshot)
        except Exception:
            pass

    result = classify_prices(ocr_text)
    if not result['price']:
        print("   ⚠️  Tesseract não encontrou preços válidos")
        return {'price': 0.0, 'old_price': 0.0, 'source': 'tesseract_no_match'}

    print(f"   ✅ Tesseract encontrou: preço={result['price']} old_price={result['old_price']}")
    return {**result, 'source': 'tesseract'}


# ── Pipeline principal ────────────────────────────────────────────────────────

def verify_product_price(product, dry_run: bool = False) -> str:
    """
    Tenta corrigir o preço de um produto usando as 3 estratégias em ordem.

    Retorna: 'updated' | 'removed' | 'skipped' | 'error'
    """
    title_short = product.title[:60] if product.title else '(sem título)'
    print(f"\n{'─'*60}")
    print(f"🔎 [{product.platform}] {title_short}")
    print(f"   Preço atual: {product.price!r} | ID: {product.id}")
    print(f"   Link: {product.link[:80] if product.link else 'N/A'}")

    if not product.link:
        print("   ⚠️  Produto sem link — removendo")
        if not dry_run:
            _remove_product(product)
        return 'removed'

    result = {'price': 0.0, 'old_price': 0.0, 'source': 'none'}

    # Estratégia 1 — OCR via info-scrap
    result = strategy_ocr_infoscrap(product.link, product.platform or '')
    if result['price'] > 0:
        print(f"   ✅ Estratégia 1 bem-sucedida: R$ {result['price']:.2f}")
    else:
        # Estratégia 2 — Pytesseract direto
        result = strategy_pytesseract(product.link, product.platform or '')
        if result['price'] > 0:
            print(f"   ✅ Estratégia 2 bem-sucedida: R$ {result['price']:.2f}")

    if result['price'] > 0:
        new_price     = _format_price(result['price'])
        new_old_price = _format_price(result['old_price']) if result['old_price'] > 0 else product.old_price
        print(f"   💾 {'[DRY-RUN] ' if dry_run else ''}Atualizando: {new_price} (old: {new_old_price}) via [{result['source']}]")
        if not dry_run:
            _update_product_price(product, new_price, new_old_price)
        return 'updated'
    else:
        print(f"   ❌ Ambas as estratégias falharam — {'[DRY-RUN] ' if dry_run else ''}removendo produto")
        if not dry_run:
            _remove_product(product)
        return 'removed'


def _update_product_price(product, new_price: str, new_old_price: str):
    """Atualiza preço no banco de dados."""
    with Session(engine) as session:
        p = session.get(Product, product.id)
        if p:
            p.price     = new_price
            p.old_price = new_old_price
            p.updated_at = datetime.utcnow()
            session.commit()
            print(f"   ✅ Banco atualizado")


def _remove_product(product):
    """Remove produto do banco de dados e sinaliza o JSON de staging."""
    with Session(engine) as session:
        p = session.get(Product, product.id)
        if p:
            session.delete(p)
            session.commit()
            print(f"   🗑️  Removido do banco: {product.id}")

    # Tenta marcar o JSON de staging como problemático (renomeia .json → .zero_price)
    _mark_staging_json(product)


def _mark_staging_json(product):
    """Localiza o JSON de staging do produto e renomeia para .zero_price."""
    staging_root = Path('/app/staging')
    if not staging_root.exists():
        return

    # Procura JSON onde link ou external_id bate com o produto
    for json_path in staging_root.rglob('*.json'):
        try:
            data = json.loads(json_path.read_text())
            match = (
                (product.external_id and data.get('external_id') == product.external_id) or
                (product.link and data.get('link') == product.link)
            )
            if match:
                dest = json_path.with_suffix('.zero_price')
                json_path.rename(dest)
                print(f"   📁 Staging marcado: {dest.name}")
                return
        except Exception:
            continue


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Verificador de preços de produtos')
    parser.add_argument('--all',     action='store_true', help='Verifica todos os produtos, não só preço=0')
    parser.add_argument('--dry-run', action='store_true', help='Apenas reporta, não altera nada')
    parser.add_argument('--id',      metavar='UUID',      help='Verifica somente o produto com este ID')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("🔍 VERIFY PRICES — Pipeline de Verificação de Preços")
    if args.dry_run:
        print("   [DRY-RUN] Nenhuma alteração será feita no banco")
    print("="*60)

    with Session(engine) as session:
        q = session.query(Product)

        if args.id:
            q = q.filter(Product.id == args.id)
        elif not args.all:
            # Filtra produtos onde o preço não contém dígito 1-9 (zero/vazio)
            q = q.filter(~Product.price.op('~')('[1-9]'))

        products = q.all()

    print(f"\n📦 Produtos a verificar: {len(products)}")
    if not products:
        print("✅ Nenhum produto com preço inválido encontrado!")
        return

    stats = {'updated': 0, 'removed': 0, 'skipped': 0, 'error': 0}

    for product in products:
        try:
            status = verify_product_price(product, dry_run=args.dry_run)
            stats[status] = stats.get(status, 0) + 1
        except Exception as e:
            print(f"   ❌ Erro inesperado ao processar {product.id}: {e}")
            stats['error'] += 1
        # Pausa entre produtos para não sobrecarregar o info-scrap
        time.sleep(2)

    print("\n" + "="*60)
    print("📊 RESUMO")
    print(f"   ✅ Atualizados:  {stats['updated']}")
    print(f"   🗑️  Removidos:   {stats['removed']}")
    print(f"   ⚠️  Com erro:    {stats['error']}")
    if args.dry_run:
        print("   [DRY-RUN] Nenhuma alteração foi feita")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
