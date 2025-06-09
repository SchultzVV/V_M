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
# from flask import Flask
# from routes.product_routes import product_bp
# from routes.media_routes import media_bp
# from sqlalchemy.orm import declarative_base

# Base = declarative_base()


# app = Flask(__name__)
# app.register_blueprint(product_bp)
# app.register_blueprint(media_bp)
# # Cria as tabelas
# Base.metadata.create_all(bind=engine)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
# main.py
import os
from flask import Flask
from routes.product_routes import product_bp
from models.product import db, Product
from database import engine
from models import Base
from routes.media_routes import media_bp

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@postgres-dev:5432/mydatabase'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db.init_app(app)
# Cria as tabelas no banco de dados (se ainda não existirem)
Base.metadata.create_all(bind=engine)
app.register_blueprint(product_bp)
app.register_blueprint(media_bp)

with app.app_context():
    db.create_all()  # ✅ Cria a tabela 'products' se não existir


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
