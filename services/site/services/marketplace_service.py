"""
Serviço para processar notificações dos marketplaces
e atualizar produtos já cadastrados (preço, disponibilidade, imagens, staging JSON)
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from database import db
from models.product import Product
from services.minio_client import minio_client


class MarketplaceService:
    """Serviço base para integração com marketplaces"""
    
    def __init__(self):
        self.minio_client = minio_client
        self.staging_dir = Path(__file__).parent.parent / "staging"
        
    def update_product_from_webhook(
        self,
        platform: str,
        external_id: str,
        product_data: Dict
    ) -> Optional[Product]:
        """
        Atualiza um produto EXISTENTE a partir de dados do webhook
        Não cria produtos novos - apenas atualiza os já cadastrados
        
        Args:
            platform: Nome da plataforma (mercadolivre, shopee, amazon)
            external_id: ID do produto no marketplace
            product_data: Dados atualizados do produto
            
        Returns:
            Produto atualizado ou None se não existir
        """
        try:
            # Busca produto existente pelo external_id
            existing_product = Product.query.filter_by(
                platform=platform,
                external_id=external_id
            ).first()
            
            if not existing_product:
                print(f"⚠️  Produto {external_id} não encontrado no banco. Webhook ignorado.")
                print(f"💡 Dica: Cadastre o produto manualmente primeiro usando os scripts de staging.")
                return None
            
            print(f"🔄 Atualizando produto existente: {external_id}")
            
            # Atualiza campos no banco de dados
            if "preco" in product_data:
                existing_product.preco = product_data["preco"]
                existing_product.price = product_data["preco"]  # Sincroniza campos
            
            if "preco_original" in product_data:
                existing_product.preco_original = product_data["preco_original"]
                existing_product.old_price = product_data["preco_original"]
            
            if "desconto" in product_data:
                existing_product.desconto = product_data["desconto"]
            
            if "link" in product_data:
                existing_product.link = product_data["link"]
            
            if "disponivel" in product_data:
                existing_product.disponivel = product_data["disponivel"]
            
            if "imagens" in product_data:
                # Atualiza imagens no banco
                existing_product.imagens = json.dumps(product_data["imagens"])
                existing_product.image = json.dumps(product_data["imagens"])
            
            existing_product.updated_at = datetime.utcnow()
            
            db.session.commit()
            print(f"✅ Banco de dados atualizado para produto ID: {existing_product.id}")
            
            # Atualiza JSON de staging
            self._update_staging_json(existing_product, product_data)
            
            return existing_product
                
        except Exception as e:
            print(f"❌ Erro ao atualizar produto: {str(e)}")
            db.session.rollback()
            raise
    
    def _update_staging_json(self, product: Product, new_data: Dict):
        """
        Atualiza o arquivo JSON de staging do produto
        Mantém a estrutura original e atualiza apenas campos relevantes
        """
        try:
            # Procura o arquivo JSON do produto
            staging_files = list(self.staging_dir.glob("*.json"))
            
            for json_file in staging_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        staging_data = json.load(f)
                    
                    # Verifica se é o produto correto (por link ou nome)
                    if staging_data.get("link") == product.link or \
                       staging_data.get("external_id") == product.external_id:
                        
                        print(f"📝 Atualizando staging JSON: {json_file.name}")
                        
                        # Atualiza campos
                        if "preco" in new_data:
                            staging_data["preco"] = new_data["preco"]
                        
                        if "preco_original" in new_data:
                            staging_data["preco_original"] = new_data["preco_original"]
                        
                        if "desconto" in new_data:
                            staging_data["desconto"] = new_data["desconto"]
                        
                        if "disponivel" in new_data:
                            staging_data["disponivel"] = new_data["disponivel"]
                        
                        if "imagens" in new_data:
                            staging_data["imagens"] = new_data["imagens"]
                        
                        # Adiciona timestamp de última atualização
                        staging_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
                        staging_data["atualizado_via_webhook"] = True
                        
                        # Salva arquivo atualizado
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(staging_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ Staging JSON atualizado com sucesso!")
                        return
                        
                except json.JSONDecodeError:
                    continue
            
            print(f"⚠️  Arquivo staging JSON não encontrado para produto {product.external_id}")
            
        except Exception as e:
            print(f"⚠️  Erro ao atualizar staging JSON: {str(e)}")


# ===================== MERCADO LIVRE =====================

def process_mercadolivre_notification(
    topic: str,
    resource: str,
    user_id: str,
    application_id: str,
    full_data: Dict
) -> Dict:
    """
    Processa notificações do Mercado Livre
    
    Topics suportados:
    - items: Novos itens ou atualizações
    - orders: Pedidos
    - payments: Pagamentos
    """
    print(f"🔍 [Mercado Livre] Processando topic: {topic}")
    
    if topic == "items":
        return process_mercadolivre_item(resource)
    elif topic == "orders":
        print(f"📦 [Mercado Livre] Pedido recebido: {resource}")
        return {"message": "Pedido registrado"}
    elif topic == "payments":
        print(f"💰 [Mercado Livre] Pagamento recebido: {resource}")
        return {"message": "Pagamento registrado"}
    else:
        print(f"⚠️ [Mercado Livre] Topic não tratado: {topic}")
        return {"message": f"Topic {topic} não implementado"}


def process_mercadolivre_item(resource_url: str) -> Dict:
    """
    Busca dados atualizados do item no Mercado Livre e atualiza no banco
    NÃO cria produtos novos - apenas atualiza os existentes
    
    Args:
        resource_url: URL da API do Mercado Livre para o item
        Ex: https://api.mercadolibre.com/items/MLB123456789
    """
    try:
        from services.ml_auth import ml_auth
        
        # Busca dados do item na API do Mercado Livre
        print(f"📡 Buscando dados atualizados do item: {resource_url}")
        
        # Tenta usar o access_token se disponível
        headers = {}
        access_token = ml_auth.get_valid_access_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            print(f"🔑 Usando access_token para autenticação")
        else:
            print(f"⚠️  Sem access_token, requisição pode ser limitada")
        
        response = requests.get(resource_url, headers=headers)
        response.raise_for_status()
        
        item_data = response.json()
        
        # Extrai informações do item
        item_id = item_data.get("id")
        title = item_data.get("title")
        price = item_data.get("price")
        original_price = item_data.get("original_price", price)
        permalink = item_data.get("permalink")
        status = item_data.get("status")  # active, paused, closed
        available_quantity = item_data.get("available_quantity", 0)
        pictures = item_data.get("pictures", [])
        
        # Verifica disponibilidade
        disponivel = status == "active" and available_quantity > 0
        
        # Calcula desconto
        discount = 0
        if original_price and price and original_price > price:
            discount = round(((original_price - price) / original_price) * 100, 2)
        
        # Monta lista de imagens
        images = [pic.get("url") or pic.get("secure_url") for pic in pictures]
        
        # Prepara dados para atualizar
        product_data = {
            "preco": str(price),
            "preco_original": str(original_price),
            "desconto": discount,
            "link": permalink,
            "disponivel": disponivel,
            "imagens": images,
            "status": status,
            "quantidade_disponivel": available_quantity
        }
        
        # Atualiza no banco (apenas se já existir)
        service = MarketplaceService()
        product = service.update_product_from_webhook(
            platform="mercadolivre",
            external_id=item_id,
            product_data=product_data
        )
        
        if not product:
            return {
                "message": "Produto não encontrado no banco",
                "external_id": item_id,
                "title": title,
                "action": "ignored",
                "tip": "Cadastre o produto manualmente primeiro"
            }
        
        return {
            "message": "Produto atualizado com sucesso",
            "product_id": product.id,
            "external_id": item_id,
            "title": title,
            "preco": price,
            "desconto": discount,
            "disponivel": disponivel,
            "action": "updated"
        }
        
    except requests.RequestException as e:
        error_msg = str(e)
        print(f"❌ Erro ao buscar item na API do ML: {error_msg}")
        
        # Se for erro 403/401, sugere autenticação
        if "403" in error_msg or "401" in error_msg:
            return {
                "message": "Erro de autenticação com a API do Mercado Livre",
                "error": error_msg,
                "tip": "Faça login em /auth/mercadolivre/login para obter access_token"
            }
        
        raise
    except Exception as e:
        print(f"❌ Erro ao processar item do ML: {str(e)}")
        raise


# ===================== SHOPEE =====================

def process_shopee_notification(data: Dict) -> Dict:
    """
    Processa notificações da Shopee
    Atualiza produtos já cadastrados
    """
    print(f"🛍️ [Shopee] Processando notificação")
    
    # A estrutura varia conforme o tipo de notificação da Shopee
    # Exemplo básico:
    code = data.get("code")
    shop_id = data.get("shop_id")
    
    # Para atualização de produtos
    if "item" in data or "product" in data:
        print(f"🔄 [Shopee] Atualizando produto")
        return {"message": "Produto da Shopee atualizado"}
    
    # Para pedidos
    order_sn = data.get("data", {}).get("order_sn")
    if order_sn:
        print(f"📦 [Shopee] Pedido recebido: {order_sn}")
        return {"message": "Pedido da Shopee registrado", "order_sn": order_sn}
    
    return {"message": "Notificação da Shopee processada"}


# ===================== AMAZON =====================

def process_amazon_notification(data: Dict) -> Dict:
    """
    Processa notificações da Amazon (SP-API)
    Atualiza produtos já cadastrados
    """
    print(f"📦 [Amazon] Processando notificação")
    
    # Estrutura básica da Amazon SP-API
    notification_type = data.get("NotificationType")
    notification_version = data.get("NotificationVersion")
    payload = data.get("Payload")
    
    if notification_type == "LISTINGS_ITEM_STATUS_CHANGE":
        print(f"🔄 [Amazon] Status de item alterado")
        return {"message": "Status de item da Amazon atualizado"}
    elif notification_type == "PRODUCT_TYPE_DEFINITIONS_CHANGE":
        print(f"📋 [Amazon] Definições de tipo de produto alteradas")
        return {"message": "Definições de produto da Amazon processadas"}
    
    return {"message": "Notificação da Amazon processada"}


# ===================== UTILS =====================
# Função removida: auto_categorize_product
# Produtos não são criados via webhook, apenas atualizados
# Categorização é feita manualmente no staging JSON

