# scripts/stage_products.py

import os
import json
import requests
from datetime import datetime
from minio import Minio
from minio.error import S3Error

STAGING_DIR = "staging"
PROCESSED_FILE = os.path.join(STAGING_DIR, ".processed")
API_ENDPOINT = "http://localhost:5000/add_product"

# Configuração do MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", f"http://{MINIO_ENDPOINT}")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def upload_images(bucket_name, local_paths):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    urls = []

    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as e:
        print(f"[ERRO] Bucket: {e}")
        return []

    for path in local_paths:
        if not os.path.isfile(path):
            print(f"⚠️  Imagem não encontrada: {path}")
            continue

        filename = os.path.basename(path)
        object_name = f"{timestamp}_{filename}"

        try:
            minio_client.fput_object(bucket_name, object_name, path)
            public_url = f"{MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_name}"
            urls.append(public_url)
            print(f"✅ Upload: {public_url}")
        except S3Error as e:
            print(f"❌ Falha no upload {filename}: {e}")

    return urls

# Leitura de arquivos processados
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed_files = set(f.read().splitlines())
else:
    processed_files = set()

newly_processed = []

for filename in os.listdir(STAGING_DIR):
    if not filename.endswith(".json") or filename == ".processed" or filename in processed_files:
        continue

    path = os.path.join(STAGING_DIR, filename)

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Valida e coleta info
        platform = data["platform"]
        local_imgs = data.get("images_local", [])

        # Upload imagens
        urls = upload_images(platform, local_imgs)

        if not urls:
            print(f"[ERRO] Sem imagens válidas: {filename}")
            continue

        data["images"] = urls  # Substitui campo
        data.pop("images_local", None)

        # Envia para o endpoint
        resp = requests.post(API_ENDPOINT, json=data)

        if resp.status_code == 201:
            print(f"[✔] Produto salvo: {filename}")
            newly_processed.append(filename)
        else:
            print(f"[ERRO] {filename}: {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"[FALHA] {filename}: {str(e)}")

# Atualiza .processed
if newly_processed:
    with open(PROCESSED_FILE, "a") as f:
        for name in newly_processed:
            f.write(name + "\n")
