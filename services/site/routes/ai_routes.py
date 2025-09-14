from flask import Blueprint, request, jsonify, render_template
import requests
import os
import logging

ai_bp = Blueprint('ai_bp', __name__)

# Endpoints dos microserviços
INGESTION_URL = 'http://ingestion_service:5003/ingest_from_url'
RETRIEVAL_URL = 'http://retrieval_service:5004/query'

# Configuração de timeout reduzido para detectar serviços indisponíveis mais rapidamente
SERVICE_TIMEOUT = 5

logger = logging.getLogger(__name__)


def check_service_health(service_url: str) -> bool:
    """Verifica se um microserviço está disponível."""
    try:
        # Tenta fazer uma requisição simples para verificar se o serviço responde
        response = requests.get(service_url.replace('/ingest_from_url', '/health').replace('/query', '/health'), 
                               timeout=2)
        return response.status_code == 200
    except:
        return False


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


@ai_bp.route('/ai/status')
def ai_status():
    """Retorna o status dos microserviços de IA."""
    ingestion_available = check_service_health(INGESTION_URL)
    retrieval_available = check_service_health(RETRIEVAL_URL)
    
    return jsonify({
        'ingestion_service': 'online' if ingestion_available else 'offline',
        'retrieval_service': 'online' if retrieval_available else 'offline',
        'overall_status': 'operational' if (ingestion_available and retrieval_available) else 'degraded'
    })


def forward_to_ingestion_service(url: str):
    """Encaminha URL para o microserviço de ingestão."""
    try:
        resp = requests.post(INGESTION_URL, json={'url': url}, timeout=SERVICE_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        raise ServiceUnavailableError("Serviço de ingestão não está disponível. Verifique se os microserviços estão rodando.")
    except requests.Timeout:
        raise ServiceUnavailableError("Serviço de ingestão não respondeu em tempo adequado.")
    except requests.RequestException as e:
        raise ServiceError(f"Erro no serviço de ingestão: {str(e)}")


def forward_to_retrieval_service(question: str):
    """Encaminha pergunta para o microserviço de consulta."""
    try:
        resp = requests.post(RETRIEVAL_URL, json={'question': question}, timeout=SERVICE_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        raise ServiceUnavailableError("Serviço de consulta não está disponível. Verifique se os microserviços estão rodando.")
    except requests.Timeout:
        raise ServiceUnavailableError("Serviço de consulta não respondeu em tempo adequado.")
    except requests.RequestException as e:
        raise ServiceError(f"Erro no serviço de consulta: {str(e)}")


class ServiceUnavailableError(Exception):
    """Exceção para quando um microserviço não está disponível."""
    pass


class ServiceError(Exception):
    """Exceção para erros gerais dos microserviços."""
    pass


@ai_bp.route('/ingest-url', methods=['POST'])
def ingest_url():
    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'url é obrigatório'}), 400
    
    try:
        result = forward_to_ingestion_service(url)
        return jsonify(result)
    except ServiceUnavailableError as e:
        logger.warning(f"Serviço de ingestão indisponível: {str(e)}")
        return jsonify({
            'error': str(e),
            'suggestion': 'Execute "make up" para iniciar os microserviços de IA.',
            'status': 'service_unavailable'
        }), 503
    except ServiceError as e:
        logger.error(f"Erro no serviço de ingestão: {str(e)}")
        return jsonify({'error': str(e), 'status': 'service_error'}), 500
    except Exception as e:
        logger.error(f"Erro inesperado na ingestão: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor', 'status': 'internal_error'}), 500


@ai_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json() or {}
    question = data.get('question')
    if not question:
        return jsonify({'error': 'question é obrigatório'}), 400
    
    try:
        result = forward_to_retrieval_service(question)
        return jsonify(result)
    except ServiceUnavailableError as e:
        logger.warning(f"Serviço de consulta indisponível: {str(e)}")
        return jsonify({
            'error': str(e),
            'suggestion': 'Execute "make up" para iniciar os microserviços de IA.',
            'status': 'service_unavailable'
        }), 503
    except ServiceError as e:
        logger.error(f"Erro no serviço de consulta: {str(e)}")
        return jsonify({'error': str(e), 'status': 'service_error'}), 500
    except Exception as e:
        logger.error(f"Erro inesperado na consulta: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor', 'status': 'internal_error'}), 500
