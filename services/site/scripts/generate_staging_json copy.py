import os
import json
from datetime import datetime
from slugify import slugify
from minio import Minio
from minio.error import S3Error

# Configurações do MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def format_price(raw):
    return f"R$ {raw.strip()}"

def prompt_user():
    plataforma = input("Plataforma (ex: shopee, amazon): ").strip().lower()
    title = input("Título do produto: ").strip()
    price = format_price(input("Preço atual (ex: 19.90): "))
    old_price = format_price(input("Preço antigo (ex: 49.90): "))
    link = input("Link de afiliado: ").strip()

    images = []
    print("Caminhos das imagens (ENTER vazio para encerrar):")
    while True:
        path = input("Imagem: ").strip()
        if not path:
            break
        images.append(path)

    return plataforma, title, price, old_price, images, link

def upload_images(plataforma, image_paths):
    bucket_name = plataforma
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  # 🔁 único timestamp

    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as e:
        print(f"Erro ao criar/verificar bucket: {e}")
        return []

    urls = []
    for img_path in image_paths:
        if not os.path.isfile(img_path):
            print(f"❌ Arquivo não encontrado: {img_path}")
            continue

        filename = os.path.basename(img_path)
        object_name = f"{timestamp}_{filename}"  # nome padrão da imagem no MinIO

        try:
            minio_client.fput_object(bucket_name, object_name, img_path)
            # ✅ Salva o caminho no formato que o Flask serve
            urls.append(f"/imagens/{bucket_name}/{object_name}")
            print(f"✅ Upload da imagem '{filename}' como '{object_name}'")
        except S3Error as e:
            print(f"❌ Falha no upload de {filename}: {e}")
    return urls

def generate_staging_json(plataforma, title, price, old_price, image_urls, link):
    os.makedirs("staging", exist_ok=True)
    slug = slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"staging/{slug}_{timestamp}.json"

    data = {
        "platform": plataforma,
        "title": title,
        "price": price,
        "oldPrice": old_price,
        "images": image_urls,
        "link": link
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Staging salvo em: {filename}")

if __name__ == "__main__":
    plataforma, title, price, old_price, images, link = prompt_user()
    image_urls = upload_images(plataforma, images)
    generate_staging_json(plataforma, title, price, old_price, image_urls, link)
