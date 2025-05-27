import uuid
import json
from utils.minio_client import s3, BUCKET_NAME
from scraper.shopee_scraper import scrape_shopee_with_playwright


def load_products_from_minio():
    products = []
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        objects = response.get("Contents", [])
        for obj in objects:
            obj_data = s3.get_object(Bucket=BUCKET_NAME, Key=obj["Key"])
            content = obj_data["Body"].read().decode("utf-8")
            products.append(json.loads(content))
    except Exception as e:
        print("❌ Erro ao carregar produtos do MinIO:", e)
    return products


def save_product_to_minio(name, url, image, price):
    product_data = {
        "id": uuid.uuid4().hex,
        "name": name,
        "url": url,
        "image": image,
        "price": price
    }

    key = f"{product_data['id']}.json"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(product_data, ensure_ascii=False),
        ContentType="application/json"
    )

    return product_data


def scrape_shopee_product(url):
    """
    Wrapper para extrair nome, imagem e preço de um link Shopee.
    Utiliza Playwright para renderizar a página.
    """
    return scrape_shopee_with_playwright(url)
