#!/usr/bin/env python3
"""
pipeline_publish.py — Pipeline completo: prepare → organize-tags → stage → tag-LLM → archive

FLUXO POR PRODUTO:
  1. Detecta marketplace pela URL (regex: ML / Shopee / Amazon)
  2. Detecta categoria automaticamente pelo título via regex (FORCE_CATEGORY=auto)
  3. Executa o prepare script correspondente (sem interação manual)
  4. Depois de todos os prepares: organize-tags --auto (garante categorias corretas)
  5. Stage: publica staging JSONs novos no DB + MinIO
  6. Update prices: só para produtos ML (update_ml_prices_right.py)
  7. LLM tag classify: tag_classifier_agent.py --db (classifica produtos sem tag/geral)
  8. Archive: links publicados → staged/staged_links.json; remove de links_to_publish.json

USO:
  python3 scripts/pipeline_publish.py
  python3 scripts/pipeline_publish.py --file /app/list_to_prepare_and_stage/links_to_publish.json
  python3 scripts/pipeline_publish.py --dry-run
  python3 scripts/pipeline_publish.py --no-price-update
  python3 scripts/pipeline_publish.py --no-stage
  python3 scripts/pipeline_publish.py --no-tag-classify

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
AGENTS_DIR  = Path(__file__).parent.parent / "agents"
DEFAULT_LINKS_FILE  = Path("/app/list_to_prepare_and_stage/links_to_publish.json")
STAGED_LINKS_FILE   = Path("/app/list_to_prepare_and_stage/staged/staged_links.json")

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

def run_prepare(url: str, marketplace: str, subcategory: str = "") -> bool:
    """Roda o prepare script com FORCE_CATEGORY=auto (sem interação)."""
    script = SCRIPTS_DIR / PREPARE_SCRIPTS[marketplace]
    env = {
        **os.environ,
        "FORCE_CATEGORY": "auto",
        "FORCE_SUBCATEGORY": subcategory,
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


def run_tag_classify_db() -> bool:
    """Classifica via LLM os produtos no banco sem tag ou com tag=geral."""
    agent = AGENTS_DIR / "tag_classifier_agent.py"
    result = subprocess.run([sys.executable, str(agent), "--db"])
    return result.returncode == 0


def archive_links(published: list[str], links_file: Path) -> None:
    """
    Move os links publicados com sucesso:
      - Adiciona em staged/staged_links.json
      - Remove de links_to_publish.json
    """
    # ── Carregar / inicializar staged_links.json ───────────────────────────
    STAGED_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STAGED_LINKS_FILE.exists() and STAGED_LINKS_FILE.stat().st_size > 0:
        with open(STAGED_LINKS_FILE) as f:
            staged_data = json.load(f)
    else:
        staged_data = {"links": []}

    already_staged = set(staged_data.get("links", []))
    new_staged = [u for u in published if u not in already_staged]
    staged_data["links"] = list(already_staged) + new_staged

    with open(STAGED_LINKS_FILE, "w") as f:
        json.dump(staged_data, f, indent=2, ensure_ascii=False)
    print(f"  📁 {len(new_staged)} link(s) arquivado(s) → {STAGED_LINKS_FILE}")

    # ── Remover links publicados de links_to_publish.json ──────────────────
    with open(links_file) as f:
        todo_data = json.load(f)

    published_set = set(published)
    remaining = [u for u in todo_data.get("links", []) if u not in published_set]
    todo_data["links"] = remaining

    with open(links_file, "w") as f:
        json.dump(todo_data, f, indent=2, ensure_ascii=False)
    print(f"  🗑️  {len(published_set)} link(s) removido(s) de {links_file.name} ({len(remaining)} restantes)")


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
    parser.add_argument(
        "--no-tag-classify",
        action="store_true",
        help="Pula a classificação LLM de tags (etapa 7)",
    )
    parser.add_argument(
        "--subcategory",
        default="",
        help="Força subcategoria (subtag) para todos os produtos preparados neste lote.",
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
    print("🚀 PIPELINE COMPLETO — prepare → organize → stage → LLM tags → archive")
    print("━" * 70)
    print(f"  📄 Fonte  : {links_file}")
    print(f"  📦 Links  : {len(links)}")
    if args.dry_run:
        print("  🔍 Modo   : DRY-RUN (sem gravação)")
    print()

    results: dict[str, list] = {"ok": [], "fail": [], "skip": []}
    ml_prepared: list[str] = []

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

        ok = run_prepare(url, marketplace, subcategory=args.subcategory)
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

    # ── ETAPA 5: LLM Tag Classify ────────────────────────────────────────────
    if not args.no_tag_classify and not args.no_stage and results["ok"]:
        print()
        print("━" * 70)
        print("🤖 ETAPA 5 — LLM Tag Classify (produtos sem tag / geral)")
        print("━" * 70)
        if args.dry_run:
            print("  [dry-run] tag_classifier_agent.py --db")
        else:
            ok = run_tag_classify_db()
            if not ok:
                print("  ⚠️  Tag classify retornou erro — produtos publicados, verifique as tags manualmente")
    else:
        if args.no_tag_classify:
            print("\n  ⏭️  Tag classify pulado (--no-tag-classify)")

    # ── ETAPA 6: Arquivar links publicados ───────────────────────────────────
    if results["ok"] and not args.dry_run:
        print()
        print("━" * 70)
        print("📁 ETAPA 6 — Arquivar links publicados")
        print("━" * 70)
        archive_links(results["ok"], links_file)
    elif args.dry_run and results["ok"]:
        print()
        print("━" * 70)
        print("📁 ETAPA 6 — Archive [dry-run]")
        print("━" * 70)
        print(f"  [dry-run] moveriam {len(results['ok'])} link(s) → staged/staged_links.json")

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
