import os
import json
import boto3
from botocore.client import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
BUCKET_NAME = "products"

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="sa-east-1"
)

def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except:
        s3.create_bucket(Bucket=BUCKET_NAME)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key="exemplo.json",
            Body=json.dumps({
                "id": "exemplo",
                "name": "Penteadeira LED",
                "url": "https://br.shp.ee/a6hM34H"
            }),
            ContentType="application/json"
        )
