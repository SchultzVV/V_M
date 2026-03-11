"""
Rotas para sincronização manual de produtos do Mercado Livre
Atualiza preços, disponibilidade e imagens via API
"""

import subprocess
import sys
from flask import Blueprint, jsonify, request
from services.ml_auth import ml_auth
from services.marketplace_service import process_mercadolivre_item
from models.product import Product
from database import db, SessionLocal

sync_bp = Blueprint("sync", __name__, url_prefix="/sync")


@sync_bp.route("/mercadolivre/product/<external_id>", methods=["POST"])
def sync_mercadolivre_product(external_id: str):
    """
    Sincroniza um produto específico do Mercado Livre
    
    Args:
        external_id: ID do produto no ML (ex: MLB1234567890)
    
    Exemplo:
        POST /sync/mercadolivre/product/MLB1234567890
    """
    try:
        # Verifica autenticação
        if not ml_auth.is_authenticated():
            return jsonify({
                "status": "error",
                "message": "Não autenticado com o Mercado Livre",
                "tip": "Faça login em /auth/mercadolivre/login"
            }), 401
        
        # Busca o produto no banco
        product = Product.query.filter_by(
            platform="mercadolivre",
            external_id=external_id
        ).first()
        
        if not product:
            return jsonify({
                "status": "error",
                "message": f"Produto {external_id} não encontrado no banco",
                "tip": "Cadastre o produto primeiro usando os scripts de staging"
            }), 404
        
        # Sincroniza via API do ML
        resource_url = f"https://api.mercadolibre.com/items/{external_id}"
        result = process_mercadolivre_item(resource_url)
        
        return jsonify({
            "status": "success",
            "message": "Produto sincronizado com sucesso",
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao sincronizar produto: {str(e)}"
        }), 500


