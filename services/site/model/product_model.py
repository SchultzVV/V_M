# product_model.py
from pydantic import BaseModel
import datetime

class Product(BaseModel):
    id: str
    nome: str
    preco: float
    imagem: str
    link_afiliado: str
    plataforma: str
    categoria: str
    data_criacao: datetime
