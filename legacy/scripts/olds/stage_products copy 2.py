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

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def upload_images(plataforma, local_paths):
    bucket_name = plataforma
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    urls = []

    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            # Permitir acesso público
            minio_client.set_bucket_policy(bucket_name, json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                }]
            }))
    except S3Error as e:
        print(f"[ERRO] Bucket: {e}")
        return []

    for path in local_paths:
        if not os.path.isfile(path):
            print(f"⚠️  Imagem não encontrada localmente: {path}")
            continue

        filename = os.path.basename(path)
        object_name = f"{timestamp}_{filename}"

        try:
            minio_client.fput_object(bucket_name, object_name, path)
            public_url = f"http://{MINIO_ENDPOINT}/{bucket_name}/{object_name}"
            urls.append(public_url)
            print(f"✅ Upload: {object_name}")
        except S3Error as e:
            print(f"❌ Falha no upload de {filename}: {e}")

    return urls

# Upload das imagens para o MinIO
# def upload_images(plataforma, local_paths):
#     bucket_name = plataforma
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     urls = []

#     try:
#         if not minio_client.bucket_exists(bucket_name):
#             minio_client.make_bucket(bucket_name)
#     except S3Error as e:
#         print(f"[ERRO] Bucket: {e}")
#         return []

#     for path in local_paths:
#         if not os.path.isfile(path):
#             print(f"⚠️  Imagem não encontrada localmente: {path}")
#             continue

#         filename = os.path.basename(path)
#         object_name = f"{timestamp}_{filename}"

#         try:
#             minio_client.fput_object(bucket_name, object_name, path)
#             urls.append(f"/imagens/{bucket_name}/{object_name}")
#             print(f"✅ Upload: {object_name}")
#         except S3Error as e:
#             print(f"❌ Falha no upload de {filename}: {e}")

#     return urls

# Processamento de arquivos
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed_files = set(f.read().splitlines())
else:
    processed_files = set()

newly_processed = []

for filename in os.listdir(STAGING_DIR):
    if not filename.endswith(".json") or filename in processed_files or filename == ".processed":
        continue

    path = os.path.join(STAGING_DIR, filename)
    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Gera os caminhos de imagem remotos a partir dos locais
        plataforma = data["platform"]
        local_paths = data.get("images_local", [])

        image_urls = upload_images(plataforma, local_paths)

        if not image_urls:
            print(f"[ERRO] Nenhuma imagem válida para: {filename}")
            continue

        # Atualiza o campo images e envia
        data["images"] = image_urls

        response = requests.post(API_ENDPOINT, json=data)

        if response.status_code == 201:
            print(f"[OK] Produto adicionado: {filename}")
            newly_processed.append(filename)
        else:
            print(f"[ERRO] {filename} - {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[FALHA] {filename} - {str(e)}")

# Atualiza o arquivo .processed
if newly_processed:
    with open(PROCESSED_FILE, "a") as f:
        for fname in newly_processed:
            f.write(fname + "\n")
