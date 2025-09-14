import time
import logging
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to connect to PostgreSQL with more graceful handling
MAX_RETRIES = 5
database_available = False

for i in range(MAX_RETRIES):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Banco conectado com sucesso.")
        database_available = True
        break
    except OperationalError:
        logger.warning(f"⏳ Aguardando PostgreSQL... Tentativa {i+1}/{MAX_RETRIES}")
        time.sleep(2)

if not database_available:
    logger.warning("⚠️ Falha ao conectar no banco de dados. Continuando sem recursos de banco de dados.")

import os
from flask import Flask, jsonify
from routes.product_routes import product_bp
from models.product import db, Product
from models import Base
from routes.media_routes import media_bp
from routes.ai_routes import ai_bp
from routes.index import index_bp

app = Flask(__name__)

# ✅ Middleware para remover tela do Ngrok
@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("POSTGRES_URI") or os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Only initialize database if it's available
if database_available:
    try:
        db.init_app(app)
        # Cria as tabelas no banco de dados (se ainda não existirem)
        Base.metadata.create_all(bind=engine)
        
        with app.app_context():
            db.create_all()  # ✅ Cria a tabela 'products' se não existir
        logger.info("✅ Tabelas do banco de dados criadas com sucesso.")
    except Exception as e:
        logger.warning(f"⚠️ Falha ao inicializar tabelas do banco: {e}")
        database_available = False

# Add health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint to verify application status."""
    status = {
        'status': 'healthy' if database_available else 'degraded',
        'service': 'V&M Site',
        'database': 'connected' if database_available else 'disconnected',
        'message': 'V&M Site está funcionando!' if database_available else 'V&M Site funcionando sem banco de dados'
    }
    return jsonify(status), 200 if database_available else 503

# Register blueprints
app.register_blueprint(product_bp)
app.register_blueprint(media_bp)
app.register_blueprint(ai_bp)
# Uncomment the index blueprint if needed
# app.register_blueprint(index_bp)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
