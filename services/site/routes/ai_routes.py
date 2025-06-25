from flask import Blueprint, request, jsonify, render_template
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

# Endpoints dos microserviços
INGESTION_URL = os.getenv('INGESTION_SERVICE_URL', 'http://localhost:5003/ingest_from_url')
RETRIEVAL_URL = os.getenv('RETRIEVAL_SERVICE_URL', 'http://localhost:5004/query')

# Futuras melhorias:
# - Substituir requests por gRPC para comunicação mais performática
# - Usar websocket para chat em tempo real
# - Ingestão assíncrona com Celery ou FastAPI BackgroundTasks
# - Frontend React/HTMX com suporte a polling
# - Disponibilizar via ngrok para testes públicos

@ai_bp.route('/ai')
def ai_page():
    """Renderiza página de integração com IA."""
    return render_template('ai.html')


def forward_to_ingestion_service(url: str):
    """Encaminha URL para o microserviço de ingesão."""
    resp = requests.post(INGESTION_URL, json={'url': url}, timeout=5)
    resp.raise_for_status()
    return resp.json()


def forward_to_retrieval_service(question: str):
    """Encaminha pergunta para o microserviço de consulta."""
    resp = requests.post(RETRIEVAL_URL, json={'question': question}, timeout=5)
    resp.raise_for_status()
    return resp.json()


@ai_bp.route('/ingest-url', methods=['POST'])
def ingest_url():
    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'url é obrigatório'}), 400
    try:
        result = forward_to_ingestion_service(url)
        return jsonify(result)
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json() or {}
    question = data.get('question')
    if not question:
        return jsonify({'error': 'question é obrigatório'}), 400
    try:
        result = forward_to_retrieval_service(question)
        return jsonify(result)
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500
