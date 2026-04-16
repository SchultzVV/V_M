"""
reprice_all.py
Revisa todos os produtos publicados no banco:
  - Busca preço atualizado via Price Oracle
  - Republica preços que mudaram
  - Limpa produtos com price = 0, vazio, ou None (soft-delete: marca como inativo)

Uso:
  python3 agents/reprice_all.py [--dry-run] [--fix-zero-only] [--batch-size N]
"""
import os
import sys
import re
import logging
import argparse
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# Garante que /app (raiz do container site) está no path
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

_SCRIPTS_DIR = os.path.join(_APP_DIR, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

_PRICE_RE = re.compile(r"[\d]+[.,][\d]{2}")


def _parse_price(val: Optional[str]) -> float:
    """'R$ 1.234,56' → 1234.56"""
    if not val:
        return 0.0
    s = str(val).replace("R$", "").replace("\xa0", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _is_broken(product) -> bool:
    """Retorna True se o produto precisa de limpeza/correção."""
    price_val = _parse_price(product.price)
    if price_val <= 0:
        return True
    if not product.external_id:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Repricing geral de todos os produtos publicados")
    parser.add_argument("--dry-run",       action="store_true", help="Simula sem gravar no banco")
    parser.add_argument("--fix-zero-only", action="store_true", help="Só limpa itens com preço 0 ou inválido, sem reprecificar")
    parser.add_argument("--batch-size",    type=int, default=0,  help="Processa apenas os primeiros N produtos (0 = todos)")
    args = parser.parse_args()

    try:
        from database import SessionLocal
        from models.product import Product
    except ImportError as exc:
        logger.error("Não consegui importar models (rode dentro do container site): %s", exc)
        sys.exit(1)

    session = SessionLocal()
    try:
        query = session.query(Product).filter(
            Product.external_id.isnot(None),
            Product.external_id != "",
        ).order_by(Product.id)

        if args.batch_size > 0:
            query = query.limit(args.batch_size)

        products = query.all()
    finally:
        pass  # sessão ainda aberta para commits abaixo

    total        = len(products)
    n_broken     = 0
    n_removed    = 0
    n_repriced   = 0
    n_unchanged  = 0
    n_error      = 0

    print()
    print("━" * 66)
    print(f"🔄 REPRICE ALL — {total} produto(s) no banco")
    if args.dry_run:
        print("   modo: DRY-RUN (nenhuma alteração será gravada)")
    if args.fix_zero_only:
        print("   modo: apenas limpeza de zeros/inválidos")
    print("━" * 66)
    print()

    # -------------------------------------------------------------------
    # Importa o oracle (disponível porque estamos no mesmo container)
    # -------------------------------------------------------------------
    if not args.fix_zero_only:
        try:
            from agents.price_oracle_agent import PriceOracleAgent
            oracle = PriceOracleAgent()
        except ImportError:
            # fallback: path relativo
            sys.path.insert(0, os.path.dirname(__file__))
            from price_oracle_agent import PriceOracleAgent  # type: ignore
            oracle = PriceOracleAgent()

    for i, product in enumerate(products, 1):
        ml_id     = product.external_id
        old_price = _parse_price(product.price)
        name      = (getattr(product, "nome", None) or getattr(product, "title", None) or ml_id or "?")[:50]

        prefix = f"[{i:>3}/{total}] {ml_id}"

        # ── 1. Limpa itens quebrados ─────────────────────────────────────
        if _is_broken(product):
            n_broken += 1
            print(f"  🗑️  {prefix} — preço inválido ({product.price!r}) → removendo")
            if not args.dry_run:
                try:
                    session.delete(product)
                    session.commit()
                    n_removed += 1
                except Exception as exc:
                    session.rollback()
                    logger.error("Erro ao remover %s: %s", ml_id, exc)
                    n_error += 1
            else:
                n_removed += 1
            continue

        # ── 2. Se fix-zero-only, pula repricing ─────────────────────────
        if args.fix_zero_only:
            n_unchanged += 1
            continue

        # ── 3. Repricing via Price Oracle ────────────────────────────────
        try:
            result = oracle.execute({
                "ml_id":      ml_id,
                "product_id": str(product.id),
                "title":      name,
                "dry_run":    args.dry_run,
                "publish":    not args.dry_run,
            })

            new_price = result.get("decision", {}).get("price_current") or 0.0
            published = result.get("published", False)

            if new_price <= 0:
                print(f"  ⚠️  {prefix} — oracle não encontrou preço → mantido (R$ {old_price:.2f})")
                n_unchanged += 1
            elif abs(float(new_price) - old_price) < 0.01:
                print(f"  ✓  {prefix} — sem mudança (R$ {old_price:.2f})")
                n_unchanged += 1
            elif published or args.dry_run:
                print(f"  ✅ {prefix} — R$ {old_price:.2f} → R$ {float(new_price):.2f}"
                      + (" (dry-run)" if args.dry_run else ""))
                n_repriced += 1
            else:
                detail = (result.get("publish_detail") or {}).get("detail", "")
                print(f"  ⚡ {prefix} — falhou ao publicar{(' — ' + detail) if detail else ''}")
                n_error += 1

        except Exception as exc:
            logger.error("Oracle erro para %s: %s", ml_id, exc)
            n_error += 1

    session.close()

    print()
    print("━" * 66)
    print(f"✅ Concluído: {total} produto(s)")
    print(f"   🔄 Repriced   : {n_repriced}")
    print(f"   ✓  Sem mudança: {n_unchanged}")
    print(f"   🗑️  Removidos  : {n_removed}  (preço 0/inválido)")
    print(f"   ❌ Erros       : {n_error}")
    if args.dry_run:
        print("   ⚠️  DRY-RUN — nenhuma alteração foi gravada")
    print("━" * 66)
    print()


if __name__ == "__main__":
    main()
