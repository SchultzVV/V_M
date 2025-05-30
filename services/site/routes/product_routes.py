from flask import Blueprint, request, jsonify, render_template, url_for
from services.product_service import save_product, get_all_products, scrape_shopee_product
import os

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

        # remove "R$" e substitui vírgula por ponto
        try:
            price_val = float(p.price.replace("R$", "").replace(",", ".").strip())
            old_val = float(p.old_price.replace("R$", "").replace(",", ".").strip()) if p.old_price else None
        except:
            continue

        # Filtros de preço
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

        # Cálculo da % de desconto
        if old_val and old_val > price_val:
            p.discount = round((1 - price_val / old_val) * 100)
        else:
            p.discount = None

        # Ajuste no caminho da imagem caso venha absoluta
        if os.path.isabs(p.image):
            # transforma em relativo ao /static/
            rel_path = os.path.relpath(p.image, os.path.join(os.getcwd(), "services", "site", "static"))
            p.image = rel_path.replace("\\", "/")  # suporte Windows/Linux

        filtered.append(p)

    return render_template("index.html", products=filtered)


@product_bp.route("/add_product", methods=["POST"])
def add_product():
    data = request.json
    required_fields = ["title", "price", "oldPrice", "image", "link"]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    image_path = data["image"]
    if os.path.isabs(image_path):
        try:
            rel_path = os.path.relpath(image_path, os.path.join(os.getcwd(), "services", "site", "static"))
            image_path = rel_path.replace("\\", "/")
        except Exception as e:
            return jsonify({"error": f"Erro ao processar caminho da imagem: {str(e)}"}), 400

    try:
        product = save_product(
            title=data["title"],
            price=data["price"],
            old_price=data["oldPrice"],
            image=image_path,
            link=data["link"]
        )
        return jsonify({
            "message": "Produto salvo com sucesso!",
            "product": {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "old_price": product.old_price,
                "image": product.image,
                "link": product.link
            }
        }), 201
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar produto: {str(e)}"}), 500