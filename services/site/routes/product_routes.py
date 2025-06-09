# routes/product_routes.py

import os
import json
import shutil
from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
from models.product import Product
from services.product_service import save_product, get_all_products

product_bp = Blueprint("product_bp", __name__)


@product_bp.route("/")
def home():
    name_filter = request.args.get("q", "").lower()
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    all_products = get_all_products()
    filtered = []

    for p in all_products:
        if name_filter and name_filter not in p.title.lower():
            continue

        try:
            price_val = float(p.price.replace("R$", "").replace(",", ".").strip())
            old_val = float(p.old_price.replace("R$", "").replace(",", ".").strip()) if p.old_price else None
        except:
            continue

        if min_price:
            try:
                if price_val < float(min_price):
                    continue
            except:
                pass

        if max_price:
            try:
                if price_val > float(max_price):
                    continue
            except:
                pass

        if old_val and old_val > price_val:
            p.discount = round((1 - price_val / old_val) * 100)
        else:
            p.discount = None

        try:
            p.image_list = json.loads(p.image) if p.image.startswith("[") else [p.image]
        except:
            p.image_list = [p.image]

        filtered.append(p)

    return render_template("index.html", products=filtered)


@product_bp.route("/add_product", methods=["POST"])
def add_product():
    data = request.json
    required_fields = ["title", "price", "oldPrice", "images", "link"]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    image_paths = []
    for img_path in data["images"]:
        if not isinstance(img_path, str) or not img_path.startswith("http"):
            return jsonify({"error": f"Caminho de imagem inválido: {img_path}"}), 400
        image_paths.append(img_path)

    # image_paths = []
    # for img_path in data["images"]:
    #     if not isinstance(img_path, str) or not img_path.startswith("/imagens/"):
    #         return jsonify({"error": f"Caminho de imagem inválido: {img_path}"}), 400
    #     image_paths.append(img_path)

    try:
        product = save_product(
            id=data.get("id"),
            title=data["title"],
            price=data["price"],
            old_price=data["oldPrice"],
            image=json.dumps(image_paths),
            link=data["link"]
        )
        # return jsonify({"message": "Produto salvo com sucesso!", "product": product.to_dict()}), 201
        return jsonify({"message": "Produto salvo com sucesso!", "product": product}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao salvar produto: {str(e)}"}), 500


@product_bp.route("/api/products")
def api_products():
    try:
        products = get_all_products()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        return jsonify({"error": f"Erro ao obter produtos: {str(e)}"}), 500
