# models/product.py
import uuid
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = "products"

    # id = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    old_price = db.Column(db.String(50))
    image = db.Column(db.Text, nullable=False)  # JSON string com lista de imagens
    link = db.Column(db.Text, nullable=False)

    def to_dict(self):
        from os import getenv
        token = getenv("MEDIA_TOKEN", "secreto123")
        try:
            # Corrige caso seja string JSON ou lista já desserializada
            images = json.loads(self.image) if isinstance(self.image, str) else self.image
            if not isinstance(images, list):
                images = [images]
        except Exception as e:
            print(f"[to_dict] erro ao carregar imagens: {e}")
            images = []
        # try:
        #     images = json.loads(self.image)
        # except:
        #     images = [self.image]
    
        safe_images = []
        # # for img_url in images:
        # #     filename = img_url.split("/")[-1]
        # #     safe_images.append(f"/media/{filename}?token={token}")
    
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "oldPrice": self.old_price,
            "link": self.link,
            "images": images
        }
