import os
import json
import re
from minio import Minio
from minio.error import S3Error

STAGING_DIR = "staging"

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def check_image_exists(bucket, filename):
    try:
        minio_client.stat_object(bucket, filename)
        return True
    except S3Error:
        return False

def main():
    for fname in os.listdir(STAGING_DIR):
        if not fname.endswith(".json") or fname == ".processed":
            continue

        path = os.path.join(STAGING_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"\n🔍 Verificando imagens em: {fname}")
        for img in data.get("images", []):
            match = re.match(r"^/imagens/([^/]+)/(.+)$", img)
            if not match:
                print(f"⚠️  Caminho inválido: {img}")
                continue

            bucket, filename = match.groups()
            if check_image_exists(bucket, filename):
                print(f"✅ {img}")
            else:
                print(f"❌ {img} - NÃO ENCONTRADA NO MINIO")

if __name__ == "__main__":
    main()
