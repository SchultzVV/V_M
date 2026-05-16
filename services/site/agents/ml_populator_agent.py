#!/usr/bin/env python3
"""
ml_populator_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Popula o site com produtos do Mercado Livre, tag por tag, subtag por
subtag.

FLUXO por (tag, subtag, query):
  1. Busca ML API: GET /sites/MLB/search?q={query}&sort=sold_quantity
     → seleciona os top N=5 mais vendidos
  2. Para cada resultado:
     a. external_id = result["id"]   (ex: MLB55308793)
     b. Verifica no banco: Product com esse external_id + platform
     c. Se EXISTS   → _find_cheapest_for_id() → atualiza price/link
                      se encontrar vendedor mais barato (igual a
                      update_ml_prices.py)
     d. Se NOT IN DB → _find_cheapest_for_id() → obtém permalink do
                        mais barato → generate_affiliate_link() → coleta
                        URL na lista de novos
  3. Ao final de cada subtag: se há novas URLs →
       - Escreve em links_to_publish.json
       - Chama pipeline_publish.py --no-price-update --no-tag-classify
         (prepare → organize-tags → stage)

Uso:
    python3 agents/ml_populator_agent.py               # todas as tags
    python3 agents/ml_populator_agent.py --tag PET     # só PET
    python3 agents/ml_populator_agent.py --tag PET --subtag gatos
    python3 agents/ml_populator_agent.py --dry-run     # simula sem gravar
    python3 agents/ml_populator_agent.py --limit 3     # N produtos/query
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ─── Path setup (igual a reprice_all.py) ─────────────────────────────────────
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

# ─── Imports internos ─────────────────────────────────────────────────────────
from database import SessionLocal
from models.product import Product
from scripts.price_validator.ml_api import get_item, get_catalog_listings
from scripts.price_validator.price_service import parse_catalog_listings, find_cheapest
from scripts.price_validator.affiliate import generate_affiliate_link

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
_API_BASE = "https://api.mercadolibre.com"
_HEADERS = {"User-Agent": "V_M-ml-populator/1.0"}
_LINKS_FILE = Path("/app/list_to_prepare_and_stage/links_to_publish.json")
_PIPELINE_SCRIPT = Path(_APP_DIR) / "scripts" / "pipeline_publish.py"

# ─── Mapa de queries por tag/subtag ───────────────────────────────────────────
# Cada subtag tem uma lista de queries que representam os produtos mais buscados
# mensalmente. Começa pelos 3 exemplos chave: ração gato macrogard, macrogard e
# areia higiênica.
SEARCH_QUERIES: dict[str, dict[str, list[str]]] = {
    "PET": {
        "gatos": [
            "ração gato macrogard",
            "areia higiênica gato",
            "macrogard gato suplemento",
            "ração de gato seca premium",
            "comedouro automático gato",
        ],
        "racao": [
            "ração gato adulto castrado",
            "ração cachorro adulto premium",
            "ração filhote cachorro",
            "ração gato indoor",
        ],
        "caes": [
            "ração cachorro premium seca",
            "petisco osso natural cachorro",
            "brinquedo mordedor cachorro",
            "ração raça pequena cachorro",
        ],
        "higiene": [
            "areia higiênica gato clumping",
            "tapete higiênico cachorro grande",
            "shampoo neutro pet",
            "lenço umedecido pet",
        ],
        "brinquedos": [
            "brinquedo gato interativo penas",
            "brinquedo cachorro pelúcia resistente",
            "arranhador gato sisal",
        ],
        "acessorios": [
            "coleira regulável cachorro",
            "guia retrátil cachorro 5m",
            "bebedouro fonte gato elétrico",
            "cama cachorro lavável",
        ],
        "saude": [
            "antipulgas gato frontline",
            "vermífugo para gato",
            "suplemento imunidade gato macrogard",
            "antipulgas cachorro bravecto",
        ],
    },
    "E": {
        "smartphones": [
            "smartphone samsung galaxy a55",
            "smartphone xiaomi redmi note",
        ],
        "audio": [
            "fone bluetooth sem fio",
            "caixa de som bluetooth portátil",
        ],
        "computadores": [
            "teclado mecânico gamer",
            "mouse gamer sem fio",
        ],
        "tv": [
            "smart tv 50 polegadas 4k",
        ],
        "games": [
            "controle dualsense playstation 5",
            "headset gamer sem fio",
        ],
        "cameras": [
            "câmera de segurança wifi externa",
        ],
        "smartwatch": [
            "smartwatch xiaomi band",
            "smartwatch samsung galaxy watch",
        ],
        "acessorios": [
            "cabo usb-c 2m carga rápida",
            "carregador turbo tipo c 65w",
        ],
    },
    "CD": {
        "banheiro": [
            "cesto roupa suja bambu",
            "organizador banheiro kit",
        ],
        "sala": [
            "luminária led sala",
            "tapete sala decorativo moderno",
        ],
        "quarto": [
            "luminária de cabeceira led",
            "travesseiro cervical ortopédico",
            "roupa de cama queen size",
            "cabeceira cama casal",
            "colcha casal matelassê",
        ],
        "cozinha": [
            "organizador cozinha modular",
            "suporte temperos parede inox",
        ],
        "garagem": [
            "kit ferramentas completo 100 peças",
            "chave combinada estojo",
            "caixa de ferramentas plástico",
            "furadeira parafusadeira",
        ],
        "corredor": [
            "sapateira organizador corredor",
        ],
        "sacada": [
            "vaso autoirrigável plantas",
        ],
        "area-servico": [
            "varal de parede retrátil aço",
            "tábua de passar roupa",
            "cesto roupas sujas com tampa",
            "escada doméstica alumínio",
        ],
    },
    "ME": {
        "feminino": [
            "bolsa feminina couro sintético",
            "sandália rasteira feminina",
        ],
        "masculino": [
            "tênis casual masculino",
            "carteira couro slim masculino",
        ],
        "calcados": [
            "tênis corrida masculino",
            "sapatilha feminina conforto",
        ],
        "acessorios": [
            "cinto couro legítimo masculino",
            "óculos de sol feminino polarizado",
        ],
        "bolsas": [
            "bolsa tote grande feminina",
            "mochila feminina notebook",
        ],
        "relogios": [
            "relógio masculino analógico aço",
            "relógio feminino pulseira couro",
        ],
        "infantil": [
            "tênis infantil menino",
            "vestido infantil casual",
        ],
    },
    "ES": {
        "futebol": [
            "chuteira campo adulto",
            "bola de futebol society oficial",
            "caneleira futebol adulto",
        ],
        "corrida": [
            "tênis de corrida masculino leve",
            "tênis corrida feminino",
            "meia cano médio corrida",
        ],
        "academia": [
            "haltere borracha par 10kg",
            "kettlebell 12kg",
            "corda de pular speed crossfit",
            "colchonete academia 10mm",
        ],
        "natacao": [
            "óculos de natação profissional",
            "touca de natação silicone",
            "prancha de natação iniciante",
        ],
        "ciclismo": [
            "capacete bike ciclismo urbano",
            "luva ciclismo dedo cortado",
            "bicicleta urbana aro 29",
        ],
        "tenis": [
            "raquete tênis adulto iniciante",
            "bola de tênis pack 3 unidades",
            "raquete beach tennis profissional",
        ],
        "esportes-radicais": [
            "capacete skate proteção",
            "patins inline adulto",
            "kit proteção joelheira cotoveleira",
        ],
        "acessorios": [
            "garrafa térmica esportiva 1l",
            "mochila esportiva academia 30l",
            "suporte celular bike guidão",
        ],
    },
}


# ─── Helpers de preço (idênticos a update_ml_prices.py) ──────────────────────

def _parse_price(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("R$", "").replace("\xa0", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _fmt(price: float) -> str:
    """Float → 'R$ 1.234,56'"""
    s = f"{price:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


# ─── Core: cheapest seller (idêntico a update_ml_prices.py) ──────────────────

def _find_cheapest_for_id(external_id: str):
    """
    Dado um external_id ML, retorna (Listing mais barato, catalog_id, total).

    1. GET /items/{id}  → catalog_product_id
    2. Fallback: usa o próprio id como catalog_product_id
    3. GET /products/{catalog_id}/items → vendedores ativos
    4. find_cheapest()
    """
    catalog_id = None
    item_data = get_item(external_id)
    if item_data:
        catalog_id = item_data.get("catalog_product_id")
    if not catalog_id:
        catalog_id = external_id

    raw_listings = get_catalog_listings(catalog_id)
    all_listings = parse_catalog_listings(raw_listings)

    if not all_listings:
        return None, catalog_id, 0

    cheapest = find_cheapest(all_listings)
    return cheapest, catalog_id, len(all_listings)


def _resolve_permalink(cheapest, catalog_id: str, external_id: str = "") -> tuple:
    """
    Garante que cheapest.permalink está preenchido.

    Retorna (url, is_reliable):
      is_reliable=True  → permalink real obtido pela API (full slug URL)
      is_reliable=False → fallback construído; não deve sobrescrever link existente

    Prioridade:
      1. permalink já preenchido no listing                       → confiável
      2. permalink retornado por /items/{item_id}                 → confiável
      3. item_id existe mas permalink é null → /p/{item_id}       → semi-confiável
      4. fallback: /p/{external_id}   (catalog page do produto)   → semi-confiável
         NUNCA usa catalog_id do listing — pode não ter página no site ML.
    """
    if cheapest.permalink:
        return cheapest.permalink, True

    item_data = get_item(cheapest.item_id)
    if item_data:
        permalink = item_data.get("permalink") or ""
        if permalink:
            cheapest.permalink = permalink
            return permalink, True
        else:
            # Item existe mas permalink é null; usa item_id diretamente.
            cheapest.permalink = f"https://www.mercadolivre.com.br/p/{cheapest.item_id}"
            return cheapest.permalink, True

    # get_item falhou — não temos permalink real.
    # Usa external_id (produto original que o usuário estava visitando) como fallback.
    fallback_id = external_id or cheapest.item_id
    cheapest.permalink = f"https://www.mercadolivre.com.br/p/{fallback_id}"
    return cheapest.permalink, False


# ─── Busca ML por keyword ─────────────────────────────────────────────────────

def _slugify_query(query: str) -> str:
    """'ração gato macrogard' → 'racao-gato-macrogard'"""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", query.lower())
    ascii_str = nfkd.encode("ASCII", "ignore").decode("ASCII")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str).strip("-")
    return slug


def _search_ml_website(query: str, limit: int) -> list:
    """
    Fallback: scrape público de lista.mercadolivre.com.br/{slug}.

    Não chama get_item() aqui — a página expõe catalog product IDs (formato /p/MLB...)
    que retornariam 404 em /items/{id}. Retorna stubs {id, title, permalink} e deixa
    _find_cheapest_for_id() (chamado downstream) resolver cada ID via
    /products/{catalog_id}/items, que é público e funciona.
    """
    slug = _slugify_query(query)
    url = f"https://lista.mercadolivre.com.br/{slug}"

    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    try:
        resp = requests.get(url, headers=browser_headers, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            logger.info(f"Website {resp.status_code} para '{query}'")
            return []

        html = resp.text

        # 1ª opção: IDs de catálogo em links de produto  /p/MLB12345678
        catalog_ids = list(dict.fromkeys(re.findall(r"/p/(MLB\d{5,12})", html)))

        # 2ª opção: IDs embutidos em JSON do pre-loaded state: "id":"MLB12345678"
        json_ids = list(dict.fromkeys(re.findall(r'"id"\s*:\s*"(MLB\d{8,12})"', html)))

        # Preferir catalog IDs (mais confiáveis), completar com JSON IDs
        all_ids = catalog_ids + [i for i in json_ids if i not in set(catalog_ids)]

        if not all_ids:
            # Último recurso: qualquer MLB¹⁰+ no texto
            all_ids = list(dict.fromkeys(re.findall(r"MLB\d{10,12}", html)))

        fetch_limit = min(limit * 4, 40)
        unique_ids = all_ids[:fetch_limit]

        if not unique_ids:
            logger.info(f"Nenhum ID no HTML para '{query}'")
            return []

        logger.info(f"Website '{query}': {len(unique_ids)} IDs (catalog:{len(catalog_ids)} json:{len(json_ids)})")

        # Retorna stubs — _find_cheapest_for_id() valida e resolve cada ID
        return [
            {
                "id": mid,
                "title": "",
                "permalink": f"https://www.mercadolivre.com.br/p/{mid}",
            }
            for mid in unique_ids
        ]

    except Exception as e:
        logger.info(f"Website scrape falhou para '{query}': {e}")
        return []


def _search_ml_api(query: str, limit: int, token: str) -> list:
    """
    GET /sites/MLB/search — tenta 3 variantes em cascata.
    Retorna [] se todas retornarem 403 (sem permissão de search na conta ML).
    """
    url = f"{_API_BASE}/sites/MLB/search"
    fetch_limit = min(limit * 3, 50)

    attempts = [
        (
            {**_HEADERS, "Authorization": f"Bearer {token}"},
            {"q": query, "sort": "sold_quantity", "limit": fetch_limit},
        ),
        (
            {**_HEADERS, "Authorization": f"Bearer {token}"},
            {"q": query, "limit": fetch_limit},
        ),
        (
            _HEADERS,
            {"q": query, "limit": fetch_limit},
        ),
    ]

    for headers, params in attempts:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 403:
                continue
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                return results
            return []
        except requests.HTTPError:
            continue
        except Exception as e:
            logger.debug(f"API search exception para '{query}': {e}")
            return []

    return []


def _search_ml(query: str, limit: int, token: str) -> list:
    """
    Estratégia de busca:
      1. ML API /sites/MLB/search (requer permissão 'search' no DevCenter ML)
      2. Fallback: scrape público de lista.mercadolivre.com.br/{slug}
    """
    results = _search_ml_api(query, limit, token)
    if results:
        return results

    logger.info(f"API search falhou para '{query}' — usando website scrape")
    return _search_ml_website(query, limit)


# ─── Atualiza produto existente (mesmo padrão de update_ml_prices.py) ─────────

def _update_existing(product: Product, session, dry_run: bool) -> str:
    """Busca vendedor mais barato e atualiza preço/link se necessário."""
    current_price = _parse_price(product.price)
    try:
        cheapest, catalog_id, total = _find_cheapest_for_id(product.external_id)
    except Exception as e:
        return f"error: {e}"

    if cheapest is None:
        return "no_data"

    permalink, is_reliable = _resolve_permalink(cheapest, catalog_id, product.external_id)
    affiliate = generate_affiliate_link(permalink) if permalink else ""

    # Guarda de título: recusa update se produto diverge muito
    cheapest_title = getattr(cheapest, "title", "") or ""
    if cheapest_title and product.title:
        def _words(t):
            return set(w for w in re.sub(r"[^a-z0-9 ]", " ", t.lower()).split() if len(w) > 3)
        our = _words(product.title)
        theirs = _words(cheapest_title)
        common = our & theirs
        if our and len(common) / len(our) < 0.2:
            return f"title_mismatch"

    if current_price > 0 and cheapest.real_price >= current_price * 0.99:
        return "cheapest"

    if not dry_run:
        product.old_price = product.price
        product.price = _fmt(cheapest.real_price)
        # Só atualiza o link se temos um permalink confiável (real da API).
        # Fallbacks construídos (/p/MLB...) podem não ter página no ML.
        if is_reliable:
            product.link = affiliate or permalink
        product.updated_at = datetime.utcnow()
        session.commit()

    return f"updated→{_fmt(cheapest.real_price)}"


# ─── Obtém URL mais barata para produto novo ──────────────────────────────────

def _get_cheapest_url(external_id: str, fallback_url: str) -> str:
    """Para produto ainda não no banco: obtém a URL do vendedor mais barato."""
    try:
        cheapest, catalog_id, total = _find_cheapest_for_id(external_id)
    except Exception as e:
        print(f"         ⚠️  cheapest err: {e}")
        return fallback_url

    if cheapest is None:
        print(f"         ℹ️  sem vendedores no catálogo — usando URL direta")
        return fallback_url

    print(f"         💸 {total} vendedor(es) → mais barato: {_fmt(cheapest.real_price)}")
    permalink, is_reliable = _resolve_permalink(cheapest, catalog_id, external_id)
    if not is_reliable:
        # Sem permalink real da API — usa fallback_url (página de catálogo original).
        return generate_affiliate_link(fallback_url) or fallback_url
    affiliate = generate_affiliate_link(permalink) if permalink else ""
    return affiliate or permalink or fallback_url


# ─── links_to_publish.json ────────────────────────────────────────────────────

def _append_to_links_file(new_urls: list[str]) -> int:
    """Adiciona URLs ao links_to_publish.json sem duplicar. Retorna qtd adicionada."""
    _LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if _LINKS_FILE.exists() and _LINKS_FILE.stat().st_size > 2:
        with open(_LINKS_FILE) as f:
            data = json.load(f)
    else:
        data = {"links": []}

    existing = set(data.get("links", []))
    added = [u for u in new_urls if u not in existing]
    data["links"] = list(existing) + added

    with open(_LINKS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return len(added)


# ─── Pipeline (prepare → organize-tags → stage) ───────────────────────────────

def _run_pipeline(dry_run: bool, subtag: str = "") -> bool:
    """
    Chama pipeline_publish.py com:
      --no-price-update  (preço já foi obtido pelo agente)
      --no-tag-classify  (evita LLM lento; organize_tags --auto já categoriza)
      --subcategory      (subtag atual → FORCE_SUBCATEGORY no prepare)
    """
    cmd = [
        sys.executable,
        str(_PIPELINE_SCRIPT),
        "--no-price-update",
        "--no-tag-classify",
    ]
    if subtag:
        cmd += ["--subcategory", subtag]
    if dry_run:
        cmd.append("--dry-run")
    print(f"\n   ▶▶ pipeline: {' '.join(Path(c).name if c.endswith('.py') else c for c in cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


# ─── Processamento de um subtag ───────────────────────────────────────────────

def process_subtag(
    tag: str,
    subtag: str,
    queries: list[str],
    limit: int,
    dry_run: bool,
    token: str,
) -> dict:
    """Itera queries do subtag, coleta novos e atualiza existentes."""
    stats = {"updated": 0, "new": 0, "skip": 0, "error": 0}
    new_urls: list[str] = []
    seen_ids: set[str] = set()  # dedup cross-query

    session = SessionLocal()
    try:
        for query in queries:
            print(f"\n   🔍 {query!r}")
            results = _search_ml(query, limit=limit, token=token)
            if not results:
                print(f"      ⚠️  nenhum resultado para essa query")
                continue
            print(f"      → {len(results)} produto(s) candidatos")
            collected = 0

            for result in results:
                if collected >= limit:
                    break

                external_id = result.get("id", "")
                title = result.get("title", "") or external_id

                if not external_id or external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                existing = (
                    session.query(Product)
                    .filter_by(external_id=external_id, platform="mercadolivre")
                    .first()
                )

                short_title = (title[:52] + "…") if len(title) > 52 else (title or external_id)
                if existing:
                    print(f"      ↻  [{external_id}] {short_title}  (já no banco → atualiza preço)")
                    status = _update_existing(existing, session, dry_run)
                    icon = "✅" if status.startswith("updated") else ("⚠️" if "error" in status else "✔️")
                    print(f"         {icon} {status}")
                    if status.startswith("updated"):
                        stats["updated"] += 1
                    elif status.startswith("error"):
                        stats["error"] += 1
                    else:
                        stats["skip"] += 1
                else:
                    print(f"      ✨ [{external_id}] {short_title}  (novo → buscando mais barato)")
                    fallback = result.get("permalink", "") or f"https://www.mercadolivre.com.br/p/{external_id}"
                    url = _get_cheapest_url(external_id, fallback)
                    print(f"         🔗 {url[:90]}")
                    new_urls.append(url)
                    stats["new"] += 1

                collected += 1
                time.sleep(0.3)  # respeita rate-limit ML API

    finally:
        session.close()

    # Publica novos via pipeline
    if new_urls:
        if not dry_run:
            added = _append_to_links_file(new_urls)
            print(f"\n   📤 {added} URL(s) → links_to_publish.json  |  rodando pipeline…")
            ok = _run_pipeline(dry_run=False, subtag=subtag)
            if not ok:
                print("   ⚠️  Pipeline retornou erro — verifique os logs do container")
        else:
            print(f"\n   [dry-run] {len(new_urls)} URL(s) seriam publicadas:")
            for u in new_urls:
                print(f"      • {u[:100]}")

    return stats


# ─── Verificação de token ─────────────────────────────────────────────────────

def _check_ml_token() -> Optional[str]:
    try:
        from services.ml_auth import ml_auth
        token = ml_auth.get_valid_access_token()
        if token:
            print("   🔑 Token OAuth: ✅ válido")
            return token
    except Exception as e:
        print(f"   ⚠️  Erro ao verificar token: {e}")

    print("\n❌ TOKEN OAUTH ML AUSENTE OU EXPIRADO")
    print("   1. Execute:  make serve-cloudflare")
    print("   2. Atualize o Redirect URI no DevCenter ML")
    print("   3. Clique no link de autorização exibido")
    print("   4. Execute novamente:  make populate-mf")
    return None


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Popula o site tag por tag, subtag por subtag via Mercado Livre"
    )
    parser.add_argument(
        "--tag",
        default=None,
        choices=list(SEARCH_QUERIES.keys()),
        help="Filtra por tag (PET, E, CD, ME). Padrão: todas.",
    )
    parser.add_argument(
        "--subtag",
        default=None,
        help="Filtra por subtag (ex: gatos, racao, caes).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Número máximo de produtos por query (default: 5).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula sem gravar no banco nem publicar.",
    )
    args = parser.parse_args()

    print()
    print("━" * 70)
    print("🛒 ML POPULATOR — Popula o site via Mercado Livre")
    if args.dry_run:
        print("   Modo: 🔍 DRY-RUN (sem gravação)")
    print("━" * 70)

    token = _check_ml_token()
    if not token:
        sys.exit(1)

    tags_to_process = [args.tag] if args.tag else list(SEARCH_QUERIES.keys())
    total = {"updated": 0, "new": 0, "skip": 0, "error": 0}

    for tag in tags_to_process:
        all_subtags = SEARCH_QUERIES.get(tag, {})

        if args.subtag:
            if args.subtag not in all_subtags:
                print(f"\n⚠️  Subtag {args.subtag!r} não encontrada em {tag}")
                print(f"   Subtags disponíveis: {', '.join(all_subtags)}")
                continue
            subtags = {args.subtag: all_subtags[args.subtag]}
        else:
            subtags = all_subtags

        print()
        print("━" * 70)
        print(f"🏷️  TAG: {tag}  ({len(subtags)} subtag(s))")
        print("━" * 70)

        for subtag, queries in subtags.items():
            print(f"\n  📂 {tag}/{subtag}  ({len(queries)} query(s))")
            stats = process_subtag(tag, subtag, queries, args.limit, args.dry_run, token)
            for k, v in stats.items():
                total[k] += v
            print(
                f"      → atualizados: {stats['updated']} | "
                f"novos: {stats['new']} | "
                f"sem mudança: {stats['skip']} | "
                f"erros: {stats['error']}"
            )

    print()
    print("━" * 70)
    print("✅ POPULATE-MF CONCLUÍDO")
    print(f"   Atualizados (preço) : {total['updated']}")
    print(f"   Publicados (novos)  : {total['new']}")
    print(f"   Sem mudança         : {total['skip']}")
    print(f"   Erros               : {total['error']}")
    print("━" * 70)
    print()


if __name__ == "__main__":
    main()
