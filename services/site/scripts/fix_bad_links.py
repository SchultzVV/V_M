#!/usr/bin/env python3
"""
Detecta e corrige produtos cujo link aponta para um item_id de listing
em vez do catalog_id (external_id) do produto.

Regra: para produtos ML, o link correto é sempre
  /p/{external_id}?matt_tool=...&utm_source=affiliate&utm_medium=link

Uso:
  python3 fix_bad_links.py          # corrige no banco
  python3 fix_bad_links.py --dry    # só reporta, sem salvar
"""
import sys
import re
import argparse

sys.path.insert(0, '/app')
from database import SessionLocal
from models import Product

AFFILIATE_PARAMS = "matt_tool=97040906&utm_source=affiliate&utm_medium=link"

def make_good_link(external_id: str) -> str:
    return f"https://www.mercadolivre.com.br/p/{external_id}?{AFFILIATE_PARAMS}"

def link_id(link: str) -> str | None:
    """Extrai o ID dentro de /p/MLBXXXXX do link."""
    m = re.search(r'/p/(MLB\w+)', link or '')
    return m.group(1) if m else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry', action='store_true', help='Só reporta, não salva')
    args = parser.parse_args()

    s = SessionLocal()

    # Produtos ML com link /p/ cujo ID não bate com o external_id
    prods = s.query(Product).filter(Product.link.like('%/p/MLB%')).all()

    bad = []
    for p in prods:
        lid = link_id(p.link)
        if lid and lid != p.external_id:
            bad.append(p)

    # Produtos ML sem /p/ no link (produto.mercadolivre.com.br/MLB-... formato)
    prods_no_p = s.query(Product).filter(
        Product.external_id.like('MLB%'),
        ~Product.link.like('%/p/%'),
        Product.link.isnot(None),
        Product.link != '',
    ).all()

    print(f"Produtos com link_id ≠ external_id : {len(bad)}")
    print(f"Produtos ML sem /p/ no link         : {len(prods_no_p)}")
    print()

    fixed = 0
    for p in bad:
        old = p.link
        new = make_good_link(p.external_id)
        print(f"  {'[DRY] ' if args.dry else ''}FIX  {p.external_id}")
        print(f"    OLD: {old[:80]}")
        print(f"    NEW: {new[:80]}")
        if not args.dry:
            p.link = new
            fixed += 1

    for p in prods_no_p:
        old = p.link
        new = make_good_link(p.external_id)
        print(f"  {'[DRY] ' if args.dry else ''}FIX  {p.external_id} (sem /p/)")
        print(f"    OLD: {old[:80]}")
        print(f"    NEW: {new[:80]}")
        if not args.dry:
            p.link = new
            fixed += 1

    if not args.dry:
        s.commit()
        print(f"\nCorrigidos: {fixed}")
    else:
        print(f"\n[DRY] Seriam corrigidos: {len(bad) + len(prods_no_p)}")

    s.close()

if __name__ == '__main__':
    main()
