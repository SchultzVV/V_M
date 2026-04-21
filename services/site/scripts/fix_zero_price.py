#!/usr/bin/env python3
"""
fix_zero_price.py
Corrige produtos com price=0 e disponivel=False que foram inseridos
com URL de catálogo inválida (fallback errado no ml_populator_agent).
Busca o preço real via API ML e atualiza o banco.

Uso:
    python3 scripts/fix_zero_price.py           # corrige todos
    python3 scripts/fix_zero_price.py --dry-run  # simula sem salvar
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models.product import Product
from scripts.price_validator.ml_api import get_item, get_catalog_listings
from scripts.price_validator.price_service import parse_catalog_listings, find_cheapest
from scripts.price_validator.affiliate import generate_affiliate_link


def _fmt(price: float) -> str:
    s = f"{price:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fix_product(p: Product, session, dry_run: bool) -> str:
    eid = p.external_id
    if not eid:
        return "skip:no_external_id"

    # Tentativa 1: item direto
    item_data = get_item(eid)
    if item_data:
        price = item_data.get("price")
        if price and float(price) > 0:
            if not dry_run:
                p.price = _fmt(float(price))
                p.disponivel = True
                p.updated_at = datetime.utcnow()
                session.commit()
            return f"ok_direct:{_fmt(float(price))}"

    # Tentativa 2: via catálogo (cheapest seller)
    catalog_id = (item_data or {}).get("catalog_product_id") or eid
    raw = get_catalog_listings(catalog_id)
    listings = parse_catalog_listings(raw)
    cheapest = find_cheapest(listings)

    if cheapest and cheapest.real_price > 0:
        permalink = ""
        if cheapest.item_id:
            id_data = get_item(cheapest.item_id)
            permalink = (id_data.get("permalink") or "") if id_data else ""
        if not permalink and cheapest.item_id:
            permalink = f"https://www.mercadolivre.com.br/p/{cheapest.item_id}"
        aff = generate_affiliate_link(permalink) if permalink else ""
        if not dry_run:
            p.price = _fmt(cheapest.real_price)
            p.disponivel = True
            p.link = aff or permalink or p.link
            p.updated_at = datetime.utcnow()
            session.commit()
        return f"ok_catalog:{_fmt(cheapest.real_price)}"

    return "fail:no_price"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        broken = (
            session.query(Product)
            .filter(
                Product.platform == "mercadolivre",
                Product.price.like("R$ 0%"),
            )
            .all()
        )

        print(f"\n{'DRY-RUN — ' if args.dry_run else ''}Fix zero-price ML products")
        print(f"Encontrados: {len(broken)}\n")

        if not broken:
            print("Nenhum produto com preco=0 encontrado.")
            return

        stats = {"ok_direct": 0, "ok_catalog": 0, "fail": 0, "skip": 0}

        for p in broken:
            print(f"[{p.external_id}] {p.title[:55]}")
            result = _fix_product(p, session, args.dry_run)
            icon = "✅" if result.startswith("ok") else ("⚠️ " if result.startswith("fail") else "–")
            print(f"  {icon} {result}")
            key = result.split(":")[0]
            stats[key] = stats.get(key, 0) + 1

        print(f"\nOK direto : {stats.get('ok_direct', 0)}")
        print(f"OK catálog: {stats.get('ok_catalog', 0)}")
        print(f"Falhou    : {stats.get('fail', 0)}")
        print(f"Pulados   : {stats.get('skip', 0)}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
