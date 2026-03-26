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
from flask import Flask, request
from flask_cors import CORS
from routes.product_routes import product_bp
from models.product import db, Product
from models import Base
from routes.media_routes import media_bp
from routes.ai_routes import ai_bp
from routes.index import index_bp
from routes.webhook_routes import webhook_bp
from routes.auth_routes import auth_bp
from routes.sync_routes import sync_bp
from routes.instagram_routes import instagram_bp
from routes.price_validator_routes import price_validator_bp

app = Flask(__name__)

# ✅ Habilita CORS para frontend em localhost:5173
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    },
    r"/auth/*": {
        "origins": ["http://localhost:5173", "http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# # ✅ Middleware para remover tela do Ngrok e evitar cache agressivo
@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    # Evita cache agressivo do Cloudflare/proxies
    if request.path.startswith('/static/'):
        response.headers["Cache-Control"] = "public, max-age=300"  # Cache de 5 minutos para estáticos
    else:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
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
app.register_blueprint(webhook_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(sync_bp)
app.register_blueprint(instagram_bp)
app.register_blueprint(price_validator_bp)

with app.app_context():
    db.create_all()  # ✅ Cria a tabela 'products' se não existir


if __name__ == "__main__":
    # Verifica se os certificados SSL existem para rodar com HTTPS
    import os.path
    cert_path = "/app/cert.pem"
    key_path = "/app/key.pem"
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print("🔒 Rodando com HTTPS (SSL certificado encontrado)")
        app.run(debug=True, host="0.0.0.0", ssl_context=(cert_path, key_path))
    else:
        print("⚠️  Rodando com HTTP (sem certificado SSL)")
        app.run(debug=True, host="0.0.0.0")
