#!/usr/bin/env python3
"""
Preparação HÍBRIDA de produtos do Mercado Livre:
1. Usa scraping HTML (auto_prepare_ml) para resolver links e obter dados básicos
2. Enriquece com API oficial para informações precisas e completas
"""

import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import re
from slugify import slugify

# Importa funções do auto_prepare_ml (scraping que funciona)
sys.path.insert(0, os.path.dirname(__file__))
from auto_prepare_ml import (
    follow_affiliate_link,
    scrape_mercadolivre_product,
    download_images as download_images_from_scraping
)


def load_ml_token():
    """Carrega o token OAuth do Mercado Livre."""
    token_file = Path("/app/config/ml_tokens.json")
    
    if not token_file.exists():
        return None
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token')
    except Exception as e:
        print(f"❌ Erro ao ler token: {e}")
        return None


def get_product_from_api(item_id, token, is_catalog=False):
    """
    Busca informações completas do produto via API oficial.
    
    Endpoints:
    - /products/{ID} - Produtos de catálogo (URLs com /p/)
    - /items/{ID} - Items individuais
    
    Documentação: https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos
    
    Retorna:
        - id: ID do item/produto
        - title: Título completo
        - price: Preço atual
        - original_price: Preço anterior (se houver desconto)
        - available_quantity: Estoque disponível
        - condition: new, used, refurbished
        - pictures: Array com imagens em alta qualidade
        - video_id: ID do vídeo (se houver)
        - permalink: Link permanente do produto
    """
    # ID já vem limpo do scraping (ex: MLB1234567890)
    clean_id = item_id.replace('-', '').replace('MLB', 'MLB')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; VitorMarketplace/1.0)'
    }
    
    # Adiciona OAuth token se disponível
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    # Tenta primeiro como produto de catálogo (mais comum)
    url_catalog = f"https://api.mercadolibre.com/products/{clean_id}"
    print(f"   🌐 Tentando endpoint de CATÁLOGO: {url_catalog}")
    print(f"   🔑 Auth: {'✅ OAuth Token' if token else '❌ Público (sem token)'}")
    
    try:
        response = requests.get(url_catalog, headers=headers, timeout=15)
        print(f"   📡 Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Produto encontrado no CATÁLOGO!")
            return response.json()
        
        # Se não achou no catálogo, tenta como item individual
        print(f"   ⚠️  Não encontrado no catálogo, tentando como ITEM individual...")
        
        url_item = f"https://api.mercadolibre.com/items/{clean_id}"
        print(f"   🌐 URL: {url_item}")
        
        response = requests.get(url_item, headers=headers, timeout=15)
        print(f"   📡 Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Item individual encontrado!")
            return response.json()
        
        if response.status_code == 404:
            print(f"   ⚠️  Produto não encontrado em nenhum endpoint")
            print(f"   💡 Possíveis causas:")
            print(f"      - Produto expirado/removido")
            print(f"      - ID incorreto: {clean_id}")
            print(f"      - Restrições de acesso")
            return None
        
        if response.status_code == 403:
            print(f"   ⚠️  Acesso negado (403)")
            print(f"   💡 Verifique permissões do OAuth token")
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        print(f"   ⚠️  Timeout na API (>15s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Erro na API: {e}")
        return None


def download_images_hq(image_urls, product_slug, base_path="/app/uploads"):
    """
    Baixa imagens do produto em ALTA QUALIDADE da API.
    Retorna o diretório e lista de arquivos baixados.
    """
    product_dir = Path(base_path) / product_slug
    product_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📥 Baixando {len(image_urls)} imagens em ALTA QUALIDADE (API)...")
    
    downloaded = []
    total_size = 0
    
    for i, img_url in enumerate(image_urls, 1):
        try:
            # Pega a URL em melhor qualidade (-O = Original)
            img_url_hq = img_url.replace('-I.', '-O.').replace('-V.', '-O.')
            
            response = requests.get(img_url_hq, timeout=15)
            response.raise_for_status()
            
            # Salva a imagem
            img_filename = f"image_{i}.jpg"
            img_path = product_dir / img_filename
            
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            size_kb = len(response.content) / 1024
            total_size += size_kb
            downloaded.append(img_filename)
            
            print(f"   ✅ Imagem {i}/{len(image_urls)} - {size_kb:.1f}KB")
            
        except Exception as e:
            print(f"   ⚠️  Erro na imagem {i}: {e}")
    
    print(f"\n📊 Total baixado: {total_size:.1f}KB ({len(downloaded)} imagens)")
    
    return str(product_dir.relative_to(Path(base_path).parent)), downloaded


