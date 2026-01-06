"""
Rotas de Webhooks para integração com marketplaces
Suporta: Mercado Livre, Shopee, Amazon, etc.
"""

import os
import json
import requests
from flask import Blueprint, request, jsonify
from datetime import datetime
from services.marketplace_service import (
    process_mercadolivre_notification,
    process_shopee_notification,
    process_amazon_notification
)

webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhook")


@webhook_bp.route("/health", methods=["GET"])
def health_check():
    """Health check para verificar se o serviço está ativo"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "webhook"
    }), 200


@webhook_bp.route("/mercadolivre", methods=["POST"])
def mercadolivre_webhook():
    """
    Webhook do Mercado Livre
    Recebe notificações sobre:
    - Novos itens publicados
    - Atualizações de preço
    - Mudanças de estoque
    - Finalizações de vendas
    
    Documentação: https://developers.mercadolivre.com.br/pt_br/notificacoes
    """
    try:
        # Captura os dados do webhook
        data = request.get_json()
        
        # Log para debug
        print(f"📦 [Mercado Livre] Webhook recebido: {json.dumps(data, indent=2)}")
        
        # Valida se há dados
        if not data:
            return jsonify({"error": "Dados vazios"}), 400
        
        # Extrai informações do webhook
        topic = data.get("topic")  # Ex: "items", "orders", "payments"
        resource = data.get("resource")  # URL do recurso
        user_id = data.get("user_id")
        application_id = data.get("application_id")
        
        # Processa a notificação
        result = process_mercadolivre_notification(
            topic=topic,
            resource=resource,
            user_id=user_id,
            application_id=application_id,
            full_data=data
        )
        
        return jsonify({
            "status": "success",
            "message": "Notificação processada",
            "result": result
        }), 200
        
    except Exception as e:
        print(f"❌ [Mercado Livre] Erro ao processar webhook: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@webhook_bp.route("/shopee", methods=["POST"])
def shopee_webhook():
    """
    Webhook da Shopee
    Recebe notificações sobre produtos e pedidos
    
    Documentação: https://open.shopee.com/documents/v2/v2.push.get_push_config
    """
    try:
        data = request.get_json()
        print(f"🛍️ [Shopee] Webhook recebido: {json.dumps(data, indent=2)}")
        
        if not data:
            return jsonify({"error": "Dados vazios"}), 400
        
        # Processa a notificação da Shopee
        result = process_shopee_notification(data)
        
        return jsonify({
            "status": "success",
            "message": "Notificação processada",
            "result": result
        }), 200
        
    except Exception as e:
        print(f"❌ [Shopee] Erro ao processar webhook: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@webhook_bp.route("/amazon", methods=["POST"])
def amazon_webhook():
    """
    Webhook da Amazon (Amazon MWS/SP-API)
    Recebe notificações sobre produtos
    
    Documentação: https://developer-docs.amazon.com/sp-api/docs/notifications-api-v1-reference
    """
    try:
        data = request.get_json()
        print(f"📦 [Amazon] Webhook recebido: {json.dumps(data, indent=2)}")
        
        if not data:
            return jsonify({"error": "Dados vazios"}), 400
        
        # Processa a notificação da Amazon
        result = process_amazon_notification(data)
        
        return jsonify({
            "status": "success",
            "message": "Notificação processada",
            "result": result
        }), 200
        
    except Exception as e:
        print(f"❌ [Amazon] Erro ao processar webhook: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@webhook_bp.route("/test", methods=["POST"])
def test_webhook():
    """
    Endpoint de teste para simular webhooks
    Útil para desenvolvimento e testes
    """
    try:
        data = request.get_json()
        marketplace = data.get("marketplace", "unknown")
        
        print(f"🧪 [TEST] Webhook de teste recebido para {marketplace}")
        print(f"📄 Dados: {json.dumps(data, indent=2)}")
        
        return jsonify({
            "status": "success",
            "message": "Webhook de teste recebido",
            "received_data": data
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
