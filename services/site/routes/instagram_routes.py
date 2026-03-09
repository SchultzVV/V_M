"""
Rotas Flask para Instagram - Sistema de Postagem Automática
Endpoints para triggerar e monitorar postagens no Instagram
"""
from flask import Blueprint, request, jsonify
from agents.instagram_orchestrator import get_orchestrator
import os
from datetime import datetime


instagram_bp = Blueprint('instagram', __name__, url_prefix='/instagram')

# Lazy loading do orquestrador
_orchestrator = None

def get_instagram_orchestrator():
    """Retorna instância do orquestrador (singleton)"""
    global _orchestrator
    if _orchestrator is None:
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        _orchestrator = get_orchestrator(redis_url)
    return _orchestrator


@instagram_bp.route('/post', methods=['POST'])
def create_instagram_post():
    """
    Endpoint principal para criar post no Instagram
    
    Body (JSON):
    {
        "filters": {
            "tag": "geral",
            "min_price": 50,
            "max_price": 500
        },
        "simulate": false,
        "custom_caption": "Texto opcional",
        "post_type": "photo"  // ou "carousel"
    }
    
    Returns:
        JSON com resultado da postagem
    """
    try:
        data = request.get_json() or {}
        
        orchestrator = get_instagram_orchestrator()
        
        result = orchestrator.run(
            filters=data.get('filters', {}),
            simulate=data.get('simulate', False),
            custom_caption=data.get('custom_caption'),
            post_type=data.get('post_type', 'photo')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Post criado com sucesso',
                'post_url': result['post_result'].get('post_url'),
                'product': {
                    'id': result['selected_product'].get('external_id'),
                    'title': result['selected_product'].get('title'),
                    'price': result['selected_product'].get('price')
                },
                'caption': result['post_result'].get('caption')
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao criar post',
                'errors': result.get('errors', [])
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/post/auto', methods=['POST'])
def auto_post():
    """
    Endpoint simplificado para postagem automática
    Seleciona automaticamente o melhor produto e posta
    
    Query params:
        ?simulate=true  - Modo de teste (não posta de verdade)
    
    Returns:
        JSON com resultado
    """
    try:
        simulate = request.args.get('simulate', 'false').lower() == 'true'
        
        orchestrator = get_instagram_orchestrator()
        
        result = orchestrator.run(
            simulate=simulate,
            post_type='photo'
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '✅ Post automático criado',
                'post_url': result['post_result'].get('post_url'),
                'product_title': result['selected_product'].get('title')
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '❌ Erro no post automático',
                'errors': result.get('errors', [])
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/schedule', methods=['POST'])
def schedule_post():
    """
    Agenda um post para horário futuro
    
    Body (JSON):
    {
        "scheduled_time": 1234567890,  // timestamp unix
        "filters": {
            "tag": "geral"
        }
    }
    
    Returns:
        JSON com confirmação do agendamento
    """
    try:
        data = request.get_json()
        
        if not data or 'scheduled_time' not in data:
            return jsonify({
                'success': False,
                'message': 'scheduled_time é obrigatório'
            }), 400
        
        orchestrator = get_instagram_orchestrator()
        
        result = orchestrator.run_async_schedule(
            scheduled_time=data['scheduled_time'],
            filters=data.get('filters', {})
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/workflow', methods=['GET'])
def get_workflow_info():
    """
    Retorna informações sobre o workflow dos agentes
    
    Returns:
        JSON com diagrama e informações do workflow
    """
    try:
        orchestrator = get_instagram_orchestrator()
        
        return jsonify({
            'success': True,
            'workflow_diagram': orchestrator.get_workflow_diagram(),
            'agents': [
                {
                    'name': 'ProductDecisionAgent',
                    'description': 'Seleciona o melhor produto do staging para postar',
                    'order': 1
                },
                {
                    'name': 'ProductEnricherAgent',
                    'description': 'Enriquece dados e gera legenda otimizada',
                    'order': 2
                },
                {
                    'name': 'InstagramPosterAgent',
                    'description': 'Gera imagem e posta no Instagram',
                    'order': 3
                }
            ]
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/history', methods=['GET'])
def get_post_history():
    """
    Retorna histórico de posts no Instagram
    
    Query params:
        ?limit=10  - Número de posts a retornar (padrão: 10)
    
    Returns:
        JSON com lista de posts
    """
    try:
        limit = int(request.args.get('limit', 10))
        
        orchestrator = get_instagram_orchestrator()
        redis_client = orchestrator.redis_client
        
        history_key = "instagram:post_history"
        posts = redis_client.lrange(history_key, 0, limit - 1)
        
        import ast
        post_list = []
        for post_bytes in posts:
            try:
                post_dict = ast.literal_eval(post_bytes.decode('utf-8'))
                post_list.append(post_dict)
            except:
                continue
        
        return jsonify({
            'success': True,
            'count': len(post_list),
            'posts': post_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/test/image', methods=['POST'])
def test_image_generation():
    """
    Testa a geração de imagem sem postar
    
    Body (JSON):
    {
        "product_id": "MLB19571567"  // ID do produto no staging
    }
    
    Returns:
        JSON com caminho da imagem gerada
    """
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({
                'success': False,
                'message': 'product_id é obrigatório'
            }), 400
        
        orchestrator = get_instagram_orchestrator()
        
        # Força seleção do produto específico
        result = orchestrator.run(
            filters={'force_product_id': product_id},
            simulate=True,  # Não posta de verdade
            post_type='photo'
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Imagem gerada (não postada)',
                'image_paths': result['post_result'].get('image_paths', []),
                'caption': result['post_result'].get('caption')
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao gerar imagem',
                'errors': result.get('errors', [])
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/analytics/<media_id>', methods=['GET'])
def get_post_analytics(media_id):
    """
    Retorna analytics de um post específico
    
    Args:
        media_id: ID do post no Instagram
    
    Returns:
        JSON com métricas do post
    """
    try:
        orchestrator = get_instagram_orchestrator()
        result = orchestrator.poster_agent.get_post_analytics(media_id)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@instagram_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    Verifica status do sistema de postagem
    
    Returns:
        JSON com status dos componentes
    """
    try:
        orchestrator = get_instagram_orchestrator()
        
        # Testa Redis
        redis_ok = False
        try:
            orchestrator.redis_client.ping()
            redis_ok = True
        except:
            pass
        
        # Verifica credenciais Instagram
        instagram_configured = bool(
            os.getenv('INSTAGRAM_USERNAME') and 
            os.getenv('INSTAGRAM_PASSWORD')
        )
        
        # Conta produtos no staging
        import glob
        staging_files = glob.glob('staging/*.json')
        staging_count = len([f for f in staging_files if not f.endswith('.processed')])
        
        return jsonify({
            'success': True,
            'status': 'operational',
            'components': {
                'redis': 'ok' if redis_ok else 'error',
                'instagram': 'configured' if instagram_configured else 'not_configured',
                'openai': 'configured' if os.getenv('OPENAI_API_KEY') else 'not_configured',
                'agents': 'loaded'
            },
            'staging': {
                'products_available': staging_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'message': str(e)
        }), 500


@instagram_bp.route('/test/agents', methods=['GET'])
def test_agents():
    """
    Testa cada agente individualmente
    
    Returns:
        JSON com resultado dos testes
    """
    try:
        orchestrator = get_instagram_orchestrator()
        
        results = {
            'decision_agent': 'not_tested',
            'enricher_agent': 'not_tested',
            'poster_agent': 'not_tested'
        }
        
        # Testa agente decisor
        try:
            decision_result = orchestrator.decision_agent.execute({})
            results['decision_agent'] = 'ok' if decision_result.get('success') else 'error'
        except Exception as e:
            results['decision_agent'] = f'error: {str(e)}'
        
        # Se decisor funcionou, testa enriquecedor
        if results['decision_agent'] == 'ok':
            try:
                enricher_result = orchestrator.enricher_agent.execute({
                    'selected_product': decision_result['selected_product']
                })
                results['enricher_agent'] = 'ok' if enricher_result.get('success') else 'error'
            except Exception as e:
                results['enricher_agent'] = f'error: {str(e)}'
        
        # Poster não é testado para evitar postagem acidental
        results['poster_agent'] = 'skipped (use /instagram/post com simulate=true)'
        
        return jsonify({
            'success': True,
            'tests': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
