"""
ml_api.py
Cliente para a API pública do Mercado Livre com cache Redis.

Endpoints usados:
  GET /items/{item_id}                                         → dados do item
  GET /sites/MLB/search?catalog_product_id={id}&limit=50      → todos os vendedores
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import redis

logger = logging.getLogger(__name__)

# ─── URLs base ────────────────────────────────────────────────────────────────
_API_BASE = "https://api.mercadolibre.com"
_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL_SECONDS", 300))   # 5 min padrão
_REQUEST_TIMEOUT = 10  # segundos

# ─── Headers padrão ───────────────────────────────────────────────────────────
_HEADERS = {"User-Agent": "V_M-price-validator/1.0"}


# ─── Conexão Redis ────────────────────────────────────────────────────────────
def _get_redis() -> Optional[redis.Redis]:
    """Retorna conexão Redis ou None se indisponível (graceful fallback)."""
    try:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        client = redis.Redis.from_url(url, socket_connect_timeout=2, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.warning("Redis indisponível — cache desativado para esta execução")
        return None


_redis: Optional[redis.Redis] = _get_redis()


# ─── Helpers de cache ─────────────────────────────────────────────────────────
def _cache_get(key: str) -> Optional[Dict]:
    if _redis is None:
        return None
    try:
        raw = _redis.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: Dict) -> None:
    if _redis is None:
        return
    try:
        _redis.setex(key, _CACHE_TTL, json.dumps(value, ensure_ascii=False))
    except Exception:
        pass


# ─── Auth token (opcional, melhora rate-limit) ────────────────────────────────
def _get_auth_headers() -> Dict[str, str]:
    """Tenta injetar o Bearer token do OAuth ML se disponível."""
    headers = dict(_HEADERS)
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.ml_auth import ml_auth
        token = ml_auth.get_valid_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass
    return headers


# ─── API calls ────────────────────────────────────────────────────────────────
def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Busca dados de um item pelo ID.
    Campos relevantes: id, price, original_price, catalog_product_id,
                       permalink, shipping.free_shipping, status.
    """
    cache_key = f"pv:item:{item_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Cache HIT para item {item_id}")
        return cached

    url = f"{_API_BASE}/items/{item_id}"
    try:
        resp = requests.get(url, headers=_get_auth_headers(), timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        _cache_set(cache_key, data)
        return data
    except requests.HTTPError as e:
        logger.error(f"HTTPError ao buscar item {item_id}: {e.response.status_code} {e.response.text[:200]}")
        return None
    except requests.RequestException as e:
        logger.error(f"Erro de rede ao buscar item {item_id}: {e}")
        return None


def get_catalog_listings(catalog_product_id: str) -> List[Dict[str, Any]]:
    """
    Retorna todos os vendedores ativos do mesmo produto no catálogo ML.

    Usa /sites/MLB/search?catalog_product_id=... com paginação (max 50 p/ request).
    Concatena até 3 páginas (150 itens — suficiente para encontrar o mais barato).
    """
    cache_key = f"pv:catalog:{catalog_product_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Cache HIT para catálogo {catalog_product_id}")
        return cached

    results: List[Dict] = []
    limit = 50
    max_pages = 3

    for page in range(max_pages):
        offset = page * limit
        url = (
            f"{_API_BASE}/sites/MLB/search"
            f"?catalog_product_id={catalog_product_id}"
            f"&limit={limit}&offset={offset}"
        )
        try:
            resp = requests.get(url, headers=_get_auth_headers(), timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            page_results = data.get("results", [])
            results.extend(page_results)
            if len(page_results) < limit:
                break  # última página
        except requests.RequestException as e:
            logger.error(f"Erro ao buscar catálogo {catalog_product_id} offset={offset}: {e}")
            break

    if results:
        _cache_set(cache_key, results)

    return results


def get_items_batch(item_ids: List[str], max_workers: int = 8) -> Dict[str, Optional[Dict]]:
    """
    Busca múltiplos itens em paralelo usando ThreadPoolExecutor.

    Returns:
        Dict {item_id: item_data_or_None}
    """
    results: Dict[str, Optional[Dict]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(get_item, iid): iid for iid in item_ids}
        for future in as_completed(future_to_id):
            iid = future_to_id[future]
            try:
                results[iid] = future.result()
            except Exception as e:
                logger.error(f"Falha ao buscar {iid}: {e}")
                results[iid] = None

    return results
