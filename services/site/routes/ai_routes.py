import os
import re
import json
import logging
from flask import Blueprint, request, jsonify, render_template
from models.product import Product
from openai import OpenAI

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai_bp', __name__, url_prefix='/ai')

_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# ─── Mapa de palavras-chave → tag do DB ─────────────────────────────────────
_TAG_KEYWORDS: list[tuple[str, list[str]]] = [
    ("E",   ["smartphone", "celular", "notebook", "computador", "tablet", "fone",
              "tv", "televisão", "game", "câmera", "smartwatch", "eletrônico", "tech"]),
    ("CD",  ["cadeira", "mesa", "sofá", "cama", "luminária", "tapete", "vaso",
              "decoração", "casa", "cozinha", "banheiro", "sala", "quarto"]),
    ("ME",  ["vestido", "camiseta", "calça", "tênis", "sapato", "bolsa", "relógio",
              "moda", "roupa", "óculos", "jaqueta", "moletom"]),
    ("PET", ["cachorro", "gato", "pet", "ração", "areia", "coleira", "brinquedo pet",
              "animais", "veterinário"]),
]

def _detect_tag(question: str) -> str | None:
    q = question.lower()
    for tag, keywords in _TAG_KEYWORDS:
        if any(kw in q for kw in keywords):
            return tag
    return None

def _search_products(question: str, limit: int = 6) -> list[dict]:
    """Busca produtos no DB por search e/ou tag inferida da pergunta."""
    tag = _detect_tag(question)
    q = Product.query
    q = q.filter(Product.price.isnot(None), Product.price.op('~')('[1-9]'))

    if tag:
        q = q.filter(Product.tags.ilike(f'%"{tag}"%'))
    else:
        # sem tag detectada, faz full-text search pelo título
        words = [w for w in re.split(r'\W+', question) if len(w) > 3]
        for word in words[:3]:
            q = q.filter(Product.title.ilike(f'%{word}%'))

    products = q.order_by(Product.created_at.desc()).limit(limit).all()
    return [p.to_dict() for p in products]


def _build_prompt(question: str, products: list[dict]) -> str:
    if not products:
        catalog = "Nenhum produto disponível no momento."
    else:
        lines = []
        for i, p in enumerate(products, 1):
            price = p.get("price", "")
            old   = p.get("oldPrice", "")
            disc  = ""
            if old and old != price:
                disc = f" (era {old})"
            lines.append(f"{i}. {p['title'][:80]} — {price}{disc}")
        catalog = "\n".join(lines)

    return f"""Você é o assistente da loja DEF — um catálogo de produtos com foco em promoções.

Catálogo atual ({len(products)} produtos encontrados):
{catalog}

Responda de forma direta, simpática e em português do Brasil.
Se tiver produtos relevantes, mencione os 1-3 mais destacados pelo nome e preço.
Se não tiver o produto pedido, diga claramente e sugira categorias similares.
Não invente produtos que não estão na lista acima.

Pergunta do usuário: {question}"""


@ai_bp.route('/')
def ai_page():
    return render_template('ai.html')


@ai_bp.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'error': 'question é obrigatório'}), 400

    products = _search_products(question)
    prompt   = _build_prompt(question, products)

    try:
        completion = _openai.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,
        )
        answer = completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        if products:
            names = ", ".join(p['title'][:40] for p in products[:3])
            answer = f"Sim! Encontrei {len(products)} produto(s): {names}."
        else:
            answer = "Não encontrei produtos para essa busca no momento."

    return jsonify({
        'answer':   answer,
        'products': products[:3],
    })
