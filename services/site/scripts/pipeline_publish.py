#!/usr/bin/env python3
"""
pipeline_publish.py — Pipeline completo: prepare → organize-tags → stage → update prices

FLUXO POR PRODUTO:
  1. Detecta marketplace pela URL (regex: ML / Shopee / Amazon)
  2. Detecta categoria automaticamente pelo título via regex (FORCE_CATEGORY=auto)
  3. Executa o prepare script correspondente (sem interação manual)
  4. Depois de todos os prepares: organize-tags --auto (garante categorias corretas)
  5. Stage: publica staging JSONs novos no DB + MinIO
  6. Update prices: só para produtos ML (update_ml_prices_right.py)

USO:
  python3 scripts/pipeline_publish.py
  python3 scripts/pipeline_publish.py --file /app/staging/links_to_publish.json
  python3 scripts/pipeline_publish.py --dry-run
  python3 scripts/pipeline_publish.py --no-price-update
  python3 scripts/pipeline_publish.py --no-stage

ARQUIVO DE LINKS (JSON):
  {
    "links": [
      "https://mercadolivre.com.br/...",
      "https://shopee.com.br/...",
      "https://amazon.com.br/..."
    ]
  }
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
DEFAULT_LINKS_FILE = Path("/app/list_to_prepare_and_stage/links_to_publish.json")

# Mapeamento marketplace → script
PREPARE_SCRIPTS = {
    "ml":     "prepare_ml_best.py",
    "shopee": "shopee_prepare_best.py",
    "amazon": "amazon_prepare_best.py",
}

# ─────────────────────────────────────────────────────────────────────────────
# Detecção de marketplace
# ─────────────────────────────────────────────────────────────────────────────

def detect_marketplace(url: str) -> str:
    u = url.lower()
    if any(x in u for x in ["mercadolivre", "mercadolibre", "meli.la", "ml.la", "mln.la", "melidata"]):
        return "ml"
    if "shopee" in u:
        return "shopee"
    if any(x in u for x in ["amazon.com.br", "amzn.to", "amzn.com", "a.co/"]):
        return "amazon"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Execução dos scripts
# ─────────────────────────────────────────────────────────────────────────────

def run_prepare(url: str, marketplace: str) -> bool:
    """Roda o prepare script com FORCE_CATEGORY=auto (sem interação)."""
    script = SCRIPTS_DIR / PREPARE_SCRIPTS[marketplace]
    env = {
        **os.environ,
        "FORCE_CATEGORY": "auto",
        "FORCE_SUBCATEGORY": "",
    }
    result = subprocess.run(
        [sys.executable, str(script), url],
        env=env,
    )
    return result.returncode == 0


def run_organize_tags() -> bool:
    script = SCRIPTS_DIR / "organize_tags.py"
    result = subprocess.run([sys.executable, str(script), "--auto"])
    return result.returncode == 0


def run_stage() -> bool:
    script = SCRIPTS_DIR / "stage_products.py"
    result = subprocess.run([sys.executable, str(script)])
    return result.returncode == 0


def run_price_update() -> bool:
    script = SCRIPTS_DIR / "update_ml_prices_right.py"
    result = subprocess.run([sys.executable, str(script)])
    return result.returncode == 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo: prepare → organize → stage → update prices"
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_LINKS_FILE),
        help="Caminho para o JSON com a lista de links (default: links_to_publish.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula sem executar prepare/stage/update",
    )
    parser.add_argument(
        "--no-price-update",
        action="store_true",
        help="Pula a etapa de atualização de preços ML",
    )
    parser.add_argument(
        "--no-stage",
        action="store_true",
        help="Pula a etapa de publicação (stage)",
    )
    args = parser.parse_args()

    # ── Carregar links ──────────────────────────────────────────────────────
    links_file = Path(args.file)
    if not links_file.exists():
        print(f"❌ Arquivo não encontrado: {links_file}")
        print(f"   Crie o arquivo com {{ \"links\": [\"https://...\"] }}")
        sys.exit(1)

    with open(links_file) as f:
        data = json.load(f)

    links = data.get("links", [])
    if not links:
        print("❌ Nenhum link encontrado no arquivo.")
        sys.exit(1)

    print()
    print("━" * 70)
    print("🚀 PIPELINE COMPLETO — prepare → organize → stage → preços")
    print("━" * 70)
    print(f"  📄 Fonte  : {links_file}")
    print(f"  📦 Links  : {len(links)}")
    if args.dry_run:
        print("  🔍 Modo   : DRY-RUN (sem gravação)")
    print()

    results = {"ok": [], "fail": [], "skip": []}
    ml_prepared = []

    # ── ETAPA 1: Prepare de cada link ───────────────────────────────────────
    for i, url in enumerate(links, 1):
        marketplace = detect_marketplace(url)
        print(f"{'━' * 70}")
        print(f"[{i}/{len(links)}] {url}")
        print(f"       Marketplace: {marketplace.upper() if marketplace != 'unknown' else '⚠️  DESCONHECIDO'}")

        if marketplace == "unknown":
            print("  ⚠️  URL não reconhecida — pulando")
            results["skip"].append(url)
            continue

        if args.dry_run:
            print(f"  [dry-run] executaria: {PREPARE_SCRIPTS[marketplace]}")
            results["ok"].append(url)
            if marketplace == "ml":
                ml_prepared.append(url)
            continue

        ok = run_prepare(url, marketplace)
        if ok:
            results["ok"].append(url)
            if marketplace == "ml":
                ml_prepared.append(url)
        else:
            print(f"  ❌ Prepare falhou para: {url}")
            results["fail"].append(url)

    if not results["ok"]:
        print("\n⚠️  Nenhum produto foi preparado com sucesso.")
        _print_summary(results)
        sys.exit(1 if results["fail"] else 0)

    # ── ETAPA 2: Organize tags (auto) ────────────────────────────────────────
    print()
    print("━" * 70)
    print("🏷️  ETAPA 2 — Organize tags (auto)")
    print("━" * 70)
    if args.dry_run:
        print("  [dry-run] organize_tags.py --auto")
    else:
        run_organize_tags()

    # ── ETAPA 3: Stage ──────────────────────────────────────────────────────
    if not args.no_stage:
        print()
        print("━" * 70)
        print("📤 ETAPA 3 — Stage (DB + MinIO)")
        print("━" * 70)
        if args.dry_run:
            print("  [dry-run] stage_products.py")
        else:
            ok = run_stage()
            if not ok:
                print("  ❌ Stage falhou — verifique os logs")

    # ── ETAPA 4: Atualizar preços ML ─────────────────────────────────────────
    if not args.no_price_update and ml_prepared:
        print()
        print("━" * 70)
        print("💰 ETAPA 4 — Atualizar preços ML")
        print(f"   ({len(ml_prepared)} produto(s) ML preparado(s))")
        print("━" * 70)
        if args.dry_run:
            print("  [dry-run] update_ml_prices_right.py")
        else:
            run_price_update()
    elif args.no_price_update:
        print("\n  ⏭️  Etapa de preços pulada (--no-price-update)")
    elif not ml_prepared:
        print("\n  ℹ️  Nenhum produto ML — etapa de preços ignorada")

    _print_summary(results)


def _print_summary(results: dict):
    print()
    print("━" * 70)
    print("✅ PIPELINE CONCLUÍDO")
    print("━" * 70)
    print(f"  ✅ Sucesso : {len(results['ok'])}")
    print(f"  ❌ Falhas  : {len(results['fail'])}")
    print(f"  ⏭️  Pulados : {len(results['skip'])}")
    if results["fail"]:
        print("\n  Produtos com falha:")
        for u in results["fail"]:
            print(f"    - {u}")
    print()


if __name__ == "__main__":
    main()
