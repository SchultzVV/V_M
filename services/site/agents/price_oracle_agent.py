"""
Price Oracle Agent
Consolida até 4 fontes de preço (ML API, Catálogo ML, DOM/Pix, histórico Qdrant)
e decide preço atual + desconto real via hsmart retrieval_service (Ollama).
Persiste resultado em Qdrant (coleção price_history).

LLM: chamada HTTP para http://retrieval_service:5004/query
     (ou HSMART_RETRIEVAL_URL no .env)
"""
import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import re
import redis

logger = logging.getLogger(__name__)

# URL do serviço hsmart — dentro do docker usa nome do container; CLI usa localhost
_HSMART_URL = os.environ.get("HSMART_RETRIEVAL_URL", os.environ.get("HSMART_URL", "http://hsmart:5005"))
_QDRANT_URL  = os.environ.get("QDRANT_URL",            "http://vector_db:6333")

# Adiciona scripts/ ao path para importar módulos de scraping
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

_MLB_RE = re.compile(r'(MLB-?\d{6,})', re.IGNORECASE)


def resolve_ml_id_from_link(link: str) -> Optional[str]:
    """
    Extrai o MLB ID a partir de qualquer forma de link ML:
      - URL direta: https://www.mercadolivre.com.br/.../MLB-123456789-...
      - Link curto: https://meli.la/2JEg3hQ  → segue redirects → extrai MLB
      - Página de perfil/social: extrai MLB do HTML (og:url, canonical, hrefs)
      - Já é um MLB ID: retorna como está

    Retorna o MLB ID normalizado (sem hífen: MLB123456789) ou None.
    """
    # Já é um ML ID
    if _MLB_RE.fullmatch(link.strip()):
        return link.strip().replace("-", "").upper()

    # Tenta extrair direto da URL (sem request)
    m = _MLB_RE.search(link)
    if m:
        return m.group(1).replace("-", "").upper()

    # Precisa seguir redirect (link curto tipo meli.la)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PriceOracle/1.0)"}
    try:
        resp = requests.get(link, headers=headers, timeout=15, allow_redirects=True)
        final_url = resp.url
        logger.info("🔗 %s → %s", link, final_url)

        # MLB na URL final
        m = _MLB_RE.search(final_url)
        if m:
            return m.group(1).replace("-", "").upper()

        # Página de perfil/social — extrai do HTML via auto_prepare_ml helpers
        if "/social/" in final_url or "/perfil/" in final_url or "matt_tool" in final_url:
            try:
                from auto_prepare_ml import _extract_product_url_from_html, extract_ml_product_id  # type: ignore
                product_url = _extract_product_url_from_html(resp.text)
                if product_url:
                    pid = extract_ml_product_id(product_url)
                    if pid:
                        return pid.replace("-", "").upper()
            except ImportError:
                pass

        # Fallback: busca MLB no HTML completo
        m = _MLB_RE.search(resp.text)
        if m:
            return m.group(1).replace("-", "").upper()

    except Exception as exc:
        logger.error("Erro ao resolver link %s: %s", link, exc)

    return None


