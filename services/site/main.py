from flask import Flask
from routes.product_routes import product_bp
from utils.minio_client import ensure_bucket

app = Flask(__name__)
app.register_blueprint(product_bp)

if __name__ == "__main__":
    ensure_bucket()
    app.run(host="0.0.0.0", port=5000)