def enrich_with_api(product_data_html, item_id, token, original_url):
    """
    Enriquece os dados do scraping HTML com informações precisas da API oficial.
    
    Campos da API (baseado na documentação oficial):
    - id: ID único do produto
    - title: Título completo
    - price: Preço atual (float)
    - original_price: Preço original antes de desconto (float ou null)
    - available_quantity: Estoque disponível (int)
    - condition: "new", "used", "refurbished"
    - pictures: Lista de objetos com URLs de imagens
      * url: URL da imagem (diferentes tamanhos: -I, -O)
      * secure_url: URL HTTPS
      * size: Tamanho em pixels
    - video_id: ID do vídeo (string ou null)
    - permalink: Link permanente do produto
    - sold_quantity: Quantidade vendida (somente com token do proprietário)
    - status: "active", "paused", "closed"
    """
    print("\n" + "=" * 60)
    print("🚀 ENRIQUECENDO COM API OFICIAL DO MERCADO LIVRE")
    print("=" * 60)
    
    # Busca na API
    print(f"\n📡 Consultando API para ID: {item_id}...")
    api_data = get_product_from_api(item_id, token)
    
    if not api_data:
        print("\n❌ API não disponível - usando APENAS dados do scraping HTML")
        print("   💡 Os dados do scraping podem estar desatualizados ou incompletos")
        
        # Como a API falhou, agora baixa as imagens do scraping
        if product_data_html.get('images'):
            print(f"\n📥 Baixando {len(product_data_html['images'])} imagens do scraping como fallback...")
            product_slug = slugify(product_data_html['title'])
            images_dir = download_images_from_scraping(product_data_html['images'], product_slug)
            product_data_html['images_local'] = images_dir
        
        return product_data_html
    
    print("✅ Dados recebidos da API oficial!")
    print(f"   📦 ID: {api_data.get('id')}")
    
    # Produtos de catálogo usam 'name', items usam 'title'
    product_title = api_data.get('name') or api_data.get('title', '')
    print(f"   📝 Título: {product_title[:60]}...")
    print(f"   🏷️  Status: {api_data.get('status', 'N/A')}")
    
    # Cria dados enriquecidos (prioriza API > Scraping)
    enriched = product_data_html.copy()
    
    # 1. TÍTULO (API é mais completo)
    if product_title:
        if product_title != enriched.get('title'):
            print(f"\n📝 Título atualizado:")
            print(f"   Scraping: {enriched.get('title', '')[:50]}...")
            print(f"   API:      {product_title[:50]}...")
        enriched['title'] = product_title
    
    # 2. PREÇOS (API de items tem, catálogo não tem)
    if api_data.get('price'):
        enriched['price'] = float(api_data['price'])
        print(f"\n💰 Preço atual (API):")
        print(f"   Scraping: R$ {product_data_html.get('price', 0)}")
        print(f"   API:      R$ {api_data['price']} ✅")
    else:
        # Produto de catálogo - mantém preço do scraping
        print(f"\n💰 Preço mantido do scraping:")
        print(f"   API de catálogo não fornece preço direto")
        print(f"   Usando: R$ {product_data_html.get('price', 0)}")
    
    # 3. DESCONTO (se houver original_price diferente)
    if api_data.get('original_price') and api_data['original_price'] != api_data.get('price'):
        enriched['old_price'] = float(api_data['original_price'])
        discount_percent = ((api_data['original_price'] - api_data['price']) / api_data['original_price']) * 100
        discount_value = api_data['original_price'] - api_data['price']
        
        print(f"\n🏷️  DESCONTO ATIVO:")
        print(f"   De:       R$ {api_data['original_price']:.2f}")
        print(f"   Por:      R$ {api_data['price']:.2f}")
        print(f"   Economia: R$ {discount_value:.2f} ({discount_percent:.0f}% OFF)")
    else:
        enriched['old_price'] = 0
    
    # 4. CONDIÇÃO DO PRODUTO
    if api_data.get('condition'):
        condition_map = {
            'new': 'Novo',
            'used': 'Usado',
            'refurbished': 'Recondicionado',
            'not_specified': 'Não especificado'
        }
        enriched['condition'] = condition_map.get(api_data['condition'], api_data['condition'])
        print(f"\n📦 Condição: {enriched['condition']}")
    
    # 5. ESTOQUE E DISPONIBILIDADE (só em items, não em catálogo)
    if 'available_quantity' in api_data:
        qty = api_data['available_quantity']
        enriched['available_quantity'] = qty
        enriched['disponivel'] = qty > 0
        
        status_icon = "✅" if qty > 0 else "❌"
        status_text = f"{qty} unidades" if qty > 0 else "ESGOTADO"
        print(f"\n📊 Estoque: {status_icon} {status_text}")
    
    # 6. IMAGENS EM ALTA QUALIDADE (CRÍTICO!)
    if api_data.get('pictures') and len(api_data['pictures']) > 0:
        num_scraping_imgs = len(product_data_html.get('images', []))
        num_api_imgs = len(api_data['pictures'])
        
        print(f"\n🖼️  IMAGENS:")
        print(f"   Scraping: {num_scraping_imgs} imagens")
        print(f"   API:      {num_api_imgs} imagens HQ disponíveis")
        
        # Extrai URLs das imagens (pega secure_url ou url)
        image_urls = []
        for pic in api_data['pictures']:
            img_url = pic.get('secure_url') or pic.get('url')
            if img_url:
                # Força qualidade original (-O = Original, maior qualidade)
                img_url_hq = img_url.replace('-I.', '-O.').replace('-V.', '-O.')
                image_urls.append(img_url_hq)
        
        if image_urls:
            print(f"   ✅ Substituindo por {len(image_urls)} imagens em ALTA QUALIDADE (Original Quality)")
            
            # Usa o slug do produto
            product_slug = slugify(enriched['title'])
            
            # Baixa as imagens em HQ
            images_dir, downloaded_images = download_images_hq(image_urls, product_slug)
            
            # Atualiza no dicionário
            enriched['images_local'] = images_dir
            enriched['images'] = []  # Será preenchido no stage
            
            print(f"   ✅ {len(downloaded_images)} imagens HQ salvas em: {images_dir}")
    
    # 7. VÍDEO DO PRODUTO
    if api_data.get('video_id') and api_data['video_id'] != 'null':
        enriched['video_id'] = api_data['video_id']
        print(f"\n🎥 Vídeo disponível: {api_data['video_id']}")
    
    # 8. LINK PERMANENTE (melhor que link de afiliado para referência)
    if api_data.get('permalink'):
        enriched['permalink'] = api_data['permalink']
        print(f"\n🔗 Link permanente: {api_data['permalink']}")
    
    # 9. ID OFICIAL
    enriched['external_id'] = api_data['id']
    
    # 10. INFORMAÇÕES EXTRAS (se disponíveis)
    if api_data.get('sold_quantity'):
        print(f"📈 Quantidade vendida: {api_data['sold_quantity']} (proprietário)")
    
    print(f"\n✅ ENRIQUECIMENTO CONCLUÍDO!")
    print(f"   Fonte: API Oficial do Mercado Livre")
    print(f"   Qualidade: ⭐⭐⭐⭐⭐ (Dados em tempo real)")
    
    return enriched


