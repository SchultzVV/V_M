import uuid
from models import Product
from database import SessionLocal
from services.shopee_scraper import scrape_shopee_product

def save_product(title, price, old_price, image, link):
    db = SessionLocal()
    try:
        product = Product(
            id=str(uuid.uuid4()),
            title=title,
            price=price,
            old_price=old_price,
            image=image,
            link=link
        )
        db.add(product)
        db.flush()
        db.refresh(product)
        db.commit()
        return product
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_all_products():
    db = SessionLocal()
    try:
        return db.query(Product).all()
    finally:
        db.close()
