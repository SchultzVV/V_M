#!/usr/bin/env python3
"""
reprepare_associate_ml.py
Re-prepara TODOS os produtos ML do banco COM link de afiliado.
Usando a API oficial do ML para gerar meli.la/... short URL com affiliate_id.

Fluxo:
1. Obtem link de afiliado via API ML (/teams/{seller_id}/affiliate_link)
2. Usa esse link na ETAPA 5B para OCR mais preciso (/product endpoint)
3. Salva JSON com link de afiliado (comissao garantida)

Matem as mesmas tags e subcategorias ja cadastradas — sem perguntas interativas.
Apos preparar todos, imprime lembrete para rodar `make stage` manualmente.

Uso:
    python scripts/reprepare_associate_ml.py              # todos os produtos ML ativos
    python scripts/reprepare_associate_ml.py --id MLB123  # so um produto especifico
    python scripts/reprepare_associate_ml.py --dry-run    # apenas lista o que seria feito

Equivalente a: make reprepare-associate-ml

Requer:
    ML_SELLER_ID — ID de afiliado no Mercado Livre (no .env)
    Token OAuth ML valido (salvo em /app/config/ml_tokens.json)
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
from api_prepare_ml import get_affiliate_link

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


def _prepare_one(product: Product, dry_run: bool, seller_id: str = None) -> dict:
    """
    Chama prepare_ml_best.py para um unico produto COM link de afiliado.
    
    Fluxo:
    1. Obtem link de afiliado via API ML
    2. Passa AFFILIATE_URL para prepare_ml_best.py (etapa 5B)
    3. Salva JSON com link de afiliado
    
    Retorna dict com status do resultado.
    """
    tag        = _parse_tag(product.tags)
    subcategory = product.subcategory or ""
    url        = (product.link or "").strip() or _ml_url(product.external_id)

    report = {
        "external_id": product.external_id,
        "title":       (product.title or "")[:55],
        "tag":         tag,
        "subcategory": subcategory,
        "url":         url,
        "affiliate_link": None,
        "status":      "pending",
        "error":       None,
    }

    if dry_run:
        report["status"] = "dry_run"
        aff_link = get_affiliate_link(product.external_id, seller_id)
        if aff_link != url:
            report["affiliate_link"] = aff_link
        return report

    print(f"   Obtendo link de afiliado...")
    affiliate_link = get_affiliate_link(product.external_id, seller_id)
    report["affiliate_link"] = affiliate_link
    
    if not affiliate_link or affiliate_link == url:
        report["status"] = "error"
        report["error"]  = "nao conseguiu gerar affiliate link"
        print(f"   Erro ao gerar affiliate link")
        return report
    
    print(f"   OK: {affiliate_link}")

    env = os.environ.copy()
    env["FORCE_CATEGORY"]    = tag
    env["FORCE_SUBCATEGORY"] = subcategory
    env["AFFILIATE_URL"]     = affiliate_link
    env["ML_SELLER_ID"]      = seller_id or ""

    script = str(Path(__file__).parent / "prepare_ml_best.py")
    try:
        result = subprocess.run(
            [sys.executable, script, url],
            env=env,
            timeout=300,
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
    # Verificar ML_SELLER_ID
    seller_id = os.environ.get('ML_SELLER_ID', '').strip()
    if not seller_id:
        print("\nErro: ML_SELLER_ID nao configurado no .env")
        print("   Configure: export ML_SELLER_ID=seu_id_ml")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Re-prepara produtos ML com link de afiliado (matem tags/subcategoria)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Lista o que seria feito sem executar")
    parser.add_argument("--id", dest="external_id", default=None,
                        help="Processa apenas o produto com este external_id")
    args = parser.parse_args()

    dry  = args.dry_run
    mode = "DRY-RUN (so lista)" if dry else "LIVE (re-prepara e atualiza staging)"

    print()
    print("━" * 66)
    print("REPREPARE ASSOCIATE ML — COM link de afiliado")
    print(f"   Modo: {mode}")
    print(f"   Afiliado: {seller_id}")
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
        print(f"        {tag}/{subcategory}  →  {_ml_url(product.external_id)}")

        report = _prepare_one(product, dry_run=dry, seller_id=seller_id)
        reports.append(report)

        if report["status"] == "ok":
            ok += 1
            print(f"        OK")
            if report["affiliate_link"]:
                print(f"        Link: {report['affiliate_link']}")
        elif report["status"] == "dry_run":
            print(f"        (dry-run)")
            if report["affiliate_link"]:
                print(f"        Link: {report['affiliate_link']}")
        else:
            errors += 1
            print(f"        Erro: {report['error']}")
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
        print("✅ JSONs de staging gerados em /app/staging/")
        print("   Revise os arquivos e rode:")
        print("   make stage")
        print("━" * 66)

    if dry:
        print("\nℹ️  Nada foi alterado (--dry-run). Rode sem a flag para aplicar.")


if __name__ == "__main__":
    main()
