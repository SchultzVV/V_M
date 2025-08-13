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

import os
from flask import Flask
from routes.product_routes import product_bp
from models.product import db, Product
from models import Base
from routes.media_routes import media_bp
from routes.ai_routes import ai_bp
from routes.index import index_bp

app = Flask(__name__)

# # ✅ Middleware para remover tela do Ngrok
@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response
# app.register_blueprint(index_bp)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("POSTGRES_URI") or os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
# Cria as tabelas no banco de dados (se ainda não existirem)
Base.metadata.create_all(bind=engine)
app.register_blueprint(product_bp)
app.register_blueprint(media_bp)
app.register_blueprint(ai_bp)

with app.app_context():
    db.create_all()  # ✅ Cria a tabela 'products' se não existir


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
