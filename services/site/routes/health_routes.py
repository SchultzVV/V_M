from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import os

health_bp = Blueprint('health_bp', __name__)

@health_bp.route('/health')
def health_check():
    """Health check endpoint to verify if the application is working."""
    status = {
        'status': 'healthy',
        'service': 'V&M Site',
        'checks': {}
    }
    
    # Check database connection
    try:
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status['checks']['database'] = 'connected'
    except OperationalError as e:
        status['checks']['database'] = f'failed: {str(e)}'
        status['status'] = 'degraded'
    except Exception as e:
        status['checks']['database'] = f'error: {str(e)}'
        status['status'] = 'degraded'
    
    # Check environment variables
    required_env_vars = ['DATABASE_URL', 'POSTGRES_URI']
    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        status['checks']['environment'] = f'missing vars: {missing_vars}'
        status['status'] = 'degraded'
    else:
        status['checks']['environment'] = 'ok'
    
    # Check AI services endpoints (without actually calling them)
    status['checks']['ai_ingestion_url'] = os.environ.get('INGESTION_URL', 'http://ingestion_service:5003/ingest_from_url')
    status['checks']['ai_retrieval_url'] = os.environ.get('RETRIEVAL_URL', 'http://retrieval_service:5004/query')
    
    # Return appropriate HTTP status code
    http_status = 200 if status['status'] == 'healthy' else 503
    
    return jsonify(status), http_status

@health_bp.route('/ping')
def ping():
    """Simple ping endpoint to check if the service is responding."""
    return jsonify({'message': 'pong', 'service': 'V&M Site'}), 200