#!/usr/bin/env python3
"""
main.py — CLI do price_validator
Uso:
    python3 scripts/price_validator/main.py                       # lê list_to_verify.json
    python3 scripts/price_validator/main.py --file my_links.json  # arquivo customizado
    python3 scripts/price_validator/main.py --url https://...     # URL avulsa

Saída:
    Exibe resultado na tela e salva em cheaper_products.json
    (apenas os produtos onde existe alternativa mais barata)
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Garante imports relativos funcionando quando chamado via docker exec
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.price_validator.validator import validate_links, ValidationResult

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Paths padrão ─────────────────────────────────────────────────────────────
_BASE = Path(__file__).parent.parent.parent   # /app
_DEFAULT_INPUT  = _BASE / "list_to_prepare_and_stage" / "list_to_verify.json"
_DEFAULT_OUTPUT = _BASE / "cheaper_products.json"


# ─── Utils ────────────────────────────────────────────────────────────────────
def _load_urls_from_file(path: Path) -> list[str]:
    """
    Aceita dois formatos:
      {"links": ["url1", "url2"]}
      ou
      ["url1", "url2"]
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [item if isinstance(item, str) else item.get("url", "") for item in data]
    if isinstance(data, dict) and "links" in data:
        links = data["links"]
        return [item if isinstance(item, str) else item.get("url", "") for item in links]
    raise ValueError(f"Formato inválido em {path}. Esperado lista ou {{\"links\": [...]}}")


def _print_result(r: ValidationResult, idx: int, total: int) -> None:
    prefix = f"[{idx:>3}/{total}]"
    if r.error:
        print(f"{prefix} ❌  {r.item_id or r.original_link[:60]}  →  ERRO: {r.error}")
        return

    price_str = f"R$ {r.current_price:.2f}" if r.current_price else "—"
    freight   = "🚚 grátis" if r.free_shipping else "frete pago"

    # Página de catálogo: sem item de referência, apenas mostra o mais barato
    if r.is_cheapest is None:
        cheap_str     = f"R$ {r.cheapest_price:.2f}" if r.cheapest_price else "?"
        cheap_freight = "🚚 grátis" if r.cheapest_free_shipping else "frete pago"
        aff_line = f"\n          🔗 Afiliado: {r.affiliate_link}" if r.affiliate_link else ""
        print(
            f"{prefix} 🔍  {r.item_id}  [catálogo — {r.total_listings} ofertas]\n"
            f"          Mais barato: {cheap_str} ({cheap_freight})\n"
            f"          → {r.cheapest_link}"
            f"{aff_line}"
        )
    elif r.is_cheapest:
        print(f"{prefix} ✅  {r.item_id}  {price_str} ({freight})  — já é o mais barato")
    else:
        diff = f"R$ {r.price_difference:.2f} mais caro"
        cheap_str = f"R$ {r.cheapest_price:.2f}" if r.cheapest_price else "?"
        cheap_freight = "🚚 grátis" if r.cheapest_free_shipping else "frete pago"
        aff_line = f"\n          🔗 Afiliado: {r.affiliate_link}" if r.affiliate_link else ""
        print(
            f"{prefix} 💸  {r.item_id}  {price_str} ({freight})\n"
            f"          Mais barato: {cheap_str} ({cheap_freight})  [{diff}]\n"
            f"          → {r.cheapest_link}"
            f"{aff_line}"
        )


def _save_output(results: list[ValidationResult], output_path: Path) -> None:
    """Salva apenas os produtos que têm alternativa mais barata."""
    cheaper = [r for r in results if r.is_cheapest is False]

    payload = {
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "total_verificados": len(results),
        "total_mais_baratos_encontrados": len(cheaper),
        "produtos": [r.to_dict() for r in cheaper],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultado salvo em: {output_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifica se links ML são os mais baratos no catálogo"
    )
    parser.add_argument("--file", "-f", type=Path, default=None,
                        help="Arquivo JSON com lista de links")
    parser.add_argument("--url", "-u", type=str, default=None,
                        help="URL avulsa para verificar")
    parser.add_argument("--output", "-o", type=Path, default=_DEFAULT_OUTPUT,
                        help="Arquivo de saída (padrão: cheaper_products.json)")
    parser.add_argument("--workers", "-w", type=int, default=6,
                        help="Threads paralelas (padrão: 6)")
    args = parser.parse_args()

    # ── Carrega URLs ──
    if args.url:
        urls = [args.url]
    elif args.file:
        urls = _load_urls_from_file(args.file)
    elif _DEFAULT_INPUT.exists():
        urls = _load_urls_from_file(_DEFAULT_INPUT)
    else:
        print(f"❌ Nenhuma URL fornecida e {_DEFAULT_INPUT} não existe.")
        print(f"   Uso: python3 scripts/price_validator/main.py --url https://...")
        print(f"   Ou crie: {_DEFAULT_INPUT}")
        sys.exit(1)

    urls = [u for u in urls if u]   # remove vazios

    if not urls:
        print("❌ Lista de URLs está vazia.")
        sys.exit(1)

    total = len(urls)
    print()
    print("━" * 60)
    print(f"🔍 VERIFICADOR DE PREÇO — {total} produto(s)")
    print("━" * 60)
    print()

    # ── Processa ──
    results = validate_links(urls, max_workers=args.workers)

    # ── Exibe ──
    print()
    for i, r in enumerate(results, 1):
        _print_result(r, i, total)

    # ── Resumo ──
    ok       = sum(1 for r in results if r.is_cheapest is True)
    cheaper  = sum(1 for r in results if r.is_cheapest is False)
    errors   = sum(1 for r in results if r.error)

    print()
    print("━" * 60)
    print(f"📊 RESUMO")
    print(f"   ✅ Já é o mais barato:        {ok}")
    print(f"   💸 Existe opção mais barata:  {cheaper}")
    print(f"   ❌ Erros:                     {errors}")
    print("━" * 60)

    # ── Salva saída ──
    _save_output(results, args.output)

    if cheaper:
        print(f"\n⚡ {cheaper} produto(s) com preço melhor disponível!")
        print(f"   Veja: {args.output}")
    else:
        print(f"\n🎯 Todos os produtos já estão com o melhor preço disponível!")
    print()


if __name__ == "__main__":
    main()
