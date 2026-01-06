"""
Rotas para sincronização manual de produtos do Mercado Livre
Atualiza preços, disponibilidade e imagens via API
"""

from flask import Blueprint, jsonify, request
from services.ml_auth import ml_auth
from services.marketplace_service import process_mercadolivre_item
from models.product import Product
from database import db

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
