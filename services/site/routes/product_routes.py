from flask import Blueprint, request, jsonify, render_template
from services.product_service import (
    load_products_from_minio,
    save_product_to_minio,
    scrape_shopee_product
)

product_bp = Blueprint("product_bp", __name__)

@product_bp.route("/")
def home():
    products = load_products_from_minio()
    return render_template("index.html", products=products)

@product_bp.route("/add_product", methods=["POST"])
def add_product():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL do produto é obrigatória"}), 400

    try:
        scraped = scrape_shopee_product(url)
    except Exception as e:
        return jsonify({"error": f"Erro ao extrair dados: {str(e)}"}), 500

    product = save_product_to_minio(scraped["name"], url, scraped["image"], scraped["price"])

    return jsonify({"message": "Produto salvo com sucesso!", "product": product})
