"""
affiliate.py
Gerador de links de afiliado do Mercado Livre.

Uso:
    from scripts.price_validator.affiliate import generate_affiliate_link

    link = generate_affiliate_link("https://produto.mercadolivre.com.br/MLB123456789")
    # → "https://produto.mercadolivre.com.br/MLB123456789?matt_tool=12345678"

Configuração (ENV):
    MERCADO_LIVRE_AFFILIATE_ID   — ID do programa de afiliados ML
    ML_UTM_SOURCE                — opcional, padrão: "affiliate"
    ML_UTM_MEDIUM                — opcional, padrão: "link"
    ML_UTM_CAMPAIGN              — opcional, deixa vazio por padrão

Segue princípios SOLID:
    S — responsabilidade única: só gera/anexa parâmetros de afiliado
    O — aberto para extensão via utm params sem alterar a função core
    L — não viola contratos de substituição
    I — interface mínima e coesa
    D — recebe affiliate_id como parâmetro, lê ENV como fallback (injeção implícita)
"""

import os
import logging
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

logger = logging.getLogger(__name__)

# ─── Constantes de ENV ────────────────────────────────────────────────────────
_AFFILIATE_ID_ENV  = "MERCADO_LIVRE_AFFILIATE_ID"
_UTM_SOURCE_ENV    = "ML_UTM_SOURCE"
_UTM_MEDIUM_ENV    = "ML_UTM_MEDIUM"
_UTM_CAMPAIGN_ENV  = "ML_UTM_CAMPAIGN"

_DEFAULT_UTM_SOURCE = "affiliate"
_DEFAULT_UTM_MEDIUM = "link"


# ─── API pública ──────────────────────────────────────────────────────────────

def get_affiliate_id() -> str | None:
    """
    Lê o ID de afiliado do Mercado Livre da variável de ambiente
    ``MERCADO_LIVRE_AFFILIATE_ID``.

    Returns:
        String com o ID ou None se não configurado.
    """
    return os.environ.get(_AFFILIATE_ID_ENV) or None


def generate_affiliate_link(
    permalink: str,
    affiliate_id: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
) -> str:
    """
    Gera um link de afiliado do Mercado Livre a partir de qualquer permalink.

    O parâmetro ``matt_tool`` é o identificador do programa de afiliados ML.
    Detecta automaticamente se a URL já contém query-string para usar ``&`` ou ``?``.

    Args:
        permalink:    URL do produto (ex: https://produto.mercadolivre.com.br/MLB123)
        affiliate_id: ID de afiliado. Se None, usa ENV ``MERCADO_LIVRE_AFFILIATE_ID``.
        utm_source:   UTM source. Se None, usa ENV ``ML_UTM_SOURCE`` ou "affiliate".
        utm_medium:   UTM medium. Se None, usa ENV ``ML_UTM_MEDIUM`` ou "link".
        utm_campaign: UTM campaign. Se None, usa ENV ``ML_UTM_CAMPAIGN`` (pode ser "").

    Returns:
        URL com parâmetros de afiliado anexados.
        Se não houver affiliate_id configurado, retorna o permalink original e loga warning.

    Raises:
        ValueError: Se permalink estiver vazio.
    """
    if not permalink or not permalink.strip():
        raise ValueError("permalink não pode ser vazio")

    permalink = permalink.strip()

    # Resolve affiliate_id
    resolved_id = affiliate_id or get_affiliate_id()
    if not resolved_id:
        logger.warning(
            "MERCADO_LIVRE_AFFILIATE_ID não configurado — retornando permalink sem afiliado. "
            f"Permalink: {permalink}"
        )
        return permalink

    # Resolve UTM params (todos opcionais)
    source   = utm_source   or os.environ.get(_UTM_SOURCE_ENV)   or _DEFAULT_UTM_SOURCE
    medium   = utm_medium   or os.environ.get(_UTM_MEDIUM_ENV)   or _DEFAULT_UTM_MEDIUM
    campaign = utm_campaign if utm_campaign is not None else os.environ.get(_UTM_CAMPAIGN_ENV, "")

    # Constrói parâmetros extras na ordem correta
    extra_params: dict[str, str] = {"matt_tool": resolved_id}
    if source:
        extra_params["utm_source"] = source
    if medium:
        extra_params["utm_medium"] = medium
    if campaign:
        extra_params["utm_campaign"] = campaign

    result = _append_query_params(permalink, extra_params)
    logger.debug(f"Affiliate link gerado: {permalink!r} → {result!r}")
    return result


def strip_affiliate_params(url: str) -> str:
    """
    Remove parâmetros de afiliado e UTM de uma URL.
    Útil para comparações e deduplicação.

    Args:
        url: URL possivelmente com parâmetros de afiliado

    Returns:
        URL limpa sem matt_tool / utm_* params
    """
    _AFFILIATE_PARAMS = {"matt_tool", "utm_source", "utm_medium", "utm_campaign"}
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    clean_qs = {k: v for k, v in qs.items() if k not in _AFFILIATE_PARAMS}
    new_query = urlencode(clean_qs, doseq=True)
    clean = parsed._replace(query=new_query)
    return urlunparse(clean)


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _append_query_params(url: str, params: dict[str, str]) -> str:
    """
    Anexa parâmetros a uma URL existente, respeitando query-string já presente.
    Não duplica parâmetros que já existam.

    Args:
        url:    URL base
        params: dict de parâmetros a adicionar

    Returns:
        URL com novos parâmetros
    """
    parsed = urlparse(url)
    existing_qs = parse_qs(parsed.query, keep_blank_values=True)

    # Não sobrescreve parâmetros que já existam (ex: affiliate já no link)
    merged: dict[str, list[str]] = {**existing_qs}
    for key, value in params.items():
        if key not in merged:
            merged[key] = [value]

    new_query = urlencode(merged, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)
