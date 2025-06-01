import json
from flask import Blueprint, request, jsonify, render_template
from services.product_service import save_product, get_all_products
import os
from werkzeug.utils import secure_filename
import shutil

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

        # suporte a múltiplas imagens
        try:
            p.image_list = json.loads(p.image) if p.image.startswith("[") else [p.image]
        except:
            p.image_list = [p.image]

        filtered.append(p)

    return render_template("index.html", products=filtered)


# @product_bp.route("/add_product", methods=["POST"])
# def add_product():
#     data = request.json
#     required_fields = ["title", "price", "oldPrice", "images", "link"]

#     if not all(field in data for field in required_fields):
#         return jsonify({"error": "Campos obrigatórios faltando"}), 400

#     image_paths = []
#     for img_path in data["images"]:
#         if not os.path.isfile(img_path):
#             return jsonify({"error": f"Imagem não encontrada: {img_path}"}), 400

#         filename = secure_filename(os.path.basename(img_path))
#         dest_dir = os.path.join("static", "images")
#         os.makedirs(dest_dir, exist_ok=True)
#         dest_path = os.path.join(dest_dir, filename)

#         try:
#             shutil.copy(img_path, dest_path)
#         except Exception as e:
#             return jsonify({"error": f"Erro ao copiar imagem: {str(e)}"}), 500

#         image_paths.append(f"/static/images/{filename}")

#     try:
#         product = save_product(
#             title=data["title"],
#             price=data["price"],
#             old_price=data["oldPrice"],
#             image=json.dumps(image_paths),  # salva como JSON no campo `image`
#             link=data["link"]
#         )
#         return jsonify({"message": "Produto salvo com sucesso!", "product": product}), 201
#     except Exception as e:
#         return jsonify({"error": f"Erro ao salvar produto: {str(e)}"}), 500
@product_bp.route("/add_product", methods=["POST"])
def add_product():
    data = request.json
    required_fields = ["title", "price", "oldPrice", "images", "link"]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    # Validação simples das imagens (opcional)
    image_paths = []
    for img_path in data["images"]:
        if not isinstance(img_path, str) or not img_path.startswith("/imagens/"):
            return jsonify({"error": f"Caminho de imagem inválido: {img_path}"}), 400
        image_paths.append(img_path)

    try:
        product = save_product(
            title=data["title"],
            price=data["price"],
            old_price=data["oldPrice"],
            image=json.dumps(image_paths),  # salva como JSON no campo `image`
            link=data["link"]
        )
        return jsonify({"message": "Produto salvo com sucesso!", "product": product}), 201
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar produto: {str(e)}"}), 500
