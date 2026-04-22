#!/usr/bin/env python3
"""
check_and_populate.py

Verifica quantos produtos existem em cada tag/subtag via banco de dados.
Para qualquer combinação com menos de MIN_PRODUCTS, executa:
  make populate-mf TAG=<tag> SUBTAG=<subtag> LIMIT=<limit>

Uso:
  python3 scripts/check_and_populate.py             # roda populate nas combos vazias
  python3 scripts/check_and_populate.py --dry-run   # apenas mostra o relatório
  python3 scripts/check_and_populate.py --min 3     # threshold (padrão: 1)
  python3 scripts/check_and_populate.py --limit 10  # produtos por query (padrão: 5)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

# ─── Configuração de tags e subtags ──────────────────────────────────────────
TAGS_SUBTAGS: dict[str, list[str]] = {
    "CD":  ["banheiro", "sala", "quarto", "cozinha", "garagem", "corredor", "sacada", "area-servico"],
    "ME":  ["feminino", "masculino", "calcados", "acessorios", "bolsas", "relogios", "infantil"],
    "E":   ["smartphones", "audio", "computadores", "tv", "games", "cameras", "smartwatch", "acessorios"],
    "PET": ["gatos", "caes", "racao", "higiene", "brinquedos", "acessorios", "saude"],
}

CONTAINER = "site"
MAKEFILE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def query_counts() -> dict[str, dict[str, int]]:
    """Consulta o banco dentro do container e retorna contagem por tag/subtag."""
    script = """import sys, json
sys.path.insert(0, '/app')
from main import app
with app.app_context():
    from models.product import Product
    ts = """ + json.dumps(TAGS_SUBTAGS) + """
    out = {}
    for tag, subs in ts.items():
        out[tag] = {
            "_total": Product.query.filter(
                Product.tags.ilike('%"' + tag + '"%')
            ).count()
        }
        for sub in subs:
            out[tag][sub] = Product.query.filter(
                Product.tags.ilike('%"' + tag + '"%'),
                Product.subcategory == sub
            ).count()
    print(json.dumps(out))
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        tmp_path = f.name

    try:
        subprocess.run(
            ["docker", "cp", tmp_path, f"{CONTAINER}:/tmp/_count_check.py"],
            check=True, capture_output=True,
        )
        result = subprocess.run(
            ["docker", "exec", CONTAINER, "python3", "/tmp/_count_check.py"],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(tmp_path)

    if result.returncode != 0:
        print("❌  Erro ao consultar o banco:")
        print(result.stderr[-800:])
        sys.exit(1)

    json_lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
    if not json_lines:
        print("❌  Nenhum JSON retornado. Saída:")
        print(result.stdout[:400])
        sys.exit(1)

    return json.loads(json_lines[-1])


def print_report(counts: dict, min_products: int) -> None:
    """Imprime tabela de counts e destaca as combos abaixo do threshold."""
    print("\n" + "─" * 60)
    print(f"  RELATÓRIO DE PRODUTOS POR TAG/SUBTAG  (mínimo: {min_products})")
    print("─" * 60)
    for tag, subs in counts.items():
        total = subs.get("_total", 0)
        print(f"\n  [{tag}]  total={total}")
        for sub, cnt in subs.items():
            if sub == "_total":
                continue
            flag = "  ← VAZIO" if cnt < min_products else ""
            bar = "█" * min(cnt, 20) if cnt > 0 else "·"
            print(f"    {sub:<16}  {cnt:>4}  {bar}{flag}")
    print("─" * 60 + "\n")


def run_populate(tag: str, subtag: str, limit: int) -> bool:
    """Executa `make populate-mf` para a combinação dada."""
    cmd = ["make", "populate-mf", f"TAG={tag}", f"SUBTAG={subtag}", f"LIMIT={limit}"]
    print(f"  ▶  make populate-mf TAG={tag} SUBTAG={subtag} LIMIT={limit}")
    result = subprocess.run(cmd, cwd=MAKEFILE_DIR)
    if result.returncode != 0:
        print(f"  ⚠️   Falhou (exit {result.returncode}) — continuando...\n")
        return False
    print(f"  ✅  Concluído\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra relatório, não executa make")
    parser.add_argument("--min", type=int, default=1, metavar="N", help="Mínimo de produtos por subtag (padrão: 1)")
    parser.add_argument("--limit", type=int, default=5, metavar="N", help="Produtos a buscar por make populate-mf (padrão: 5)")
    parser.add_argument("--tag", metavar="TAG", help="Processar somente esta tag (ex: CD)")
    args = parser.parse_args()

    print("\n🔍  Consultando banco de dados...")
    counts = query_counts()

    print_report(counts, args.min)

    # Collect combos below threshold
    to_populate: list[tuple[str, str]] = []
    for tag, subs in counts.items():
        if args.tag and tag != args.tag.upper():
            continue
        for sub, cnt in subs.items():
            if sub == "_total":
                continue
            if cnt < args.min:
                to_populate.append((tag, sub))

    if not to_populate:
        print("✅  Todas as combinações têm produtos suficientes. Nada a fazer.\n")
        return

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}📦  {len(to_populate)} combinação(ões) a popular:\n")
    for tag, sub in to_populate:
        print(f"     {tag}/{sub}")
    print()

    if args.dry_run:
        print("  --dry-run ativo: nenhum comando executado.\n")
        return

    ok = fail = 0
    for tag, sub in to_populate:
        if run_populate(tag, sub, args.limit):
            ok += 1
        else:
            fail += 1

    print("─" * 60)
    print(f"  Concluído: {ok} ✅  |  {fail} ⚠️")
    print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
