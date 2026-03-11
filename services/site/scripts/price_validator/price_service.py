"""
price_service.py
Calcula preço real (price + frete estimado) e encontra o listing mais barato
entre todos os vendedores de um mesmo produto no catálogo ML.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Custo de frete padrão quando o frete NÃO é grátis e não sabemos o valor exato.
# Usamos um valor simbólico para "penalizar" lisatings sem frete grátis no ranking.
# Em produção isso poderia ser calculado via /items/{id}/shipping_options.
_DEFAULT_SHIPPING_COST = 0.0   # conservador: só usamos price para comparar


@dataclass
class Listing:
    """Representa um listing (produto + vendedor) no ML."""
    item_id: str
    price: float
    free_shipping: bool
    permalink: str
    seller_id: Optional[int] = None
    status: str = "active"

    @property
    def real_price(self) -> float:
        """
        Preço real = price + custo de frete.
        Quando frete grátis: shipping_cost = 0.
        Quando não grátis: usamos _DEFAULT_SHIPPING_COST (0 por padrão —
        assim comparamos apenas pelo preço base e bonus do frete grátis é
        sinalizado mas não distorce o ranking).
        """
        shipping_cost = 0.0 if self.free_shipping else _DEFAULT_SHIPPING_COST
        return round(self.price + shipping_cost, 2)

    @property
    def is_active(self) -> bool:
        return self.status == "active"


def listing_from_api(data: Dict[str, Any]) -> Optional[Listing]:
    """
    Constrói um Listing a partir do JSON da API do ML.
    Retorna None se os dados essenciais (price, permalink) estiverem ausentes.
    """
    try:
        price = data.get("price") or data.get("sale_price")
        permalink = data.get("permalink") or data.get("catalog_url")
        item_id = data.get("id", "")

        if price is None or not permalink or not item_id:
            return None

        shipping = data.get("shipping") or {}
        free_shipping = bool(shipping.get("free_shipping", False))
        status = data.get("status", "active")
        seller_id = data.get("seller_id") or (data.get("seller") or {}).get("id")

        return Listing(
            item_id=item_id,
            price=float(price),
            free_shipping=free_shipping,
            permalink=permalink,
            seller_id=seller_id,
            status=status,
        )
    except (TypeError, ValueError) as e:
        logger.debug(f"Erro ao construir Listing de {data.get('id', '?')}: {e}")
        return None


def find_cheapest(listings: List[Listing]) -> Optional[Listing]:
    """
    Retorna o listing com menor real_price entre os ativos.
    Em caso de empate no preço, prioriza frete grátis.
    """
    active = [l for l in listings if l.is_active]
    if not active:
        return None

    return min(
        active,
        key=lambda l: (l.real_price, not l.free_shipping),  # (preço, sem_frete_grátis)
    )


def parse_catalog_listings(api_results: List[Dict[str, Any]]) -> List[Listing]:
    """Converte a lista bruta da API em objetos Listing, filtrando inválidos."""
    listings = []
    for raw in api_results:
        listing = listing_from_api(raw)
        if listing:
            listings.append(listing)
    return listings
