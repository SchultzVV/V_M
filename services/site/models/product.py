import uuid
import json
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
import os

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    old_price = db.Column(db.String(50))
    image = db.Column(db.Text, nullable=False)  # JSON string com lista de imagens
    link = db.Column(db.Text, nullable=False)

    def to_dict(self):
        token = os.getenv("MEDIA_TOKEN", "secreto123")
        try:
            # Garante que é uma lista de strings
            images = json.loads(self.image) if isinstance(self.image, str) else self.image
            if not isinstance(images, list):
                images = [images]
        except Exception as e:
            print(f"[to_dict] erro ao carregar imagens: {e}")
            images = []

        safe_images = []
        bucket_name = None
        for img_url in images:
            try:
                parsed = urlparse(img_url)
                parts = parsed.path.strip("/").split("/", 1)
                if len(parts) != 2:
                    print(f"[to_dict] URL inválida: {img_url}")
                    continue
                bucket, filename = parts
                proxy_url = f"/media/{bucket}/{filename}?token={token}"
                safe_images.append(proxy_url)
                if not bucket_name:
                    bucket_name = bucket  # pega o primeiro bucket válido
            except Exception as e:
                print(f"[to_dict] erro ao processar imagem: {e}")
                continue

        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "oldPrice": self.old_price,
            "link": self.link,
            "images": safe_images,
            "bucketName": bucket_name or "desconhecido"
        }
