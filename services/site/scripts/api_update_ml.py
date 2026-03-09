#!/usr/bin/env python3
"""
Script para ATUALIZAR produtos existentes no banco via API oficial do Mercado Livre.
Atualiza: preço, desconto, disponibilidade e mídias (imagens/vídeos).
"""
import sys
import os
import json
import re
import requests
from pathlib import Path
from datetime import datetime

# Adiciona o diretório pai ao path para importar models
sys.path.append(str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy.orm import sessionmaker
from models.product import Product

Session = sessionmaker(bind=engine)

# Diretórios
STAGING_DIR = Path("/app/staging")
CONFIG_DIR = Path("/app/config")
TOKENS_FILE = CONFIG_DIR / "ml_tokens.json"


def load_tokens():
    """Carrega tokens OAuth do arquivo."""
    if not TOKENS_FILE.exists():
        print("❌ Arquivo de tokens não encontrado!")
        print(f"   Execute o OAuth primeiro: acesse /auth/mercadolivre/login")
        sys.exit(1)
    
    with open(TOKENS_FILE, 'r') as f:
        return json.load(f)


def extract_item_id(url):
    """Extrai o MLB ID da URL do produto."""
    # Padrões possíveis:
    # https://produto.mercadolivre.com.br/MLB-1234567890-...
    # https://www.mercadolivre.com.br/MLB-1234567890-...
    # https://mercadolivre.com/sec/ABC123 (link de afiliado)
    
    patterns = [
        r'MLB-(\d+)',  # Captura direto o ID
        r'/p/MLB(\d+)',  # Formato alternativo
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            item_id = f"MLB{match.group(1)}" if 'MLB' not in match.group(0) else match.group(0)
            return item_id
    
    # Se for link de afiliado, precisa resolver primeiro
    if '/sec/' in url or 'mpago.la' in url or 'mercadolivre.com/p/' in url:
        print(f"🔄 Resolvendo link de afiliado: {url}")
        try:
            response = requests.get(url, allow_redirects=True, timeout=10)
            final_url = response.url
            print(f"✅ URL resolvida: {final_url}")
            return extract_item_id(final_url)
        except Exception as e:
            print(f"❌ Erro ao resolver link: {e}")
            return None
    
    print(f"❌ Não foi possível extrair o MLB ID da URL: {url}")
    return None


def fetch_product_from_api(item_id, access_token):
    """Busca informações atualizadas do produto via API do Mercado Livre."""
    print(f"📡 Buscando dados atualizados do produto {item_id}...")
    
    # API do Mercado Livre - endpoint de item
    api_url = f"https://api.mercadolibre.com/items/{item_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extrai informações relevantes
        product_info = {
            'item_id': item_id,
            'title': data.get('title', ''),
            'price': data.get('price', 0),
            'original_price': data.get('original_price'),
            'available_quantity': data.get('available_quantity', 0),
            'status': data.get('status', 'unknown'),  # active, paused, closed
            'pictures': [pic['url'] for pic in data.get('pictures', [])],
            'video_id': data.get('video_id'),
            'permalink': data.get('permalink', ''),
            'currency': data.get('currency_id', 'BRL'),
        }
        
        # Calcula desconto
        if product_info['original_price'] and product_info['original_price'] > product_info['price']:
            discount = int((1 - product_info['price'] / product_info['original_price']) * 100)
            product_info['discount'] = discount
        else:
            product_info['discount'] = 0
        
        return product_info
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar produto: {e}")
        return None


def update_product_in_db(item_id, product_info):
    """Atualiza produto existente no banco de dados."""
    session = Session()
    
    try:
        # Busca produto pelo MLB ID no link
        product = session.query(Product).filter(
            Product.link.like(f'%{item_id}%')
        ).first()
        
        if not product:
            print(f"❌ Produto {item_id} não encontrado no banco de dados!")
            print(f"   Use 'make api-prepare-product' para adicionar um novo produto.")
            return False
        
        print(f"✅ Produto encontrado no banco: ID {product.id} - {product.title}")
        print(f"")
        print(f"🔄 Atualizando informações...")
        
        # Atualiza campos
        old_price = product.price
        old_old_price = product.oldPrice
        old_available = product.available_quantity if hasattr(product, 'available_quantity') else 'N/A'
        
        # Formata preço
        new_price = f"R$ {product_info['price']:.2f}".replace('.', ',')
        new_old_price = f"R$ {product_info['original_price']:.2f}".replace('.', ',') if product_info['original_price'] else None
        
        product.price = new_price
        product.oldPrice = new_old_price
        
        # Atualiza imagens se houver novas
        if product_info['pictures']:
            # Mantém bucket name original
            bucket_name = product.bucketName
            images_urls = []
            
            for idx, pic_url in enumerate(product_info['pictures']):
                # Extrai nome do arquivo da URL
                filename = f"image_{idx+1}.jpg"
                # Monta URL do MinIO
                minio_url = f"/media/{bucket_name}/{filename}?token=secreto123"
                images_urls.append(minio_url)
            
            product.images = images_urls
            print(f"   📸 Atualizadas {len(images_urls)} imagens")
        
        # Atualiza disponibilidade (se campo existir)
        if hasattr(product, 'available_quantity'):
            product.available_quantity = product_info['available_quantity']
        
        # Commit
        session.commit()
        
        print(f"")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✅ PRODUTO ATUALIZADO COM SUCESSO!")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"")
        print(f"📊 Alterações:")
        print(f"   💰 Preço:        {old_price} → {new_price}")
        if product_info['discount'] > 0:
            print(f"   🔥 Desconto:     {product_info['discount']}%")
        if new_old_price:
            print(f"   💸 Preço antigo: {old_old_price} → {new_old_price}")
        if hasattr(product, 'available_quantity'):
            print(f"   📦 Estoque:      {old_available} → {product_info['available_quantity']}")
        print(f"   📸 Imagens:      {len(product_info['pictures'])} fotos atualizadas")
        print(f"")
        print(f"🔗 Link: {product.link}")
        print(f"")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao atualizar produto no banco: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python3 api_update_ml.py <URL_DO_PRODUTO>")
        sys.exit(1)
    
    product_url = sys.argv[1]
    
    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔄 ATUALIZAÇÃO DE PRODUTO - API MERCADO LIVRE")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")
    
    # Extrai MLB ID
    item_id = extract_item_id(product_url)
    if not item_id:
        sys.exit(1)
    
    print(f"🆔 MLB ID: {item_id}")
    print("")
    
    # Carrega tokens
    tokens = load_tokens()
    access_token = tokens.get('access_token')
    
    if not access_token:
        print("❌ Token de acesso não encontrado!")
        sys.exit(1)
    
    # Busca dados atualizados da API
    product_info = fetch_product_from_api(item_id, access_token)
    if not product_info:
        sys.exit(1)
    
    print(f"✅ Dados obtidos da API:")
    print(f"   📝 Título: {product_info['title'][:60]}...")
    print(f"   💰 Preço: R$ {product_info['price']:.2f}")
    if product_info['original_price']:
        print(f"   💸 Preço original: R$ {product_info['original_price']:.2f}")
    if product_info['discount'] > 0:
        print(f"   🔥 Desconto: {product_info['discount']}%")
    print(f"   📦 Estoque: {product_info['available_quantity']} unidades")
    print(f"   📊 Status: {product_info['status']}")
    print(f"   📸 Imagens: {len(product_info['pictures'])} fotos")
    print("")
    
    # Atualiza no banco
    success = update_product_in_db(item_id, product_info)
    
    if success:
        print("✅ Produto atualizado e pronto para uso!")
        print("")
    else:
        print("❌ Falha ao atualizar produto")
        sys.exit(1)


if __name__ == "__main__":
    main()