def save_staging_json(product_data, original_url):
    """
    Salva o JSON de staging com dados enriquecidos.
    """
    # Detecta a pasta staging
    staging_paths = [
        Path("/app/staging"),
        Path("services/site/staging")
    ]
    
    staging_dir = None
    for path in staging_paths:
        if path.exists() or path.parent.exists():
            staging_dir = path
            break
    
    if staging_dir is None:
        staging_dir = Path("/app/staging")
    
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    # Gera slug e timestamp
    title = product_data['title']
    product_slug = slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Converte preços para número se vieram como string do scraping
    def parse_price(price):
        if isinstance(price, str):
            # Remove "R$", espaços, e converte para float
            return float(price.replace('R$', '').replace(' ', '').strip())
        return float(price) if price else 0
    
    price = parse_price(product_data.get('price', 0))
    old_price = parse_price(product_data.get('old_price', 0))
    
    # Monta o JSON final
    data = {
        "platform": "mercadolivre",
        "external_id": product_data.get('external_id', ''),
        "title": product_data['title'],
        "price": price,
        "oldPrice": old_price,
        "images_local": product_data.get('images_local', f"uploads/{product_slug}"),
        "images": [],
        "link": original_url,  # Preserva link de afiliado
        "tag": product_data.get('tag', 'geral'),
        "disponivel": product_data.get('available_quantity', 1) > 0 if 'available_quantity' in product_data else True,
        "criado_em": timestamp,
        "via_webhook": False
    }
    
    # Campos opcionais
    if 'condition' in product_data:
        data['condition'] = product_data['condition']
    
    if 'available_quantity' in product_data:
        data['available_quantity'] = product_data['available_quantity']
    
    if 'video_id' in product_data:
        data['video_id'] = product_data['video_id']
    
    # Salva
    json_filename = f"{product_slug}_{timestamp}.json"
    json_path = staging_dir / json_filename
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return json_path, data


