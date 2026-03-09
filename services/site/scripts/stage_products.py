import os
import json
import requests
from pathlib import Path
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Desabilitar warnings de SSL para desenvolvimento
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

STAGING_DIR = "staging"
API_ENDPOINT = "https://localhost:5000/add_product"

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

# Permissão pública: política do tipo download
DOWNLOAD_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetObject"],
        "Resource": ["arn:aws:s3:::{bucket}/*"]
    }]
}

def set_bucket_public(bucket_name):
    policy = json.dumps(DOWNLOAD_POLICY).replace("{bucket}", bucket_name)
    try:
        minio_client.set_bucket_policy(bucket_name, policy)
        print(f"🔓 Bucket `{bucket_name}` agora é público (download)")
    except S3Error as e:
        print(f"⚠️  Falha ao definir política pública: {e}")

def upload_images(bucket_name, local_paths):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    urls = []

    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            set_bucket_public(bucket_name)
    except S3Error as e:
        print(f"[ERRO] Bucket: {e}")
        return []

    if not os.path.isdir(local_paths):
        print(f"❌ Pasta não encontrada: {local_paths}")
        return urls
    
    # Extrair o nome da pasta do produto (ex: "racao" de "uploads/racao")
    product_folder_name = os.path.basename(local_paths.rstrip('/'))
    print(f"📁 Criando pasta do produto: {product_folder_name}")
    
    # Listar arquivos em ordem alfabética
    filenames = sorted(os.listdir(local_paths))
    
    for filename in filenames:
        path = os.path.join(local_paths, filename)
        if not os.path.isfile(path):
           continue  # ignora subpastas, etc.
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
           continue  # ignora arquivos que não são imagem

        # Criar estrutura: bucket/produto/timestamp_filename
        object_name = f"{product_folder_name}/{timestamp}_{filename}"

        try:
            minio_client.fput_object(bucket_name, object_name, path)
            public_url = f"{MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_name}"
            urls.append(public_url)
            print(f"✅ Upload: {public_url}")
        except S3Error as e:
            print(f"❌ Falha no upload {filename}: {e}")

    return urls

def ensure_fallback_bucket():
    fallback_dir = "uploads/fallback_img"
    bucket = "fallbacks"

    try:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
            set_bucket_public(bucket)

        for img in os.listdir(fallback_dir):
            path = os.path.join(fallback_dir, img)
            if os.path.isfile(path):
                try:
                    minio_client.fput_object(bucket, img, path)
                    print(f"✅ Fallback enviado: {bucket}/{img}")
                except S3Error as e:
                    print(f"❌ Falha fallback {img}: {e}")
    except Exception as e:
        print(f"⚠️  Erro ao preparar bucket fallback: {e}")

# --- Execução principal ---
ensure_fallback_bucket()

PROCESSED_FILE = os.path.join(STAGING_DIR, ".processed")

if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed_files = set(f.read().splitlines())
else:
    processed_files = set()

newly_processed = []

# Busca recursiva em todas as subpastas de staging (eletronicos/smartphones/, etc.)
staging_path = Path(STAGING_DIR)
all_json = sorted(staging_path.rglob("*.json"))

# Filtrar já processados e .processed (usa path relativo como chave)
json_files = [
    p for p in all_json
    if str(p.relative_to(staging_path)) not in processed_files
]

if not json_files:
    print("ℹ️  Nenhum produto novo em staging para processar.")

for json_path in json_files:
    rel_path = str(json_path.relative_to(staging_path))  # ex: eletronicos/smartphones/produto_xxx.json

    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        platform = data["platform"]
        local_imgs = data.get("images_local", [])
        tag = data.get("tag", "geral")
        subcategory = data.get("subcategory", "")

        urls = upload_images(platform, local_imgs)

        if not urls:
            print(f"[ERRO] Sem imagens válidas: {rel_path}")
            continue

        data["images"] = urls
        data.pop("images_local", None)

        payload = {
            "title": data["title"],
            "price": data["price"],
            "oldPrice": data["oldPrice"],
            "images": data["images"],
            "link": data["link"],
            "tag": tag,
            "subcategory": subcategory,
            "disponivel": data.get("disponivel", True),
            "external_id": data.get("external_id", ""),
            "platform": platform,
        }

        resp = requests.post(API_ENDPOINT, json=payload, verify=False)

        if resp.status_code == 201:
            print(f"[✔] Produto salvo: {rel_path} (Tag: {tag}/{subcategory})")
            newly_processed.append(rel_path)
        else:
            print(f"[ERRO] {rel_path}: {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"[FALHA] {rel_path}: {str(e)}")

if newly_processed:
    with open(PROCESSED_FILE, "a") as f:
        for name in newly_processed:
            f.write(name + "\n")
