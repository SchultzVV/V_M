from flask import Blueprint, render_template_string

index_bp = Blueprint("index", __name__)

@index_bp.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>DEF - Lojinha</title>
      <style>
        body { margin: 0; font-family: sans-serif; text-align: center; background: #000; color: white; }
        iframe { display: none; }
      </style>
    </head>
    <body>
      <iframe src="/media/ping" id="ngrok-prewarm"></iframe>
      <h1>DEF - Lojinha</h1>
      <p>Produtos promocionais garimpados com bom gosto 😍</p>
      <p><a class="button" href="/ai">Ir para integração IA</a></p>
      <div class="grid" id="products-container"></div>
      <script src="/static/app.js"></script>
    </body>
    </html>
    """)
