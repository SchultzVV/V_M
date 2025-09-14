import os
import time
import logging
from flask import Flask
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask application with robust error handling."""
    app = Flask(__name__)
    
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("POSTGRES_URI") or os.environ.get("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Middleware to remove Ngrok warning screen
    @app.after_request
    def skip_ngrok_warning(response):
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response
    
    # Try to initialize database connection (non-blocking)
    database_available = False
    try:
        from database import engine
        # Try to connect to database with limited retries
        MAX_RETRIES = 3
        for i in range(MAX_RETRIES):
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("✅ Database connected successfully.")
                database_available = True
                break
            except OperationalError:
                logger.warning(f"⏳ Waiting for PostgreSQL... Attempt {i+1}/{MAX_RETRIES}")
                time.sleep(1)
        
        if not database_available:
            logger.warning("⚠️ Database not available, continuing without database features.")
    
    except Exception as e:
        logger.warning(f"⚠️ Database initialization failed: {e}")
    
    # Initialize database models and Flask-SQLAlchemy (if database is available)
    if database_available:
        try:
            from models.product import db
            from models import Base
            db.init_app(app)
            
            with app.app_context():
                # Create tables
                Base.metadata.create_all(bind=engine)
                db.create_all()
                logger.info("✅ Database tables created successfully.")
        except Exception as e:
            logger.warning(f"⚠️ Database table creation failed: {e}")
            database_available = False
    
    # Register blueprints (always register, they handle their own database dependencies)
    try:
        from routes.product_routes import product_bp
        from routes.ai_routes import ai_bp
        from routes.media_routes import media_bp
        from routes.index import index_bp
        from routes.health_routes import health_bp
        
        app.register_blueprint(product_bp)
        app.register_blueprint(ai_bp)
        app.register_blueprint(media_bp)
        app.register_blueprint(index_bp)
        app.register_blueprint(health_bp)
        
        logger.info("✅ All routes registered successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to register routes: {e}")
        # Still create the app but with limited functionality
        from routes.health_routes import health_bp
        app.register_blueprint(health_bp)
    
    return app

# Create the app
app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") != "production"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)