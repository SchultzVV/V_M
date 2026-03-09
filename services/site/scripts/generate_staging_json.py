import os
import json
import sys
from datetime import datetime
from slugify import slugify
from pathlib import Path

# Importar funções de scraping do auto_prepare_ml
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

try:
    from auto_prepare_ml import scrape_mercadolivre_product, download_images
except ImportError as e:
    print(f"⚠️  Erro ao importar módulo de scraping: {e}")
    scrape_mercadolivre_product = None
    download_images = None

def format_price(raw):
    return f"R$ {raw.strip()}"

def load_links_from_json():
    """Carrega links do arquivo list_to_prepare.json"""
    json_path = "list_to_prepare_and_stage/list_to_prepare.json"
    
    if not os.path.exists(json_path):
        print(f"⚠️  Arquivo {json_path} não encontrado!")
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def prompt_category_and_subcategory():
    """Solicita categoria e subcategoria do produto"""
    print("\n🏷️  Escolha a categoria do produto:")
    print("1. CD - Casa & Decoração")
    print("2. ME - Moda & Estilo") 
    print("3. E - Eletrônicos")
    print("4. PET - PetShop")
    print("5. Geral (padrão)")
    
    tag_choice = input("Digite o número da categoria (1-5) [5]: ").strip()
    
    tag_map = {
        "1": "CD",
        "2": "ME", 
        "3": "E",
        "4": "PET",
        "5": "geral"
    }
    
    tag = tag_map.get(tag_choice, "geral")
    
    # Mapear subcategorias por categoria
    subcategories_map = {
        "CD": ["banheiro", "sala", "quarto", "cozinha", "corredor", "garagem", "sacada", "area-servico"],
        "ME": ["feminino", "masculino", "infantil", "calcados", "acessorios", "bolsas", "relogios"],
        "E": ["smartphones", "computadores", "audio", "tv", "games", "cameras", "smartwatch", "acessorios"],
        "PET": ["caes", "gatos", "racao", "brinquedos", "higiene", "acessorios", "saude"]
    }
    
    subcategory = None
    if tag in subcategories_map:
        print(f"\n🔖 Subcategorias disponíveis para {tag}:")
        subcats = subcategories_map[tag]
        for idx, subcat in enumerate(subcats, 1):
            print(f"{idx}. {subcat.replace('-', ' ').title()}")
        print(f"{len(subcats) + 1}. Nenhuma (pular)")
        
        subcat_choice = input(f"Digite o número da subcategoria (1-{len(subcats) + 1}) [{len(subcats) + 1}]: ").strip()
        
        try:
            subcat_idx = int(subcat_choice) - 1
            if 0 <= subcat_idx < len(subcats):
                subcategory = subcats[subcat_idx]
                print(f"✅ Subcategoria selecionada: {subcategory}")
        except:
            pass
    
    print(f"✅ Categoria selecionada: {tag}")
    
    return tag, subcategory

def prompt_user_from_links():
    """Processa links do JSON e solicita informações para cada um"""
    data = load_links_from_json()
    
    if not data or 'links' not in data:
        print("❌ Nenhum link encontrado no JSON. Usando modo manual...")
        return prompt_user_manual()
    
    platform = data.get('platform', 'mercadolivre')
    links = data['links']
    
    if not links:
        print("❌ Lista de links vazia. Usando modo manual...")
        return prompt_user_manual()
    
    print(f"\n📦 Encontrados {len(links)} links para processar")
    print(f"🌐 Plataforma: {platform}\n")
    
    products_data = []
    
    for idx, link_obj in enumerate(links, 1):
        url = link_obj.get('url', '')
        if not url:
            continue
            
        print(f"\n{'='*60}")
        print(f"📦 Produto {idx}/{len(links)}")
        print(f"🔗 URL: {url}")
        print('='*60)
        
        # Fazer scraping automático do produto
        if scrape_mercadolivre_product:
            print("\n🔄 Coletando informações do produto automaticamente...")
            product_info = scrape_mercadolivre_product(url)
            
            if not product_info:
                print("\n⚠️  Não foi possível coletar dados do produto. Pulando...")
                continue
            
            # Mostrar informações coletadas
            print(f"\n{'='*60}")
            print(f"📋 INFORMAÇÕES COLETADAS")
            print(f"{'='*60}")
            print(f"📦 Título: {product_info['title']}")
            print(f"💰 Preço: {product_info['price']}")
            print(f"💰 Preço Antigo: {product_info['old_price']}")
            print(f"🖼️  Imagens: {len(product_info['images'])} encontradas")
            print(f"🆔 External ID: {product_info['external_id']}")
            if product_info.get('has_discount'):
                print(f"🎉 Desconto: {product_info['discount_percentage']}% OFF")
            print(f"{'='*60}\n")
            
            # Baixar imagens automaticamente
            print("\n📥 Baixando imagens do produto...")
            if download_images:
                # Gerar slug do produto para nome da pasta
                from slugify import slugify
                product_slug = slugify(product_info['title'])
                
                images_folder = download_images(
                    product_info['images'],
                    product_slug
                )
                
                if images_folder:
                    print(f"✅ Imagens salvas em: {images_folder}")
                else:
                    images_folder = ""
                    print("⚠️  Não foi possível baixar as imagens")
            else:
                images_folder = ""
                print("⚠️  Função de download não disponível")
            
            # Perguntar apenas categoria e subcategoria
            tag, subcategory = prompt_category_and_subcategory()
            
            # Sempre disponível quando usando prepare-products
            disponivel = True
            
            products_data.append({
                'platform': platform,
                'external_id': product_info['external_id'],
                'title': product_info['title'],
                'price': product_info['price'],
                'old_price': product_info['old_price'],
                'images': images_folder,
                'link': url,
                'tag': tag,
                'subcategory': subcategory,
                'disponivel': disponivel
            })
            
        else:
            # Fallback: modo manual
            print("\n⚠️  Scraping automático não disponível. Usando modo manual...")
            
            tag, subcategory = prompt_category_and_subcategory()
            external_id = input("ID do produto no marketplace (ex: MLB123456789) [opcional]: ").strip()
            title = input("Título do produto: ").strip()
            
            if not title:
                print("⚠️  Título não pode ser vazio. Pulando este produto...")
                continue
            
            price = format_price(input("Preço atual (ex: 19.90): "))
            old_price = format_price(input("Preço antigo (ex: 49.90): "))
            images = input("Caminho da pasta de imagens: ").strip()
            
            # Sempre disponível quando usando prepare-products
            disponivel = True
            
            products_data.append({
                'platform': platform,
                'external_id': external_id if external_id else None,
                'title': title,
                'price': price,
                'old_price': old_price,
                'images': images,
                'link': url,
                'tag': tag,
                'subcategory': subcategory,
                'disponivel': disponivel
            })
    
    return products_data

