#!/usr/bin/env python3
"""
update_ml_prices.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Percorre TODOS os produtos Mercado Livre no banco, usa o
price_validator para encontrar o vendedor mais barato no
catálogo ML e atualiza o produto se encontrar preço menor.

FLUXO por produto:
  1. Pega external_id (ex: MLB55308793) direto do banco
     → NÃO usa o campo `link` (pode ser meli.la/... ou qualquer coisa)
  2. GET /items/{id} → pega catalog_product_id
     Se 404 → usa o próprio id como catalog_product_id
  3. GET /sites/MLB/search?catalog_product_id=... → listagem de vendedores
  4. find_cheapest() → Listing mais barato
  5. generate_affiliate_link() → link de afiliado do mais barato
  6. Atualiza: price, old_price, link

Uso:
    python3 scripts/update_ml_prices.py              # todos os produtos
    python3 scripts/update_ml_prices.py --dry-run    # simula sem salvar
    python3 scripts/update_ml_prices.py --id MLB123  # produto específico
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models.product import Product
from scripts.price_validator.ml_api import get_item, get_catalog_listings
from scripts.price_validator.price_service import parse_catalog_listings, find_cheapest
from scripts.price_validator.affiliate import generate_affiliate_link


def _check_ml_token() -> bool:
    """Verifica se existe um token OAuth válido. Retorna False e imprime orientação se ausente."""
    try:
        from services.ml_auth import ml_auth
        token = ml_auth.get_valid_access_token()
        if token:
            print(f"   🔑 Token OAuth: ✅ válido")
            return True
        print("\n❌ TOKEN OAUTH ML AUSENTE OU EXPIRADO")
        print("   A ML exige autenticação para buscar preços de catálogo.")
        print()
        print("   Solução:")
        print("   1. Execute:  make serve-cloudflare")
        print("   2. Atualize o Redirect URI no DevCenter ML")
        print("   3. Clique no link de autorização exibido")
        print("   4. Execute novamente:  make update-ml-prices")
        print()
        return False
    except Exception as e:
        print(f"\n⚠️  Não foi possível verificar token: {e}")
        return False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_price(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace('R$', '').replace('\xa0', '').strip()
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _fmt(price: float) -> str:
    """Float → 'R$ 1.234,56'"""
    s = f"{price:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _find_cheapest_for_id(external_id: str):
    """
    Dado um external_id ML (item ou catálogo), retorna (Listing mais barato,
    catalog_id usado, total de listagens).

    Estratégia:
      1. GET /items/{id}  → tenta pegar catalog_product_id
      2. Se não encontrar, usa o próprio external_id como catalog_product_id
      3. GET /sites/MLB/search?catalog_product_id=... → listagem de vendedores
      4. find_cheapest()
    """
    catalog_id = None

    # Tenta como item individual para pegar o catalog_product_id canônico
    item_data = get_item(external_id)
    if item_data:
        catalog_id = item_data.get("catalog_product_id")

    # Fallback: usa o próprio ID como catalog_product_id
    if not catalog_id:
        catalog_id = external_id

    # Busca todos os vendedores do catálogo
    raw_listings = get_catalog_listings(catalog_id)
    all_listings  = parse_catalog_listings(raw_listings)

    if not all_listings:
        return None, catalog_id, 0

    cheapest = find_cheapest(all_listings)
    return cheapest, catalog_id, len(all_listings)


def _check_and_update(product: Product, session, dry_run: bool) -> dict:
    """Valida um produto e atualiza se encontrou vendedor mais barato."""
    current_price = _parse_price(product.price)
    report = {
        "external_id":   product.external_id,
        "title":         product.title[:55],
        "current_price": current_price,
        "status":        "unchanged",
        "error":         None,
    }

    if not product.external_id:
        report["status"] = "error"
        report["error"]  = "external_id vazio"
        return report

    try:
        cheapest, catalog_id, total = _find_cheapest_for_id(product.external_id)
    except Exception as e:
        report["status"] = "error"
        report["error"]  = str(e)
        return report

    if cheapest is None:
        report["status"]     = "no_data"
        report["catalog_id"] = catalog_id
        return report

    # Resolve permalink (endpoint /products/{id}/items não retorna permalink)
    permalink_reliable = False
    if not cheapest.permalink:
        item_data = get_item(cheapest.item_id)
        if item_data:
            cheapest.permalink = item_data.get("permalink", "") or ""
            if cheapest.permalink:
                permalink_reliable = True
            else:
                cheapest.permalink = f"https://www.mercadolivre.com.br/p/{cheapest.item_id}"
                permalink_reliable = True
    else:
        permalink_reliable = True

    if not cheapest.permalink:
        # Fallback: usa external_id (catalog page do produto original).
        # NUNCA usa catalog_id do listing — pode não ter página no site ML.
        cheapest.permalink = f"https://www.mercadolivre.com.br/p/{product.external_id}"
        permalink_reliable = False

    report["cheapest_price"]  = cheapest.real_price
    report["cheapest_link"]   = cheapest.permalink
    report["total_listings"]  = total

    # Gera link de afiliado para o mais barato
    affiliate = generate_affiliate_link(cheapest.permalink) if cheapest.permalink else ""
    report["affiliate_link"] = affiliate

    # Guarda de integridade: verifica se o item mais barato é o mesmo produto.
    # Se o titulo do listing for completamente diferente, recusa a atualização —
    # evita que produtos de categoria errada no catalogo ML contaminem o banco.
    cheapest_title = getattr(cheapest, 'title', '') or ''
    if cheapest_title:
        def _title_words(t):
            import re
            return set(w for w in re.sub(r'[^a-z0-9 ]', ' ', t.lower()).split() if len(w) > 3)
        our_words     = _title_words(product.title or '')
        cheaper_words = _title_words(cheapest_title)
        common = our_words & cheaper_words
        if our_words and len(common) / len(our_words) < 0.2:
            report["status"] = "title_mismatch"
            report["error"]  = f"título divergente: nosso={product.title[:40]!r} vs ML={cheapest_title[:40]!r}"
            print(f"   ⚠️  Título divergente — link NÃO atualizado")
            print(f"      nosso: {product.title[:60]}")
            print(f"      ML:    {cheapest_title[:60]}")
            return report


    if current_price > 0 and cheapest.real_price >= current_price * 0.99:
        report["status"] = "cheapest"
        return report

    # Encontrou mais barato → atualiza
    report["status"] = "updated"
    if not dry_run:
        product.old_price  = product.price
        product.price      = _fmt(cheapest.real_price)
        # Só atualiza link se permalink é confiável (real da API).
        # Fallbacks construídos (/p/MLB...) podem não ter página no ML.
        if permalink_reliable:
            product.link = affiliate or cheapest.permalink
        product.updated_at = datetime.utcnow()
        session.commit()

    return report


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Atualiza preços ML → vendedor mais barato")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar no banco")
    parser.add_argument("--id", dest="external_id", default=None,
                        help="Processa apenas produto com esse external_id")
    args = parser.parse_args()

    dry  = args.dry_run
    mode = "🔍 DRY-RUN (sem alterações)" if dry else "✏️  LIVE (atualizará o banco)"

    print()
    print("━" * 66)
    print("🔄 UPDATE ML PRICES — Buscador de vendedor mais barato")
    print(f"   Modo: {mode}")
    print("━" * 66)

    if not _check_ml_token():
        sys.exit(1)

    session = SessionLocal()
    try:
        q = session.query(Product).filter(
            Product.platform == "mercadolivre",
            Product.external_id.isnot(None),
            Product.external_id != "",
            Product.disponivel == True,
        )
        if args.external_id:
            q = q.filter(Product.external_id == args.external_id)
        products = q.all()

        if not products:
            print("⚠️  Nenhum produto ML disponível encontrado no banco.")
            return

        print(f"\n📦 {len(products)} produto(s) para verificar\n")

        stats   = {"updated": 0, "cheapest": 0, "no_data": 0, "error": 0}
        updated = []

        for i, product in enumerate(products, 1):
            print(f"[{i:>3}/{len(products)}] {product.title[:50]:<50}  {product.external_id}")
            report = _check_and_update(product, session, dry_run=dry)

            status = report["status"]
            stats[status] = stats.get(status, 0) + 1

            if status == "updated":
                diff     = report["current_price"] - report["cheapest_price"]
                diff_pct = round(diff / report["current_price"] * 100) if report["current_price"] else 0
                tag      = "[DRY] " if dry else "✅ "
                print(f"       {tag}MAIS BARATO ENCONTRADO! ({report['total_listings']} vendedores)")
                print(f"          De  : {_fmt(report['current_price'])}")
                print(f"          Para: {_fmt(report['cheapest_price'])}  (-{diff_pct}%)")
                print(f"          Link: {report['affiliate_link'] or report['cheapest_link']}")
                updated.append(report)

            elif status == "cheapest":
                n = report.get("total_listings", "?")
                print(f"       ✅ Já é o mais barato entre {n} vendedores  ({_fmt(report['current_price'])})")

            elif status == "no_data":
                print(f"       ⚠️  Sem anúncios no catálogo {report.get('catalog_id', '?')}")

            elif status == "error":
                print(f"       ❌ Erro: {report['error']}")

        # ── Resumo ────────────────────────────────────────────────────
        print()
        print("━" * 66)
        print("📊 RESUMO")
        print("━" * 66)
        print(f"  Total verificados           : {len(products)}")
        print(f"  🔥 Atualizados (mais barato): {stats['updated']}" + (" (simulado)" if dry else ""))
        print(f"  ✅ Já eram o mais barato    : {stats['cheapest']}")
        print(f"  ⚠️  Sem dados de catálogo    : {stats['no_data']}")
        print(f"  ❌ Erros                     : {stats['error']}")

        if updated:
            print()
            print("🔥 Produtos atualizados:")
            for r in updated:
                diff_pct = round((r["current_price"] - r["cheapest_price"]) / r["current_price"] * 100)
                print(f"  • {r['title'][:48]:<48}  {_fmt(r['current_price'])} → {_fmt(r['cheapest_price'])}  (-{diff_pct}%)")

        if dry:
            print()
            print("ℹ️  Nada salvo (--dry-run). Rode sem a flag para aplicar.")
        print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
