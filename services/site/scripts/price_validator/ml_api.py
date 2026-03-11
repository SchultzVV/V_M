"""
ml_api.py
Cliente para a API pública do Mercado Livre com cache Redis.

Endpoints usados:
  GET /items/{item_id}                                         → dados do item
  GET /products/{catalog_id}/items                            → todos os vendedores do catálogo
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
        resp = _get_with_fallback(url)
        resp.raise_for_status()
        data = resp.json()
        _cache_set(cache_key, data)
        return data
    except requests.HTTPError as e:
        status = e.response.status_code
        # 404 = catalog ID passado como item ID (fallback esperado)
        # 403 = PolicyAgent bloqueia item de terceiro (fallback esperado)
        lvl = logger.debug if status in (404, 403) else logger.error
        lvl(f"[item {item_id}] HTTP {status} — {e.response.text[:120]}")
        return None
    except requests.RequestException as e:
        logger.error(f"Erro de rede ao buscar item {item_id}: {e}")
        return None


def _get_with_fallback(url: str) -> Optional[requests.Response]:
    """
    Faz GET com auth; se retornar 403 (token expirado/inválido),
    tenta novamente sem Authorization header (endpoint público).
    """
    resp = requests.get(url, headers=_get_auth_headers(), timeout=_REQUEST_TIMEOUT)
    if resp.status_code == 403:
        logger.debug(f"403 com auth em {url} — retentando sem token (endpoint público)")
        resp = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    return resp


def get_catalog_listings(catalog_product_id: str) -> List[Dict[str, Any]]:
    """
    Retorna todos os vendedores ativos do mesmo produto no catálogo ML.

    Usa GET /products/{catalog_product_id}/items — endpoint público que lista
    todos os itens do catálogo, ordenados por preço ascendente.
    (O endpoint /sites/MLB/search?catalog_product_id= requer nível Partner — 403)

    Normaliza cada resultado para compatibilidade com listing_from_api():
      - Adiciona "id"        = item["item_id"]
      - Adiciona "permalink" = "" (será buscado sob demanda pelo caller se necessário)
    """
    cache_key = f"pv:catalog:{catalog_product_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Cache HIT para catálogo {catalog_product_id}")
        return cached

    url = f"{_API_BASE}/products/{catalog_product_id}/items"
    try:
        resp = _get_with_fallback(url)
        resp.raise_for_status()
        data = resp.json()
        raw_results = data.get("results", [])

        # Normaliza campos para compatibilidade com listing_from_api
        results = []
        for item in raw_results:
            normalized = dict(item)
            normalized["id"] = item.get("item_id", "")
            if "permalink" not in normalized:
                normalized["permalink"] = ""   # será buscado sob demanda
            results.append(normalized)

    except requests.HTTPError as e:
        logger.error(f"HTTPError ao buscar catálogo {catalog_product_id}: {e.response.status_code} {e.response.text[:200]}")
        results = []
    except requests.RequestException as e:
        logger.error(f"Erro de rede ao buscar catálogo {catalog_product_id}: {e}")
        results = []

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