def prompt_user_manual():
    """Modo manual antigo (um produto por vez)"""
    plataforma = input("Plataforma (ex: shopee, amazon, mercadolivre): ").strip().lower()
    
    # External ID para rastreamento via webhook
    external_id = input("ID do produto no marketplace (ex: MLB123456789) [opcional]: ").strip()
    
    title = input("Título do produto: ").strip()
    price = format_price(input("Preço atual (ex: 19.90): "))
    old_price = format_price(input("Preço antigo (ex: 49.90): "))
    link = input("Link de afiliado: ").strip()
    images = input("Caminho da pasta de imagens: ").strip()
    
    # Solicitar categoria e subcategoria
    tag, subcategory = prompt_category_and_subcategory()
    
    # Sempre disponível quando usando prepare-products
    disponivel = True
    
    return [{
        'platform': plataforma,
        'external_id': external_id if external_id else None,
        'title': title,
        'price': price,
        'old_price': old_price,
        'images': images,
        'link': link,
        'tag': tag,
        'subcategory': subcategory,
        'disponivel': disponivel
    }]

def generate_staging_json(product_data):
    """Gera arquivo JSON de staging para um produto"""
    
    # Mapear tags para nomes de pastas
    tag_to_folder = {
        "CD": "casa-decoracao",
        "ME": "moda-estilo",
        "E": "eletronicos",
        "PET": "petshop",
        "geral": "geral"
    }
    
    tag = product_data['tag']
    subcategory = product_data.get('subcategory')
    
    # Determinar o caminho da pasta baseado em categoria e subcategoria
    category_folder = tag_to_folder.get(tag, "geral")
    
    if subcategory:
        # staging/eletronicos/smartphones/
        staging_path = f"staging/{category_folder}/{subcategory}"
    else:
        # staging/eletronicos/
        staging_path = f"staging/{category_folder}"
    
    # Criar diretórios se não existirem
    os.makedirs(staging_path, exist_ok=True)
    
    title = product_data['title']
    slug = slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{staging_path}/{slug}_{timestamp}.json"

    data = {
        "platform": product_data['platform'],
        "external_id": product_data['external_id'],
        "title": title,
        "price": product_data['price'],
        "oldPrice": product_data['old_price'],
        "images_local": product_data['images'],
        "images": [],  # será preenchido posteriormente no stage
        "link": product_data['link'],
        "tag": product_data['tag'],
        "subcategory": product_data.get('subcategory'),
        "disponivel": product_data['disponivel'],
        "criado_em": timestamp,
        "via_webhook": False
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Staging salvo em: {filename}")
    print(f"🏷️  Tag: {data['tag']}")
    if data.get('subcategory'):
        print(f"🔖 Subcategoria: {data['subcategory']}")
    print(f"📦 Plataforma: {data['platform']}")
    if data['external_id']:
        print(f"🔗 External ID: {data['external_id']}")
    print(f"✅ Disponível: {'Sim' if data['disponivel'] else 'Não'}")
    
    return filename

if __name__ == "__main__":
    # Tenta carregar do JSON primeiro, senão usa modo manual
    print("🚀 Iniciando preparação de produtos...")
    print("\n📋 Verificando arquivo list_to_prepare.json...")
    
    products_data = prompt_user_from_links()
    
    if not products_data:
        print("\n❌ Nenhum produto para processar.")
        exit(1)
    
    print(f"\n{'='*60}")
    print(f"📦 Gerando arquivos de staging para {len(products_data)} produto(s)...")
    print('='*60)
    
    generated_files = []
    for product in products_data:
        filename = generate_staging_json(product)
        generated_files.append(filename)
    
    print(f"\n{'='*60}")
    print(f"✅ Processo concluído!")
    print(f"📁 {len(generated_files)} arquivo(s) gerado(s):")
    for f in generated_files:
        print(f"   - {f}")
    print('='*60)
