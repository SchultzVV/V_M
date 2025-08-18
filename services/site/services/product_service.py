import uuid
from models.product import Product
from database import SessionLocal
from services.shopee_scraper import scrape_shopee_product


def get_all_products():
    db = SessionLocal()
    try:
        return db.query(Product).all()
    finally:
        db.close()

def get_products_by_tag(tag):
    """Busca produtos que contenham a tag especificada"""
    db = SessionLocal()
    try:
        return db.query(Product).filter(Product.tags.contains(f'"{tag}"')).all()
    finally:
        db.close()

def save_product(title, price, old_price, image, link, id=None, tags=None):
    db = SessionLocal()
    try:
        product = Product(
            id=id or str(uuid.uuid4()),  # usa o id do JSON ou gera um novo
            title=title,
            price=price,
            old_price=old_price,
            image=image,
            link=link,
            tags=tags or '["geral"]'  # Default para "geral" se não especificado
        )
        db.add(product)
        db.flush()
        db.refresh(product)
        db.commit()
        return {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "old_price": product.old_price,
            "image": product.image,
            "link": product.link,
            "tags": product.tags
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# def save_product(title, price, old_price, image, link):
#     db = SessionLocal()
#     try:
#         product = Product(
#             id=str(uuid.uuid4()),
#             title=title,
#             price=price,
#             old_price=old_price,
#             image=image,
#             link=link
#         )
#         db.add(product)
#         db.flush()
#         db.refresh(product)
#         db.commit()
#         # return product
#         return {
#             "id": product.id,
#             "title": product.title,
#             "price": product.price,
#             "old_price": product.old_price,
#             "image": product.image,
#             "link": product.link
#         }

#     except Exception as e:
#         db.rollback()
#         raise e
#     finally:
#         db.close()

