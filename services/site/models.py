from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    title = Column(String)
    price = Column(String)
    old_price = Column(String)
    image = Column(String)
    link = Column(String)
