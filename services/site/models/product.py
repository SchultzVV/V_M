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
    tags = db.Column(db.Text, default='["geral"]')  # JSON string com as tags

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
        
        # Ordenar imagens alfabeticamente pelo nome do arquivo
        sorted_images = sorted(images, key=lambda url: urlparse(url).path.split("/")[-1].lower())
        
        for img_url in sorted_images:
            try:
                parsed = urlparse(img_url)
                path_parts = parsed.path.strip("/").split("/")
                
                # Suporta tanto estrutura antiga (bucket/arquivo) quanto nova (bucket/pasta/arquivo)
                if len(path_parts) == 2:
                    # Estrutura antiga: bucket/arquivo
                    bucket, filename = path_parts
                    proxy_url = f"/media/{bucket}/{filename}?token={token}"
                elif len(path_parts) >= 3:
                    # Estrutura nova: bucket/pasta/arquivo ou bucket/pasta/subpasta/arquivo
                    bucket = path_parts[0]
                    remaining_path = "/".join(path_parts[1:])
                    proxy_url = f"/media/{bucket}/{remaining_path}?token={token}"
                else:
                    print(f"[to_dict] URL inválida: {img_url}")
                    continue
                    
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
            "bucketName": bucket_name or "desconhecido",
            "tags": json.loads(self.tags) if hasattr(self, 'tags') and self.tags else ["geral"]
        }
