import os
import json
from datetime import datetime
from slugify import slugify

def format_price(raw):
    return f"R$ {raw.strip()}"

def prompt_user():
    plataforma = input("Plataforma (ex: shopee, amazon, mercadolivre): ").strip().lower()
    
    # External ID para rastreamento via webhook
    external_id = input("ID do produto no marketplace (ex: MLB123456789) [opcional]: ").strip()
    
    title = input("Título do produto: ").strip()
    price = format_price(input("Preço atual (ex: 19.90): "))
    old_price = format_price(input("Preço antigo (ex: 49.90): "))
    link = input("Link de afiliado: ").strip()
    images = input("Caminho da pasta de imagens: ").strip()
    
    # Disponibilidade
    disponivel_input = input("Produto disponível? (s/n) [s]: ").strip().lower()
    disponivel = disponivel_input != 'n'
    
    # Solicitar a tag/categoria do produto
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
    print(f"✅ Categoria selecionada: {tag}")
    
    return plataforma, external_id, title, price, old_price, images, link, tag, disponivel

def generate_staging_json(plataforma, external_id, title, price, old_price, local_paths, link, tag, disponivel):
    os.makedirs("staging", exist_ok=True)
    slug = slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"staging/{slug}_{timestamp}.json"

    data = {
        "platform": plataforma,
        "external_id": external_id if external_id else None,
        "title": title,
        "price": price,
        "oldPrice": old_price,
        "images_local": local_paths,
        "images": [],  # será preenchido posteriormente no stage
        "link": link,
        "tag": tag,
        "disponivel": disponivel,
        "criado_em": timestamp,
        "via_webhook": False
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Staging salvo em: {filename}")
    print(f"🏷️  Tag: {tag}")
    print(f"📦 Plataforma: {plataforma}")
    if external_id:
        print(f"🔗 External ID: {external_id}")
    print(f"✅ Disponível: {'Sim' if disponivel else 'Não'}")

if __name__ == "__main__":
    plataforma, external_id, title, price, old_price, images, link, tag, disponivel = prompt_user()
    generate_staging_json(plataforma, external_id, title, price, old_price, images, link, tag, disponivel)
