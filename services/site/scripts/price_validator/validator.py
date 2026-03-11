"""
validator.py
Orquestra o fluxo completo de validação de preço:
  URL → MLB ID → item data → catalog → cheapest → comparação
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .url_parser import detect_url_type
from .ml_api import get_item, get_catalog_listings
from .price_service import listing_from_api, parse_catalog_listings, find_cheapest, Listing
from .affiliate import generate_affiliate_link

logger = logging.getLogger(__name__)


def _resolve_permalink(listing: "Listing", catalog_id: str = "") -> str:
    """
    Retorna o permalink do listing.
    Se estiver vazio (caso do endpoint /products/{id}/items que não retorna permalink),
    faz GET /items/{item_id} para obter o permalink real.
    Fallback final: URL da página de catálogo se catalog_id for fornecido.
    """
    if listing.permalink:
        return listing.permalink
    item_data = get_item(listing.item_id)
    if item_data:
        listing.permalink = item_data.get("permalink", "") or ""
    if not listing.permalink and catalog_id:
        listing.permalink = f"https://www.mercadolivre.com.br/p/{catalog_id}"
    return listing.permalink


@dataclass
class ValidationResult:
    """Resultado da validação de um link."""
    original_link: str
    item_id: Optional[str] = None
    is_cheapest: Optional[bool] = None
    current_price: Optional[float] = None
    cheapest_price: Optional[float] = None
    cheapest_link: Optional[str] = None
    affiliate_link: Optional[str] = None       # cheapest_link com parâmetro matt_tool
    price_difference: Optional[float] = None   # current - cheapest (positivo = mais caro)
    free_shipping: Optional[bool] = None
    cheapest_free_shipping: Optional[bool] = None
    catalog_product_id: Optional[str] = None
    total_listings: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("is_cheapest", "error")}


def validate_single(url: str) -> ValidationResult:
    """
    Valida um único link de produto ML.

    Suporta dois tipos de URL:
      - Página de catálogo (/p/MLB...): vai direto para listings do catálogo
      - Página de item  (/MLB...):  busca /items/{id} primeiro, depois catálogo

    Fluxo (item):
      1. detect_url_type → ('item', item_id)
      2. GET /items/{id} → price + catalog_product_id
      3. GET /sites/MLB/search?catalog_product_id=... → listings
      4. Encontra o mais barato e compara

    Fluxo (catalog):
      1. detect_url_type → ('catalog', catalog_id)
      2. GET /sites/MLB/search?catalog_product_id=... → listings
      3. Retorna o mais barato (sem preço "atual" para comparar)
    """
    result = ValidationResult(original_link=url)

    # STEP 1 — Classifica URL
    url_type, id_found = detect_url_type(url)

    if url_type == "unknown" or id_found is None:
        result.error = "Não foi possível extrair MLB ID da URL"
        logger.warning(f"[{url}] {result.error}")
        return result

    # ── Fluxo: página de CATÁLOGO ─────────────────────────────────────────────
    if url_type == "catalog":
        catalog_product_id = id_found
        result.item_id = catalog_product_id
        result.catalog_product_id = catalog_product_id
        logger.info(f"URL de catálogo detectada: {catalog_product_id}")

        raw_listings = get_catalog_listings(catalog_product_id)
        all_listings = parse_catalog_listings(raw_listings)
        result.total_listings = len(all_listings)

        if not all_listings:
            result.error = f"Nenhum listing encontrado para o catálogo {catalog_product_id}"
            return result

        cheapest = find_cheapest(all_listings)
        if cheapest:
            result.is_cheapest = None   # N/A — sem item de referência
            result.cheapest_price = cheapest.real_price
            result.cheapest_free_shipping = cheapest.free_shipping
            permalink = _resolve_permalink(cheapest, catalog_product_id)
            result.cheapest_link = permalink
            result.affiliate_link = generate_affiliate_link(permalink) if permalink else None
            logger.info(
                f"[{catalog_product_id}] Mais barato no catálogo: R$ {cheapest.real_price:.2f} "
                f"→ {permalink}"
            )
        return result

    # ── Fluxo: página de ITEM ─────────────────────────────────────────────────
    item_id = id_found
    result.item_id = item_id

    # STEP 2 — Busca dados do item
    item_data = get_item(item_id)
    if not item_data:
        result.error = f"Item {item_id} não encontrado na API do ML"
        logger.error(f"[{item_id}] {result.error}")
        return result

    original_listing = listing_from_api(item_data)
    if not original_listing:
        result.error = f"Dados insuficientes para o item {item_id}"
        return result

    result.current_price = original_listing.real_price
    result.free_shipping = original_listing.free_shipping

    # STEP 3 — Obtém catalog_product_id
    catalog_product_id = item_data.get("catalog_product_id")
    result.catalog_product_id = catalog_product_id

    if not catalog_product_id:
        # Sem catálogo: produto único, por definição é o mais barato disponível
        logger.info(f"[{item_id}] Sem catalog_product_id — assumindo único vendedor")
        result.is_cheapest = True
        result.total_listings = 1
        return result

    # STEP 4 — Busca todos os listings do catálogo
    raw_listings = get_catalog_listings(catalog_product_id)
    all_listings = parse_catalog_listings(raw_listings)
    result.total_listings = len(all_listings)

    if not all_listings:
        logger.warning(f"[{item_id}] Catálogo {catalog_product_id} retornou 0 listings")
        result.is_cheapest = True   # fallback conservador
        return result

    # STEP 5 — Encontra o mais barato
    cheapest = find_cheapest(all_listings)
    if not cheapest:
        result.is_cheapest = True
        return result

    result.cheapest_price = cheapest.real_price
    result.cheapest_free_shipping = cheapest.free_shipping

    # STEP 6 — Compara
    is_cheapest = (cheapest.item_id == item_id) or (cheapest.real_price >= original_listing.real_price)
    result.is_cheapest = is_cheapest

    if not is_cheapest:
        permalink = _resolve_permalink(cheapest, catalog_product_id or "")
        result.cheapest_link = permalink
        result.affiliate_link = generate_affiliate_link(permalink) if permalink else None
        result.price_difference = round(original_listing.real_price - cheapest.real_price, 2)
        logger.info(
            f"[{item_id}] Existe opção mais barata: R$ {cheapest.real_price:.2f} "
            f"vs R$ {original_listing.real_price:.2f} (diff: R$ {result.price_difference:.2f}) "
            f"→ {permalink}"
        )
    else:
        logger.info(f"[{item_id}] Já é o mais barato: R$ {original_listing.real_price:.2f}")

    return result


def validate_links(urls: List[str], max_workers: int = 6) -> List[ValidationResult]:
    """
    Valida uma lista de URLs em paralelo.

    Args:
        urls: lista de links de produtos ML
        max_workers: threads paralelas (default 6 — respeita rate limit da API)

    Returns:
        Lista de ValidationResult na mesma ordem dos inputs
    """
    if not urls:
        return []

    results_map: Dict[str, ValidationResult] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(validate_single, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results_map[url] = future.result()
            except Exception as e:
                logger.error(f"Exceção ao validar {url}: {e}")
                results_map[url] = ValidationResult(original_link=url, error=str(e))

    # Mantém a ordem original
    return [results_map[url] for url in urls]
