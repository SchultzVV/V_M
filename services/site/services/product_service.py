import uuid
import logging
from models.product import Product
from database import SessionLocal
from services.shopee_scraper import scrape_shopee_product

logger = logging.getLogger(__name__)

def get_all_products():
    """Get all products from database with error handling."""
    try:
        db = SessionLocal()
        try:
            return db.query(Product).all()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database error in get_all_products: {e}")
        return []  # Return empty list if database is not available

def save_product(title, price, old_price, image, link, id=None):
    """Save product to database with error handling."""
    try:
        db = SessionLocal()
        try:
            product = Product(
                id=id or str(uuid.uuid4()),  # usa o id do JSON ou gera um novo
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
            return {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "old_price": product.old_price,
                "image": product.image,
                "link": product.link
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database error in save_product: {e}")
        return {
            "error": f"Failed to save product: {e}",
            "id": id or str(uuid.uuid4()),
            "title": title,
            "price": price,
            "old_price": old_price,
            "image": image,
            "link": link
        }


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

