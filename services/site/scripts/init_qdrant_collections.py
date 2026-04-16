#!/usr/bin/env python3
"""
init_qdrant_collections.py
Cria as 4 coleções padrão do projeto no Qdrant.
Seguro de executar múltiplas vezes — ignora coleções já existentes.

Coleções criadas:
  - agent_rules      : regras e prompt templates dos agentes
  - price_history    : histórico de preços por produto (ML)
  - product_catalog  : dados enriquecidos de produtos
  - site_knowledge   : regras de negócio do site
"""
import os
import sys
import logging

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Dimensão dos embeddings depende do provider
_LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()
_EMBED_DIM = 768 if _LLM_PROVIDER == "ollama" else 1536  # nomic-embed-text=768, text-embedding-3-small=1536

COLLECTIONS = {
    "agent_rules": {
        "description": "Regras e prompt templates dos agentes",
        "dim": _EMBED_DIM,
    },
    "price_history": {
        "description": "Histórico de preços por produto ML",
        "dim": 1,  # vetor escalar com o preço; buscas por payload filter
    },
    "product_catalog": {
        "description": "Dados enriquecidos de produtos",
        "dim": _EMBED_DIM,
    },
    "site_knowledge": {
        "description": "Regras de negócio e conhecimento do site",
        "dim": _EMBED_DIM,
    },
}


def main():
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", 6333))

    log.info("Conectando ao Qdrant em %s:%s …", host, port)
    client = QdrantClient(host=host, port=port)

    existing = {c.name for c in client.get_collections().collections}
    log.info("Coleções existentes: %s", existing or "(nenhuma)")

    created = []
    skipped = []

    for name, cfg in COLLECTIONS.items():
        if name in existing:
            log.info("  ⏭  %-20s já existe — ignorado", name)
            skipped.append(name)
            continue

        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=cfg["dim"],
                distance=Distance.COSINE,
            ),
        )
        log.info("  ✅  %-20s criado   (%s)", name, cfg["description"])
        created.append(name)

    log.info("")
    log.info("Resultado: %d criadas, %d já existiam.", len(created), len(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