@sync_bp.route("/mercadolivre/all", methods=["POST"])
def sync_all_mercadolivre_products():
    """
    Sincroniza TODOS os produtos do Mercado Livre cadastrados
    
    Exemplo:
        POST /sync/mercadolivre/all
    """
    try:
        # Verifica autenticação
        if not ml_auth.is_authenticated():
            return jsonify({
                "status": "error",
                "message": "Não autenticado com o Mercado Livre",
                "tip": "Faça login em /auth/mercadolivre/login"
            }), 401
        
        # Busca todos os produtos do ML que têm external_id
        products = Product.query.filter(
            Product.platform == "mercadolivre",
            Product.external_id.isnot(None),
            Product.external_id != ""
        ).all()
        
        if not products:
            return jsonify({
                "status": "warning",
                "message": "Nenhum produto do Mercado Livre encontrado",
                "tip": "Cadastre produtos com external_id primeiro"
            })
        
        results = {
            "total": len(products),
            "success": 0,
            "errors": 0,
            "details": []
        }
        
        # Sincroniza cada produto
        for product in products:
            try:
                resource_url = f"https://api.mercadolibre.com/items/{product.external_id}"
                result = process_mercadolivre_item(resource_url)
                
                results["success"] += 1
                results["details"].append({
                    "external_id": product.external_id,
                    "title": product.title,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                results["errors"] += 1
                results["details"].append({
                    "external_id": product.external_id,
                    "title": product.title,
                    "status": "error",
                    "error": str(e)
                })
        
        return jsonify({
            "status": "completed",
            "message": f"Sincronização concluída: {results['success']} sucesso, {results['errors']} erros",
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao sincronizar produtos: {str(e)}"
        }), 500


@sync_bp.route("/mercadolivre/status")
def sync_status():
    """
    Verifica quantos produtos estão prontos para sincronização
    """
    # Conta produtos do ML com external_id
    ml_products = Product.query.filter(
        Product.platform == "mercadolivre",
        Product.external_id.isnot(None),
        Product.external_id != ""
    ).count()
    
    # Verifica autenticação
    is_authenticated = ml_auth.is_authenticated()
    
    return jsonify({
        "platform": "mercadolivre",
        "total_products": ml_products,
        "authenticated": is_authenticated,
        "ready_to_sync": ml_products > 0 and is_authenticated,
        "endpoints": {
            "sync_one": "/sync/mercadolivre/product/<external_id>",
            "sync_all": "/sync/mercadolivre/all"
        }
    })


@sync_bp.route("/mercadolivre/cheapest-all", methods=["POST"])
def sync_ml_cheapest_all():
    """
    Percorre todos os produtos ML no banco e atualiza para o vendedor mais barato.
    Usa external_id diretamente (ignora link salvo, que pode ser meli.la/...).

    Query param opcional:
        ?dry_run=true   → simula sem salvar

    Exemplo:
        POST /sync/mercadolivre/cheapest-all
        POST /sync/mercadolivre/cheapest-all?dry_run=true
    """
    dry_run = request.args.get("dry_run", "false").lower() == "true"
    try:
        from scripts.price_validator.ml_api import get_item, get_catalog_listings
        from scripts.price_validator.price_service import parse_catalog_listings, find_cheapest
        from scripts.price_validator.affiliate import generate_affiliate_link
        from datetime import datetime

        def _parse_price(val):
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

        def _fmt(price):
            s = f"{price:,.2f}"
            return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

        session = SessionLocal()
        products = session.query(Product).filter(
            Product.platform == "mercadolivre",
            Product.external_id.isnot(None),
            Product.external_id != "",
            Product.disponivel == True,
        ).all()

        results = {"total": len(products), "updated": 0, "cheapest": 0, "errors": 0, "details": []}

        for product in products:
            current_price = _parse_price(product.price)
            try:
                # Usa external_id diretamente — não parseia link
                catalog_id = None
                item_data  = get_item(product.external_id)
                if item_data:
                    catalog_id = item_data.get("catalog_product_id")
                if not catalog_id:
                    catalog_id = product.external_id

                raw      = get_catalog_listings(catalog_id)
                listings = parse_catalog_listings(raw)
                cheapest = find_cheapest(listings) if listings else None

                if not cheapest:
                    results["details"].append({"id": product.external_id, "status": "no_data"})
                    continue

                # Resolve permalink (endpoint /products/{id}/items não retorna permalink)
                if not cheapest.permalink:
                    pd = get_item(cheapest.item_id)
                    if pd:
                        cheapest.permalink = pd.get("permalink", "") or ""
                if not cheapest.permalink:
                    cheapest.permalink = f"https://www.mercadolivre.com.br/p/{catalog_id}"

                affiliate = generate_affiliate_link(cheapest.permalink) if cheapest.permalink else ""

                if current_price > 0 and cheapest.real_price >= current_price * 0.99:
                    results["cheapest"] += 1
                    results["details"].append({
                        "id": product.external_id, "status": "cheapest",
                        "price": _fmt(current_price)
                    })
                    continue

                if not dry_run:
                    product.old_price  = product.price
                    product.price      = _fmt(cheapest.real_price)
                    product.link       = affiliate or cheapest.permalink
                    product.updated_at = datetime.utcnow()
                    session.commit()

                results["updated"] += 1
                results["details"].append({
                    "id":        product.external_id,
                    "title":     product.title[:60],
                    "status":    "updated" + ("_dry" if dry_run else ""),
                    "old_price": _fmt(current_price),
                    "new_price": _fmt(cheapest.real_price),
                    "new_link":  affiliate or cheapest.permalink,
                })

            except Exception as e:
                results["errors"] += 1
                results["details"].append({"id": product.external_id, "status": "error", "error": str(e)})

        session.close()
        return jsonify({
            "status":  "ok",
            "dry_run": dry_run,
            "summary": {
                "total":    results["total"],
                "updated":  results["updated"],
                "cheapest": results["cheapest"],
                "errors":   results["errors"],
            },
            "details": results["details"],
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@sync_bp.route("/shopee/product/<external_id>", methods=["POST"])
def sync_shopee_product(external_id: str):
    """
    Sincroniza um produto específico da Shopee
    TODO: Implementar quando tiver credenciais da Shopee
    """
    return jsonify({
        "status": "not_implemented",
        "message": "Sincronização da Shopee ainda não implementada",
        "platform": "shopee"
    }), 501


@sync_bp.route("/amazon/product/<external_id>", methods=["POST"])
def sync_amazon_product(external_id: str):
    """
    Sincroniza um produto específico da Amazon
    TODO: Implementar quando tiver credenciais da Amazon
    """
    return jsonify({
        "status": "not_implemented",
        "message": "Sincronização da Amazon ainda não implementada",
        "platform": "amazon"
    }), 501