def main():
    print("=" * 60)
    print("🚀 PREPARAÇÃO HÍBRIDA - SCRAPING + API OFICIAL")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n❌ URL não fornecida!")
        print("\nUso: python3 api_prepare_ml.py <URL>")
        print("Exemplo: python3 api_prepare_ml.py https://mercadolivre.com/sec/ABC123")
        sys.exit(1)
    
    original_url = sys.argv[1]
    print(f"\n🔗 URL: {original_url}\n")
    
    # PASSO 1: Usa scraping HTML (que funciona!) para obter dados básicos
    print("=" * 60)
    print("📥 PASSO 1: SCRAPING HTML (Dados Básicos)")
    print("=" * 60 + "\n")
    
    print("🔗 Resolvendo link e coletando dados via scraping...")
    
    # Chama a função do auto_prepare_ml que FUNCIONA
    product_data_html = scrape_mercadolivre_product(original_url)
    
    if not product_data_html:
        print("\n❌ Falha ao obter dados via scraping")
        print("💡 Verifique se o link do produto está correto")
        sys.exit(1)
    
    print(f"\n✅ Dados básicos obtidos via scraping:")
    print(f"   📦 Produto: {product_data_html['title'][:60]}...")
    print(f"   💰 Preço: R$ {product_data_html.get('price', 'N/A')}")
    print(f"   🖼️  Mídias: {len(product_data_html.get('images', []))}")
    print(f"   🆔 ID: {product_data_html.get('external_id', 'N/A')}")
    
    # NÃO baixa imagens do scraping - a API tem imagens melhores
    print(f"\n⏩ Pulando download de imagens do scraping")
    print(f"   💡 A API fornecerá imagens em alta qualidade")
    
    # PASSO 2: Carrega token OAuth
    print("\n" + "=" * 60)
    print("🔑 PASSO 2: AUTENTICAÇÃO")
    print("=" * 60)
    
    token = load_ml_token()
    if not token:
        print("\n⚠️  Token OAuth não encontrado")
        print("   Usando apenas dados do scraping HTML")
        print("   Para dados mais precisos, execute: make oauth-url")
        
        # Salva apenas com dados do scraping
        json_path, data = save_staging_json(product_data_html, original_url)
        
        print("\n" + "=" * 60)
        print("✅ PREPARAÇÃO CONCLUÍDA (SEM API)")
        print("=" * 60)
        print(f"\n✅ JSON criado: {json_path.name}")
        print(f"\n📋 Próximo passo:")
        print(f"   make stage    # Publicar produto")
        return
    
    print("\n✅ Token OAuth carregado")
    
    # PASSO 3: Enriquece com API oficial
    item_id = product_data_html.get('external_id')
    
    if not item_id:
        print("\n⚠️  ID do produto não encontrado")
        print("   Usando apenas dados do scraping")
        json_path, data = save_staging_json(product_data_html, original_url)
    else:
        # Enriquece os dados
        enriched_data = enrich_with_api(product_data_html, item_id, token, original_url)
        
        # Salva JSON enriquecido
        print("\n" + "=" * 60)
        print("💾 SALVANDO JSON ENRIQUECIDO")
        print("=" * 60)
        
        json_path, data = save_staging_json(enriched_data, original_url)
    
    # Resultado final
    print("\n" + "=" * 60)
    print("✅ PREPARAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    
    print(f"\n✅ JSON criado: {json_path.name}")
    print(f"📂 Categoria: {data['tag']}")
    print(f"📦 Produto: {data['title'][:60]}...")
    print(f"💰 Preço: R$ {data['price']}")
    if data.get('oldPrice', 0) > 0:
        discount = ((data['oldPrice'] - data['price']) / data['oldPrice']) * 100
        print(f"🏷️  De: R$ {data['oldPrice']} ({discount:.0f}% OFF)")
    print(f"🖼️  Imagens: {data['images_local']}")
    print(f"🔗 Link: {data['link']}")
    
    print(f"\n📋 Próximo passo:")
    print(f"   make stage    # Publicar produto no site")
    print()


if __name__ == "__main__":
    main()
