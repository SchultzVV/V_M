"""
Script para inicializar o banco de dados e popular com dados de teste
"""
import asyncio
from sqlalchemy import create_engine
from shared.database import Base, SessionLocal, UserModel, ProductModel
from shared.schemas import ConsentStatus
import uuid
import json

DATABASE_URL = "postgresql://user:password@localhost:5432/recommendations_db"


def init_database():
    """Cria todas as tabelas"""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados inicializado")


def seed_products():
    """Popula banco com produtos de exemplo"""
    db = SessionLocal()
    
    products = [
        {
            "id": "prod-001",
            "title": "Fone de Ouvido Bluetooth",
            "description": "Som de alta qualidade com cancelamento de ruído",
            "price": 299.90,
            "discount": 25,
            "category": "electronics",
            "tags": ["audio", "wireless", "tech"]
        },
        {
            "id": "prod-002",
            "title": "Tênis de Corrida Nike",
            "description": "Confortável e estiloso para suas corridas",
            "price": 399.90,
            "discount": 15,
            "category": "fashion",
            "tags": ["shoes", "sports", "nike"]
        },
        {
            "id": "prod-003",
            "title": "Smartwatch Apple Watch",
            "description": "Monitore sua saúde e fitness",
            "price": 2499.90,
            "discount": 10,
            "category": "electronics",
            "tags": ["wearable", "fitness", "apple"]
        },
        {
            "id": "prod-004",
            "title": "Mochila para Laptop",
            "description": "Espaçosa e resistente para seu notebook",
            "price": 189.90,
            "discount": 20,
            "category": "accessories",
            "tags": ["bags", "laptop", "travel"]
        },
        {
            "id": "prod-005",
            "title": "Câmera DSLR Canon",
            "description": "Capture momentos incríveis com qualidade profissional",
            "price": 3999.90,
            "discount": 30,
            "category": "electronics",
            "tags": ["camera", "photography", "canon"]
        },
        {
            "id": "prod-006",
            "title": "Cafeteira Espresso",
            "description": "Café de qualidade na sua casa",
            "price": 899.90,
            "discount": 18,
            "category": "home",
            "tags": ["coffee", "kitchen", "appliance"]
        },
        {
            "id": "prod-007",
            "title": "Livro: Clean Code",
            "description": "Manual essencial para desenvolvedores",
            "price": 89.90,
            "discount": 5,
            "category": "books",
            "tags": ["programming", "education", "tech"]
        },
        {
            "id": "prod-008",
            "title": "Mouse Gamer Logitech",
            "description": "Precisão e conforto para gamers",
            "price": 249.90,
            "discount": 22,
            "category": "electronics",
            "tags": ["gaming", "peripherals", "logitech"]
        },
        {
            "id": "prod-009",
            "title": "Óculos de Sol Ray-Ban",
            "description": "Estilo clássico com proteção UV",
            "price": 499.90,
            "discount": 12,
            "category": "fashion",
            "tags": ["sunglasses", "rayban", "accessories"]
        },
        {
            "id": "prod-010",
            "title": "Garrafa Térmica Stanley",
            "description": "Mantenha suas bebidas na temperatura ideal",
            "price": 199.90,
            "discount": 15,
            "category": "accessories",
            "tags": ["bottle", "thermal", "outdoor"]
        }
    ]
    
    for p in products:
        product = ProductModel(
            id=p["id"],
            title=p["title"],
            description=p["description"],
            price=p["price"],
            discount=p["discount"],
            category=p["category"],
            tags=p["tags"],
            embedding_vector=None  # Será gerado depois
        )
        db.add(product)
    
    db.commit()
    print(f"✅ {len(products)} produtos adicionados")
    db.close()


def create_test_user():
    """Cria usuário de teste"""
    db = SessionLocal()
    
    user = UserModel(
        id=str(uuid.uuid4()),
        instagram_id="test_instagram_123",
        consent_status=ConsentStatus.PENDING,
        scopes=[]
    )
    db.add(user)
    db.commit()
    
    print(f"✅ Usuário de teste criado: {user.id}")
    db.close()
    
    return user.id


if __name__ == "__main__":
    print("🚀 Inicializando sistema...")
    
    # 1. Criar tabelas
    init_database()
    
    # 2. Popular produtos
    seed_products()
    
    # 3. Criar usuário de teste
    test_user_id = create_test_user()
    
    print("\n" + "="*60)
    print("✅ Setup completo!")
    print("="*60)
    print(f"\n📝 Usuário de teste: {test_user_id}")
    print("\n🔗 Próximos passos:")
    print("1. Configure suas credenciais no .env")
    print("2. Execute: docker-compose -f docker-compose.recommendations.yaml up")
    print("3. Acesse: http://localhost:8000/docs")
    print("\n💡 Exemplo de request:")
    print(f"""
    POST http://localhost:8000/recommendations?user_id={test_user_id}
    """)
