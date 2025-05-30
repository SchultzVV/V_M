import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from database import engine

# Aguarda o PostgreSQL estar pronto
MAX_RETRIES = 10
for i in range(MAX_RETRIES):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Banco conectado com sucesso.")
        break
    except OperationalError:
        print(f"⏳ Aguardando PostgreSQL... Tentativa {i+1}/{MAX_RETRIES}")
        time.sleep(2)
else:
    print("❌ Falha ao conectar no banco de dados.")
    exit(1)

# agora importa o restante
from flask import Flask
from routes.product_routes import product_bp
from models import Base

app = Flask(__name__)
app.register_blueprint(product_bp)

# Cria as tabelas
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
