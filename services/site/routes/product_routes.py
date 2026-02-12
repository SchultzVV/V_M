# routes/product_routes.py

import os
import json
import shutil
import requests
from flask import Blueprint, request, jsonify, render_template, Response
from werkzeug.utils import secure_filename
from models.product import Product
from services.product_service import save_product, get_all_products, get_products_by_tag
from services.seo_service import seo_service

product_bp = Blueprint("product_bp", __name__)


@product_bp.route("/")
def index():
    # Exibe todos os produtos na página principal
    products = get_all_products()
    
    # Gerar meta tags otimizadas
    meta_tags = seo_service.generate_meta_tags(
        title="Promoções e Ofertas Incríveis",
        description="Catálogo de sobrevivência pós-sistema! As melhores promoções da internet em um só lugar. Eletrônicos, Casa, Moda e muito mais!",
        keywords=["promoções", "ofertas", "descontos", "loja online", "eletrônicos", "casa", "moda"]
    )
    
    # Gerar schema da organização
    organization_schema = seo_service.generate_organization_schema(
        organization_name="V&M - Lojinha",
        social_profiles=[
            "https://www.instagram.com/seu_perfil",
            "https://www.facebook.com/sua_pagina"
        ]
    )
    
    return render_template("index.html", meta_tags=meta_tags, organization_schema=organization_schema)

@product_bp.route("/secao1")
def secao1():
    # Casa & Decoração
    return render_template("secao1.html")

@product_bp.route("/secao2")
def secao2():
    # Moda & Estilo
    return render_template("secao2.html")

@product_bp.route("/secao3")
def secao3():
    # Eletrônicos
    return render_template("secao3.html")

@product_bp.route("/secao4")
def secao4():
    # PetShop
    return render_template("secao4.html")


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

    # Usa a tag do JSON se disponível, senão faz auto-categorização
    if "tag" in data and data["tag"]:
        tags = ["geral", data["tag"]]  # Sempre inclui "geral" + a tag específica
    else:
        # Auto-categorização baseada no título do produto (fallback)
        tags = auto_categorize_product(data["title"])

    try:
        product = save_product(
            id=data.get("id"),
            title=data["title"],
            price=data["price"],
            old_price=data["oldPrice"],
            image=json.dumps(image_paths),
            link=data["link"],
            tags=json.dumps(tags)
        )
        return jsonify({"message": "Produto salvo com sucesso!", "product": product}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao salvar produto: {str(e)}"}), 500

def auto_categorize_product(title):
    """Auto-categoriza produtos baseado no título"""
    title_lower = title.lower()
    tags = ["geral"]  # Todo produto tem a tag geral
    
    # Casa & Decoração
    casa_keywords = ['casa', 'cozinha', 'quarto', 'sala', 'decoração', 'móvel', 'organizador', 
                     'pote', 'utensílio', 'panela', 'frigideira', 'aspirador', 'robô', 'limpeza',
                     'hermético', 'mantimentos', 'dispensa', 'armário', 'plástico']
    
    # Moda & Estilo  
    moda_keywords = ['vestido', 'blusa', 'calça', 'sapato', 'tênis', 'bolsa', 'acessório', 
                     'roupa', 'moda', 'multiformas', 'madrinhas', 'casamento', 'festas']
    
    # Eletrônicos
    eletronicos_keywords = ['celular', 'smartphone', 'tablet', 'notebook', 'fone', 'carregador', 
                           'cabo', 'eletrônico', 'tv', 'monitor', 'mouse', 'teclado', 'camera', 
                           'smartwatch', 'airfryer', 'fritadeira', 'philips']
    
    if any(keyword in title_lower for keyword in casa_keywords):
        tags.append("CD")
        
    if any(keyword in title_lower for keyword in moda_keywords):
        tags.append("ME")
        
    if any(keyword in title_lower for keyword in eletronicos_keywords):
        tags.append("E")
    
    return tags


@product_bp.route("/api/products")
def api_products():
    try:
        tag = request.args.get('tag', 'all')
        
        if tag == 'all':
            products = get_all_products()
        else:
            products = get_products_by_tag(tag)
            
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        return jsonify({"error": f"Erro ao obter produtos: {str(e)}"}), 500

@product_bp.route("/minio_proxy/<bucket>/<path:filename>")
def minio_proxy(bucket, filename):
    url = f"http://localhost:9000/{bucket}/{filename}"
    try:
        response = requests.get(url, stream=True, timeout=5)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "image/jpeg")
        return Response(response.content, content_type=content_type)
    except Exception as e:
        print(f"❌ Erro ao buscar imagem do MinIO: {e}")
        return Response("Imagem não encontrada", status=404)

@product_bp.route("/admin")
def admin_panel():
    return render_template("admin.html")


from models.product import db

@product_bp.route("/api/list_ids", methods=["GET"])
def list_product_ids():
    try:
        products = get_all_products()
        data = [{"id": p.id, "title": p.title, "price": p.price} for p in products]
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@product_bp.route("/api/delete/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "Produto não encontrado"}), 404

        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": f"Produto {product_id} removido com sucesso."}), 200

    except Exception as e:
        return jsonify({"error": f"Erro ao deletar: {str(e)}"}), 500


@product_bp.route("/sitemap.xml")
def sitemap():
    """Gera sitemap.xml dinamicamente"""
    pages = [
        {'path': '/', 'priority': 1.0, 'changefreq': 'daily'},
        {'path': '/secao1', 'priority': 0.8, 'changefreq': 'daily'},
        {'path': '/secao2', 'priority': 0.8, 'changefreq': 'daily'},
        {'path': '/secao3', 'priority': 0.8, 'changefreq': 'daily'},
        {'path': '/secao4', 'priority': 0.8, 'changefreq': 'daily'},
    ]
    
    sitemap_xml = seo_service.generate_sitemap_xml(pages)
    return Response(sitemap_xml, mimetype='application/xml')


@product_bp.route("/robots.txt")
def robots():
    """Gera robots.txt"""
    robots_txt = seo_service.generate_robots_txt(
        disallow_paths=['/admin', '/api'],
        sitemap_url=f"{seo_service.site_url}/sitemap.xml"
    )
    return Response(robots_txt, mimetype='text/plain')


@product_bp.route("/produto/<product_id>")
def product_detail(product_id):
    """Exibe página detalhada do produto com SEO completo"""
    product = Product.query.get(product_id)
    
    if not product:
        return "Produto não encontrado", 404
    
    # Converter product para dict
    product_dict = product.to_dict()
    
    # Gerar schema.org do produto
    product_schema = seo_service.generate_product_schema(product_dict)
    
    # Gerar breadcrumb schema
    breadcrumb_schema = seo_service.generate_breadcrumb_schema([
        {'name': 'Home', 'url': '/'},
        {'name': 'Produtos', 'url': '/'},
        {'name': product.title[:30], 'url': f'/produto/{product_id}'}
    ])
    
    return render_template(
        "produto.html",
        product=product_dict,
        product_schema=product_schema,
        breadcrumb_schema=breadcrumb_schema
    )
