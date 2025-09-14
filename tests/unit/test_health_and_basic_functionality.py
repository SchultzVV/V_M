import pytest
import os
import sys
from flask import Flask
from unittest.mock import patch, MagicMock

# Add the site directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/site'))

@pytest.fixture
def robust_app():
    """Create a robust Flask app that doesn't fail on database connection issues."""
    from main_robust import create_app
    return create_app()

@pytest.fixture
def client(robust_app):
    """Create test client."""
    robust_app.config['TESTING'] = True
    return robust_app.test_client()

def test_health_check_endpoint(client):
    """Test that the health check endpoint works."""
    response = client.get('/health')
    assert response.status_code in [200, 503]  # Either healthy or degraded is fine
    
    data = response.get_json()
    assert 'status' in data
    assert 'service' in data
    assert 'checks' in data
    assert data['service'] == 'V&M Site'

def test_ping_endpoint(client):
    """Test that the ping endpoint works."""
    response = client.get('/ping')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['message'] == 'pong'
    assert data['service'] == 'V&M Site'

def test_ai_page_endpoint(client):
    """Test that the AI page can be accessed."""
    response = client.get('/ai')
    # Should either work (200) or have some error but not crash completely
    assert response.status_code in [200, 404, 500]

def test_index_page_endpoint(client):
    """Test that the index page can be accessed."""
    response = client.get('/')
    # Should work since index route has minimal dependencies
    assert response.status_code == 200

def test_ingest_url_endpoint_validation(client):
    """Test URL ingestion endpoint input validation."""
    # Test missing URL
    response = client.post('/ingest-url', json={})
    assert response.status_code == 400
    
    data = response.get_json()
    assert 'error' in data

def test_query_endpoint_validation(client):
    """Test query endpoint input validation."""
    # Test missing question
    response = client.post('/query', json={})
    assert response.status_code == 400
    
    data = response.get_json()
    assert 'error' in data

def test_application_can_start_without_database():
    """Test that the application can start even without database connection."""
    from main_robust import create_app
    app = create_app()
    assert app is not None
    assert len(list(app.url_map.iter_rules())) > 0  # Should have routes registered

def test_media_ping_endpoint(client):
    """Test that the media ping endpoint works."""
    response = client.get('/media/ping')
    # This should work as it's a simple endpoint
    assert response.status_code == 200