class PriceOracleAgent:
    """
    Agente que obtém e valida preços de produtos ML.

    Fontes consultadas (em ordem de confiabilidade):
      1. ML Catalog API  — preço de catálogo (mais confiável)
      2. ML Item API     — preço do listing do vendedor
      3. DOM / Pix       — preço extraído por Playwright da página ML
      4. Qdrant history  — últimas medições salvas localmente

    O LLM decide qual preço exibir e qual tratar como "de" (riscado).
    O resultado é persistido no Qdrant para uso futuro.
    """

    COLLECTION = "price_history"

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._memory_key = "agent:price_oracle:memory"

    # ------------------------------------------------------------------
    # Ponto de entrada principal
    # ------------------------------------------------------------------

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parâmetros esperados em input_data:
          - product_id   : str   — ID interno / slug do banco (opcional se ml_id único)
          - ml_id        : str   — ID ML (ex: MLB123) — obrigatório
          - title        : str   — Título do produto
          - current_price: float — Preço atualmente no banco
          - dry_run      : bool  — Se True: não escreve no banco nem no Qdrant
          - publish      : bool  — Se True (default): publica price+old_price no banco
        """
        product_id    = input_data.get("product_id", "")
        ml_id         = input_data.get("ml_id", "")
        title         = input_data.get("title", ml_id)
        current_price = float(input_data.get("current_price", 0.0))
        dry_run       = input_data.get("dry_run", False)
        publish       = input_data.get("publish", True)  # publica por default

        if not ml_id:
            return {"success": False, "error": "ml_id obrigatório"}

        # 1. Coleta dados das fontes disponíveis
        sources = self._collect_sources(ml_id, current_price)

        # 2. LLM (hsmart) decide price_current / price_original
        decision = self._ask_hsmart(title, ml_id, sources)

        result = {
            "success":    True,
            "product_id": product_id,
            "ml_id":      ml_id,
            "title":      title,
            "sources":    sources,
            "decision":   decision,
            "published":  False,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }

        if not dry_run:
            # 3. Persiste decisão no Qdrant price_history
            self._persist(result)

            # 4. Tool: publica direto no banco do site
            if publish:
                pub = self._publish_to_site(ml_id, decision)
                result["published"]      = pub.get("success", False)
                result["publish_detail"] = pub

        # 5. Salva na memória Redis
        if self._redis:
            self._save_to_memory(result)

        return result

    # ------------------------------------------------------------------
    # Tool: publica preço direto no banco do site
    # ------------------------------------------------------------------

    def _publish_to_site(self, ml_id: str, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza price + old_price + desconto + updated_at no banco via SQLAlchemy.
        Busca o produto por external_id = ml_id.
        Retorna {"success": bool, "changed": bool, "detail": str}.
        """
        price_current  = decision.get("price_current")
        price_original = decision.get("price_original")

        if not price_current:
            return {"success": False, "changed": False, "detail": "price_current ausente na decisão LLM"}

        try:
            from database import SessionLocal
            from models.product import Product
            from scripts.price_validator.affiliate import generate_affiliate_link
        except ImportError as exc:
            return {"success": False, "changed": False, "detail": f"Import falhou (fora do container?): {exc}"}

        session = SessionLocal()
        try:
            product = session.query(Product).filter(
                Product.external_id == ml_id
            ).first()

            if not product:
                return {"success": False, "changed": False, "detail": f"Produto {ml_id} não encontrado no banco"}

            old_price_val  = float(price_original or price_current)
            new_price_val  = float(price_current)
            desconto       = round((old_price_val - new_price_val) / old_price_val * 100) if old_price_val > new_price_val else 0

            prev_price = product.price

            product.price      = f"R$ {new_price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            product.old_price  = f"R$ {old_price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if desconto > 0 else ""
            product.desconto   = float(desconto)
            product.updated_at = datetime.now(timezone.utc)

            session.commit()
            logger.info("✅ [publish] %s → R$ %.2f (de R$ %.2f, %d%% off)", ml_id, new_price_val, old_price_val, desconto)

            return {
                "success":    True,
                "changed":    True,
                "ml_id":      ml_id,
                "prev_price": prev_price,
                "new_price":  product.price,
                "old_price":  product.old_price,
                "desconto":   desconto,
            }

        except Exception as exc:
            session.rollback()
            logger.error("Erro ao publicar preço para %s: %s", ml_id, exc)
            return {"success": False, "changed": False, "detail": str(exc)}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Coleta de fontes
    # ------------------------------------------------------------------

    def _collect_sources(self, ml_id: str, current_price: float) -> Dict[str, Any]:
        sources: Dict[str, Any] = {"current_db": current_price}

        # Fonte 1 + 2: ML API (item + catalog cheapest) via _fetch_api_info
        try:
            import sys, os as _os
            _scripts = _os.path.join(_os.path.dirname(__file__), "..", "scripts")
            if _scripts not in sys.path:
                sys.path.insert(0, _scripts)
            from update_ml_prices_right import _fetch_api_info  # type: ignore
            api_info = _fetch_api_info(ml_id)
            if api_info:
                if api_info.get("api_price"):
                    sources["item_api_price"] = float(api_info["api_price"])
                if api_info.get("original_price"):
                    sources["item_api_original"] = float(api_info["original_price"])
                if api_info.get("cheapest_price"):
                    sources["catalog_api"] = float(api_info["cheapest_price"])
                    sources["catalog_free_shipping"] = api_info.get("cheapest_free_shipping", False)
                if api_info.get("title") and not sources.get("title"):
                    sources["title"] = api_info["title"]
        except Exception as exc:
            logger.warning("item/catalog API falhou para %s: %s", ml_id, exc)

        # Fonte 3: DOM / Pix via Playwright (opcional — lento, sem browser por default)
        if os.environ.get("PRICE_ORACLE_USE_BROWSER", "0") == "1":
            try:
                from update_ml_prices_right import _extract_price_from_page  # type: ignore
                from playwright.sync_api import sync_playwright

                url = f"https://www.mercadolivre.com.br/p/{ml_id}"
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, timeout=20_000)
                    dom_prices = _extract_price_from_page(page)
                    browser.close()
                sources["dom"] = dom_prices
            except Exception as exc:
                logger.warning("Playwright falhou para %s: %s", ml_id, exc)

        # Fonte 4: histórico Qdrant (via REST)
        try:
            history = self._get_recent_history(ml_id, limit=3)
            if history:
                sources["qdrant_history"] = history
        except Exception as exc:
            logger.warning("Qdrant history falhou para %s: %s", ml_id, exc)

        return sources

    # ------------------------------------------------------------------
    # Chama hsmart /query
    # ------------------------------------------------------------------

    def _ask_hsmart(self, title: str, ml_id: str, sources: Dict[str, Any]) -> Dict[str, Any]:
        question = (
            f"Você é um oráculo de preços para um site de afiliados do Mercado Livre.\n"
            f"Produto: {title} (ID: {ml_id})\n"
            f"Fontes de preço coletadas:\n"
            f"{json.dumps(sources, ensure_ascii=False, indent=2)}\n\n"
            f"Regra: se preço DOM >= 1.5x preço da API, trate o DOM como preço original (riscado).\n"
            f"Responda APENAS com JSON válido (sem markdown) com os campos:\n"
            f"  price_current (float), price_original (float ou null), confidence (baixa/media/alta), reasoning (1 frase)"
        )

        try:
            resp = requests.post(
                f"{_HSMART_URL}/query",
                json={"question": question},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            raw  = data.get("result") or data.get("response") or data.get("answer") or str(data)
        except Exception as exc:
            logger.error("hsmart /query falhou: %s", exc)
            return self._fallback_decision(sources)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning("hsmart retornou JSON inválido, usando fallback. Raw: %s", raw[:120])
            return self._fallback_decision(sources, raw)

    def _fallback_decision(self, sources: Dict[str, Any], raw: str = "") -> Dict[str, Any]:
        best = (
            sources.get("catalog_api")
            or sources.get("item_api_price")
            or sources.get("current_db")
        )
        return {
            "price_current":  best,
            "price_original": None,
            "confidence":     "baixa",
            "reasoning":      f"Fallback automático.{(' Raw: ' + raw[:80]) if raw else ''}",
        }

    # ------------------------------------------------------------------
    # Qdrant REST: persistência e histórico
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Cria a collection price_history no Qdrant se ainda não existir."""
        try:
            r = requests.get(f"{_QDRANT_URL}/collections/{self.COLLECTION}", timeout=5)
            if r.status_code == 404:
                requests.put(
                    f"{_QDRANT_URL}/collections/{self.COLLECTION}",
                    json={"vectors": {"size": 1, "distance": "Cosine"}},
                    timeout=10,
                ).raise_for_status()
                logger.info("✅ collection %s criada no Qdrant", self.COLLECTION)
        except Exception as exc:
            logger.warning("Não foi possível garantir collection Qdrant: %s", exc)

    def _persist(self, result: Dict[str, Any]) -> None:
        self._ensure_collection()
        try:
            doc_id    = abs(hash(f"{result['ml_id']}:{result['timestamp']}")) % (2**31)
            price_val = float(result["decision"].get("price_current") or 0.0)
            body = {
                "points": [{
                    "id":     doc_id,
                    "vector": [price_val],
                    "payload": {
                        "ml_id":          result["ml_id"],
                        "product_id":     result["product_id"],
                        "title":          result["title"],
                        "price_current":  result["decision"].get("price_current"),
                        "price_original": result["decision"].get("price_original"),
                        "confidence":     result["decision"].get("confidence"),
                        "timestamp":      result["timestamp"],
                    },
                }]
            }
            resp = requests.put(
                f"{_QDRANT_URL}/collections/{self.COLLECTION}/points",
                json=body,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("✅ price_history gravado para %s", result["ml_id"])
        except Exception as exc:
            logger.error("Erro ao persistir no Qdrant: %s", exc)

    def _get_recent_history(self, ml_id: str, limit: int = 3):
        resp = requests.post(
            f"{_QDRANT_URL}/collections/{self.COLLECTION}/points/scroll",
            json={
                "filter":       {"must": [{"key": "ml_id", "match": {"value": ml_id}}]},
                "limit":        limit,
                "with_payload": True,
                "with_vector":  False,
            },
            timeout=10,
        )
        if resp.ok:
            return [p["payload"] for p in resp.json().get("result", {}).get("points", [])]
        return []


    # ------------------------------------------------------------------
    # Memória Redis
    # ------------------------------------------------------------------

    def _save_to_memory(self, data: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "price_oracle",
            "data": data,
        }
        self._redis.lpush(self._memory_key, json.dumps(entry, ensure_ascii=False))
        self._redis.ltrim(self._memory_key, 0, 99)


# ------------------------------------------------------------------
# CLI rápido para testes
# ------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Price Oracle Agent CLI")
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--ml-id",  help="ID direto do produto ML (ex: MLB123456789)")
    id_group.add_argument("--link",   help="Link de afiliado ou URL do produto (meli.la, mercadolivre.com.br...)")
    id_group.add_argument("--file",   help="Caminho para JSON com lista de links {\"links\": [...]}")
    parser.add_argument("--dry-run",       action="store_true", help="Não escreve no banco nem no Qdrant")
    parser.add_argument("--no-publish",    action="store_true", help="Consulta preço mas não publica no banco")
    args = parser.parse_args()

    os.environ.setdefault("HSMART_RETRIEVAL_URL", "http://localhost:5005")
    os.environ.setdefault("QDRANT_URL",            "http://localhost:6333")

    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    try:
        r = redis.Redis(host=redis_host, port=redis_port)
        r.ping()
    except Exception:
        r = None
        logger.warning("Redis indisponível — memória desativada")

    agent = PriceOracleAgent(redis_client=r)

    # ── modo --file: processa lista inteira ──────────────────────────
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
        links = data.get("links", [])
        if not links:
            print("❌ Nenhum link encontrado no arquivo.")
            sys.exit(1)

        print(f"\n📋 {len(links)} link(s) para processar\n")
        results = []
        for i, link in enumerate(links, 1):
            print(f"─── [{i}/{len(links)}] {link}")
            ml_id = resolve_ml_id_from_link(link)
            if not ml_id:
                print(f"  ⚠️  Não foi possível resolver MLB ID — pulando\n")
                results.append({"link": link, "success": False, "error": "ML ID não resolvido"})
                continue
            print(f"  ✅ ML ID: {ml_id}")
            result = agent.execute({
                "product_id":    ml_id,
                "ml_id":         ml_id,
                "title":         ml_id,
                "current_price": 0.0,
                "dry_run":       args.dry_run,
                "publish":       not args.no_publish,
            })
            result["link"] = link
            results.append(result)
            if result.get("published"):
                status = "✅ publicado"
            elif args.dry_run:
                status = "🔍 dry-run"
            else:
                detail = (result.get("publish_detail") or {}).get("detail", "")
                status = f"⚡ sem publicação{(' — ' + detail) if detail else ''}"
            price = result.get("decision", {}).get("price_current")
            print(f"  {status} | price_current={price}\n")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        ok  = sum(1 for r in results if r.get("success"))
        pub = sum(1 for r in results if r.get("published"))
        print(f"Resultado: {ok}/{len(links)} OK | {pub} publicados")
        sys.exit(0)

    # ── modo único: --link ou --ml-id ────────────────────────────────
    if args.link:
        print(f"🔗 Resolvendo link: {args.link}")
        ml_id = resolve_ml_id_from_link(args.link)
        if not ml_id:
            print(f"❌ Não foi possível extrair o MLB ID do link: {args.link}")
            sys.exit(1)
        print(f"✅ ML ID resolvido: {ml_id}")
    else:
        ml_id = args.ml_id

    result = agent.execute({
        "product_id":    ml_id,
        "ml_id":         ml_id,
        "title":         ml_id,
        "current_price": 0.0,
        "dry_run":       args.dry_run,
        "publish":       not args.no_publish,
    })

    print(json.dumps(result, ensure_ascii=False, indent=2))
