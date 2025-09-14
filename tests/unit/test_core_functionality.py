import pytest
import os
import tempfile
import sys
from flask import Flask
from unittest.mock import patch, MagicMock

# Add the site directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/site'))

@pytest.fixture
def test_app():
    """Create a test Flask app with minimal configuration."""
    from routes.product_routes import product_bp
    from routes.ai_routes import ai_bp
    from routes.index import index_bp
    from routes.media_routes import media_bp
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Register blueprints
    app.register_blueprint(product_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(index_bp)
    app.register_blueprint(media_bp)
    
    return app

@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()

def test_index_route_exists(client):
    """Test that the index route exists and returns valid HTML."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'V&M - Lojinha' in response.data
    assert b'html' in response.data

def test_ai_page_route_exists(client):
    """Test that the AI page route exists."""
    with patch('routes.ai_routes.render_template') as mock_render:
        mock_render.return_value = "<html>AI Page</html>"
        response = client.get('/ai')
        assert response.status_code == 200
        mock_render.assert_called_once_with('ai.html')

def test_ingest_url_validation(client):
    """Test URL ingestion endpoint validation."""
    # Test missing URL
    response = client.post('/ingest-url', json={})
    assert response.status_code == 400
    assert 'url é obrigatório'.encode('utf-8') in response.data
    
    # Test empty URL
    response = client.post('/ingest-url', json={'url': ''})
    assert response.status_code == 400

def test_query_validation(client):
    """Test query endpoint validation."""
    # Test missing question
    response = client.post('/query', json={})
    assert response.status_code == 400
    assert 'question é obrigatório'.encode('utf-8') in response.data
    
    # Test empty question
    response = client.post('/query', json={'question': ''})
    assert response.status_code == 400

def test_product_home_route(client):
    """Test that the product home route works."""
    with patch('routes.product_routes.get_all_products') as mock_get:
        mock_get.return_value = []
        response = client.get('/')
        assert response.status_code == 200

def test_application_health_check():
    """Test that core application components can be imported without errors."""
    try:
        # Import from correct path with modified sys.path
        from main import app
        from models.product import Product
        from database import engine
        assert app is not None
        assert Product is not None
        assert engine is not None
    except ImportError as e:
        pytest.fail(f"Failed to import core components: {e}")

def test_environment_variables_loading():
    """Test that environment variables are properly loaded."""
    # This tests that the app can handle missing environment variables gracefully
    required_vars = ['DATABASE_URL', 'POSTGRES_URI']
    
    # The app should handle missing environment variables
    for var in required_vars:
        if var in os.environ:
            # Store original value
            original = os.environ.get(var)
            # Test without the variable
            del os.environ[var]
            try:
                from main import app
                assert app is not None
            finally:
                # Restore original value
                if original:
                    os.environ[var] = original

def test_ai_routes_error_handling(client):
    """Test AI routes handle external service errors gracefully."""
    with patch('routes.ai_routes.requests.post') as mock_post:
        # Simulate service unavailable
        mock_post.side_effect = Exception("Service unavailable")
        
        response = client.post('/ingest-url', json={'url': 'https://example.com'})
        assert response.status_code == 500
        assert b'error' in response.data
        
        response = client.post('/query', json={'question': 'test question'})
        assert response.status_code == 500
        assert b'error' in response.data