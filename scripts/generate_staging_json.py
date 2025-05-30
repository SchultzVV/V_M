import os
import json
from datetime import datetime
from slugify import slugify

def format_price(raw):
    return f"R$ {raw.strip()}"

def prompt_user():
    title = input("Título do produto: ").strip()
    price = format_price(input("Preço atual (ex: 19.90): "))
    old_price = format_price(input("Preço antigo (ex: 49.90): "))
    link = input("Link de afiliado: ").strip()

    images = []
    print("Caminhos das imagens (digite uma por vez, pressione ENTER vazio para terminar):")
    while True:
        path = input("Imagem: ").strip()
        if not path:
            break
        images.append(path)

    return title, price, old_price, images, link

def generate_staging_json(title, price, old_price, images, link):
    os.makedirs("staging", exist_ok=True)

    slug = slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"staging/{slug}_{timestamp}.json"

    data = {
        "title": title,
        "price": price,
        "oldPrice": old_price,
        "images": images,
        "link": link
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Staging salvo em: {filename}")

if __name__ == "__main__":
    title, price, old_price, images, link = prompt_user()
    generate_staging_json(title, price, old_price, images, link)
