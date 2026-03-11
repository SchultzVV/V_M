"""
routes/price_validator_routes.py
Endpoint HTTP para o serviço de validação de preço.

POST /validate-prices
  Body: {"links": ["https://...", "https://..."]}
  Response: lista de ValidationResult + resumo
"""

import logging
from flask import Blueprint, request, jsonify

from scripts.price_validator.validator import validate_links

logger = logging.getLogger(__name__)

price_validator_bp = Blueprint("price_validator", __name__)


@price_validator_bp.route("/validate-prices", methods=["POST"])
def validate_prices():
    """
    Verifica se os links fornecidos são os mais baratos para o produto no catálogo ML.

    Body JSON:
        {
          "links": ["url1", "url2", ...],
          "workers": 6   // opcional — threads paralelas
        }

    Returns 200:
        {
          "total": N,
          "summary": { "cheapest": X, "has_cheaper": Y, "errors": Z },
          "results": [ ... ]
        }
    """
    body = request.get_json(silent=True) or {}
    links = body.get("links", [])
    workers = int(body.get("workers", 6))

    if not links:
        return jsonify({"error": "Campo 'links' é obrigatório e não pode estar vazio."}), 400

    if not isinstance(links, list):
        return jsonify({"error": "'links' deve ser uma lista de strings."}), 400

    if len(links) > 100:
        return jsonify({"error": "Máximo de 100 links por requisição."}), 400

    logger.info(f"[validate-prices] Validando {len(links)} link(s)")

    try:
        results = validate_links(links, max_workers=workers)
    except Exception as e:
        logger.exception("Erro inesperado em validate_links")
        return jsonify({"error": str(e)}), 500

    serialized = [r.to_dict() for r in results]

    summary = {
        "cheapest":    sum(1 for r in results if r.is_cheapest is True),
        "has_cheaper": sum(1 for r in results if r.is_cheapest is False),
        "errors":      sum(1 for r in results if r.error),
    }

    return jsonify({
        "total": len(results),
        "summary": summary,
        "results": serialized,
    }), 200


@price_validator_bp.route("/validate-prices/health", methods=["GET"])
def health():
    """Healthcheck simples do serviço."""
    return jsonify({"status": "ok", "service": "price_validator"}), 200
