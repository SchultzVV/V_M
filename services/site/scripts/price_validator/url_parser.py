"""
url_parser.py
Extrai o ID do item (MLB\d+) ou catalog_product_id de qualquer link do ML.
Suporta links diretos, links de afiliado e links curtos.
"""

import re
import logging
from typing import Optional, Tuple
import requests

logger = logging.getLogger(__name__)

_MLB_PATTERN = re.compile(r"(MLB-?\d+)", re.IGNORECASE)
_CATALOG_PAGE_PATTERN = re.compile(r"/p/(MLB\d+)", re.IGNORECASE)


def extract_item_id(url: str) -> Optional[str]:
    """
    Extrai o ID MLB de uma URL do Mercado Livre.
    Se não encontrar, resolve redirects e tenta novamente.

    Returns:
        ID no formato 'MLB123456789' ou None
    """
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    item_id = _extract_from_string(url)
    if item_id:
        return item_id

    try:
        response = requests.head(url, allow_redirects=True, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0"})
        final_url = response.url
        item_id = _extract_from_string(final_url)
        if item_id:
            logger.debug(f"ID extraído após redirect: {url} → {final_url}")
            return item_id
    except requests.RequestException as e:
        logger.warning(f"Falha ao resolver redirect para {url}: {e}")

    logger.warning(f"Não foi possível extrair MLB ID de: {url}")
    return None


def detect_url_type(url: str) -> Tuple[str, Optional[str]]:
    """
    Detecta o tipo de URL do ML e retorna (tipo, id).

    Tipos:
      - 'catalog'  → URL de página de catálogo (/p/MLB...)
                     o ID é o catalog_product_id — vai direto para search
      - 'item'     → URL de item direto (MLB...)
                     o ID é o item_id — precisa chamar /items/{id} primeiro

    Returns:
        ('catalog', catalog_id) | ('item', item_id) | ('unknown', None)
    """
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    # Checa antes de resolver redirect
    t, id_ = _classify_string(url)
    if t != "unknown":
        return t, id_

    # Resolve redirect
    try:
        response = requests.head(url, allow_redirects=True, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0"})
        return _classify_string(response.url)
    except requests.RequestException:
        pass

    return "unknown", None


def _classify_string(url: str) -> Tuple[str, Optional[str]]:
    """Classifica uma URL já resolvida."""
    catalog_match = _CATALOG_PAGE_PATTERN.search(url)
    if catalog_match:
        return "catalog", catalog_match.group(1).upper()

    item_id = _extract_from_string(url)
    if item_id:
        return "item", item_id

    return "unknown", None


def _extract_from_string(text: str) -> Optional[str]:
    match = _MLB_PATTERN.search(text)
    if match:
        return match.group(1).upper().replace("-", "")
    return None


def normalize_item_id(item_id: str) -> str:
    return item_id.upper().replace("-", "")
