#!/usr/bin/env python3
"""
reprepare_all_ml.py
Re-prepara TODOS os produtos ML do banco usando o pipeline completo
(prepare_ml_best.py: API + OCR de preço + download de imagens).

Mantém as mesmas tags e subcategorias já cadastradas — sem perguntas interativas.
Após preparar todos, executa stage_products.py --force para atualizar o banco.

Uso:
    python scripts/reprepare_all_ml.py              # todos os produtos ML ativos
    python scripts/reprepare_all_ml.py --id MLB123  # só um produto específico
    python scripts/reprepare_all_ml.py --dry-run    # apenas lista o que seria feito

Equivalente a: make reprepare-ml
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# ─── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import SessionLocal
from models import Product

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_tag(tags_str: str) -> str:
    """Extrai a tag principal (não-geral) do JSON de tags. Ex: '["geral","E"]' → 'E'"""
    try:
        tags = json.loads(tags_str or "[]")
        for t in tags:
            if t and t.lower() != "geral":
                return t.upper()
    except Exception:
        pass
    return "geral"


def _ml_url(external_id: str) -> str:
    """Constrói URL de catálogo ML a partir do external_id."""
    return f"https://www.mercadolivre.com.br/p/{external_id}"


def _prepare_one(product: Product, dry_run: bool) -> dict:
    """
    Chama prepare_ml_best.py para um único produto com FORCE_CATEGORY/FORCE_SUBCATEGORY.
    Retorna dict com status do resultado.
    """
    tag        = _parse_tag(product.tags)
    subcategory = product.subcategory or ""
    url        = _ml_url(product.external_id)

    report = {
        "external_id": product.external_id,
        "title":       (product.title or "")[:55],
        "tag":         tag,
        "subcategory": subcategory,
        "url":         url,
        "status":      "pending",
        "error":       None,
    }

    if dry_run:
        report["status"] = "dry_run"
        return report

    env = os.environ.copy()
    env["FORCE_CATEGORY"]    = tag
    env["FORCE_SUBCATEGORY"] = subcategory

    script = str(Path(__file__).parent / "prepare_ml_best.py")
    try:
        result = subprocess.run(
            [sys.executable, script, url],
            env=env,
            timeout=300,   # 5 min por produto (screenshot + OCR pode demorar)
        )
        if result.returncode == 0:
            report["status"] = "ok"
        else:
            report["status"] = "error"
            report["error"]  = f"returncode={result.returncode}"
    except subprocess.TimeoutExpired:
        report["status"] = "timeout"
        report["error"]  = "timeout 5min"
    except Exception as e:
        report["status"] = "error"
        report["error"]  = str(e)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Re-prepara produtos ML do banco (mantém tags/subcategoria)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Lista o que seria feito sem executar")
    parser.add_argument("--id", dest="external_id", default=None,
                        help="Processa apenas o produto com este external_id")
    args = parser.parse_args()

    dry  = args.dry_run
    mode = "🔍 DRY-RUN (só lista)" if dry else "✏️  LIVE (re-prepara e atualiza staging)"

    print()
    print("━" * 66)
    print("🔄 REPREPARE ML — Re-preparação completa de todos os produtos ML")
    print(f"   Modo: {mode}")
    print("━" * 66)

    session = SessionLocal()
    try:
        q = session.query(Product).filter(
            Product.platform == "mercadolivre",
            Product.disponivel == True,
            Product.external_id.isnot(None),
            Product.external_id != "",
        )
        if args.external_id:
            q = q.filter(Product.external_id == args.external_id)

        products = q.order_by(Product.created_at).all()
    finally:
        session.close()

    if not products:
        print("⚠️  Nenhum produto ML ativo encontrado.")
        sys.exit(0)

    total = len(products)
    print(f"\n📦 {total} produto(s) para re-preparar\n")

    reports = []
    ok = errors = 0

    for i, product in enumerate(products, 1):
        tag        = _parse_tag(product.tags)
        subcategory = product.subcategory or ""
        print(f"[{i:3d}/{total}] {(product.title or '')[:50]:<50}  {product.external_id}")
        print(f"        🏷️  {tag}/{subcategory}  →  {_ml_url(product.external_id)}")

        report = _prepare_one(product, dry_run=dry)
        reports.append(report)

        if report["status"] == "ok":
            ok += 1
            print(f"        ✅ Pronto")
        elif report["status"] == "dry_run":
            print(f"        ⏩ (dry-run)")
        else:
            errors += 1
            print(f"        ❌ Erro: {report['error']}")
        print()

    # ─── Após preparar todos → restage ────────────────────────────────────────
    print("━" * 66)
    print("📊 RESUMO")
    print("━" * 66)
    print(f"  Total            : {total}")
    if not dry:
        print(f"  ✅ Preparados    : {ok}")
        print(f"  ❌ Erros         : {errors}")

    if not dry and ok > 0:
        print()
        print("━" * 66)
        print("📤 Executando stage --force para publicar no banco...")
        print("━" * 66)
        stage_script = str(Path(__file__).parent / "stage_products.py")
        subprocess.run([sys.executable, stage_script, "--force"])

    if dry:
        print("\nℹ️  Nada foi alterado (--dry-run). Rode sem a flag para aplicar.")


if __name__ == "__main__":
    main()
