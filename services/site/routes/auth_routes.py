"""
Rotas de autenticação OAuth para Mercado Livre
"""

import os
import sys
from flask import Blueprint, request, redirect, jsonify, render_template_string
from services.ml_auth import ml_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/mercadolivre/login")
def mercadolivre_login():
    """
    Inicia o fluxo de autenticação OAuth do Mercado Livre
    Redireciona DIRETAMENTE para a página de autorização (sem página intermediária)
    """
    auth_url = ml_auth.get_authorization_url()
    
    # Redirecionar diretamente para evitar problemas com CloudFront/bloqueios
    return redirect(auth_url)


@auth_bp.route("/mercadolivre/callback")
def mercadolivre_callback():
    """
    Callback do OAuth - Mercado Livre redireciona aqui após autorização
    Recebe o código de autorização e troca por access_token
    """
    code = request.args.get("code")
    error = request.args.get("error")
    
    if error:
        return jsonify({
            "status": "error",
            "message": f"Erro na autorização: {error}",
            "description": request.args.get("error_description", "")
        }), 400
    
    if not code:
        return jsonify({
            "status": "error",
            "message": "Código de autorização não recebido"
        }), 400
    
    try:
        print(f"🔍 Callback recebido - código: {code[:30]}...", flush=True)
        sys.stdout.flush()
        
        # Troca o código por tokens
        tokens = ml_auth.exchange_code_for_token(code)
        
        print(f"✅ Tokens recebidos com sucesso!", flush=True)
        sys.stdout.flush()
        
        # Template de sucesso
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Autenticação Concluída</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 600px;
                }
                .success {
                    color: #4CAF50;
                    font-size: 60px;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #333;
                }
                .token-info {
                    background: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    text-align: left;
                }
                .token-info code {
                    display: block;
                    background: #333;
                    color: #0f0;
                    padding: 10px;
                    border-radius: 3px;
                    overflow-x: auto;
                    font-size: 12px;
                    margin: 5px 0;
                }
                .btn {
                    display: inline-block;
                    padding: 12px 24px;
                    background: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>Autenticação Concluída!</h1>
                <p>Sua conta do Mercado Livre foi conectada com sucesso.</p>
                
                <div class="token-info">
                    <strong>Informações do Token:</strong>
                    <p>User ID: <code>{{ user_id }}</code></p>
                    <p>Expira em: <strong>{{ expires_in }} segundos</strong> (≈ 6 horas)</p>
                    <p>Access Token: <code>{{ access_token[:50] }}...</code></p>
                </div>
                
                <p>✅ Os tokens foram salvos automaticamente.</p>
                <p>✅ O webhook agora pode acessar a API do Mercado Livre.</p>
                
                <a href="/" class="btn">🏠 Voltar para o site</a>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(
            template,
            user_id=tokens.get("user_id", "N/A"),
            expires_in=tokens.get("expires_in", 0),
            access_token=tokens.get("access_token", "")
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ERRO no callback:", flush=True)
        print(error_trace, flush=True)
        sys.stdout.flush()
        
        return jsonify({
            "status": "error",
            "message": f"Erro ao processar callback: {str(e)}",
            "type": type(e).__name__,
            "trace": error_trace if os.getenv("DEBUG") == "True" else None
        }), 500


@auth_bp.route("/mercadolivre/status")
def mercadolivre_status():
    """
    Verifica o status da autenticação com o Mercado Livre
    """
    is_authenticated = ml_auth.is_authenticated()
    access_token = ml_auth.get_valid_access_token()
    
    if is_authenticated:
        return jsonify({
            "status": "authenticated",
            "message": "Autenticado com sucesso",
            "has_token": bool(access_token),
            "token_preview": access_token[:20] + "..." if access_token else None
        })
    else:
        return jsonify({
            "status": "not_authenticated",
            "message": "Não autenticado",
            "login_url": "/auth/mercadolivre/login"
        })


@auth_bp.route("/mercadolivre/logout", methods=["POST"])
def mercadolivre_logout():
    """
    Remove os tokens salvos
    """
    ml_auth.logout()
    
    return jsonify({
        "status": "success",
        "message": "Logout realizado com sucesso"
    })


@auth_bp.route("/mercadolivre/refresh", methods=["POST"])
def mercadolivre_refresh():
    """
    Força a renovação do access_token
    """
    try:
        tokens = ml_auth.refresh_access_token()
        
        return jsonify({
            "status": "success",
            "message": "Token renovado com sucesso",
            "expires_in": tokens.get("expires_in")
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao renovar token: {str(e)}"
        }), 500
