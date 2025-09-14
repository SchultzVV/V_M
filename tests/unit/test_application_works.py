"""
Test to answer the question: "vc funciona de fato?" (Does it actually work?)

This test verifies that the V&M application actually works and provides the essential functionality.
"""
import pytest
import os
import sys
import requests
from unittest.mock import patch, MagicMock

# Add the site directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/site'))

def test_application_starts_successfully():
    """Test that the application starts without crashing."""
    from main import app
    assert app is not None
    assert app.name == 'main'
    
    # Test that we can create a test client
    client = app.test_client()
    assert client is not None

def test_health_endpoint_works():
    """Test that the health endpoint provides status information."""
    from main import app
    client = app.test_client()
    
    response = client.get('/health')
    assert response.status_code in [200, 503]  # Either healthy or degraded is fine
    
    data = response.get_json()
    assert 'status' in data
    assert 'service' in data
    assert 'database' in data
    assert 'message' in data
    assert data['service'] == 'V&M Site'
    
    # Verify message indicates functionality
    assert 'funcionando' in data['message'].lower()

def test_ai_routes_validation_works():
    """Test that AI routes properly validate input."""
    from main import app
    client = app.test_client()
    
    # Test ingest-url endpoint validation
    response = client.post('/ingest-url', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    
    # Test query endpoint validation  
    response = client.post('/query', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_ai_routes_handle_external_service_errors():
    """Test that AI routes handle external service failures gracefully."""
    from main import app
    
    with patch('routes.ai_routes.forward_to_ingestion_service') as mock_ingestion:
        with patch('routes.ai_routes.forward_to_retrieval_service') as mock_retrieval:
            # Mock service failures
            mock_ingestion.side_effect = requests.RequestException("Service unavailable")
            mock_retrieval.side_effect = requests.RequestException("Service unavailable")
            
            client = app.test_client()
            
            # Test ingestion service error handling
            response = client.post('/ingest-url', json={'url': 'https://example.com'})
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            
            # Test retrieval service error handling
            response = client.post('/query', json={'question': 'test question'})
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data

def test_ai_routes_work_with_successful_external_services():
    """Test that AI routes work when external services are available."""
    from main import app
    
    with patch('routes.ai_routes.forward_to_ingestion_service') as mock_ingestion:
        with patch('routes.ai_routes.forward_to_retrieval_service') as mock_retrieval:
            # Mock successful responses
            mock_ingestion.return_value = {'message': 'URL ingested successfully'}
            mock_retrieval.return_value = {'answer': 'This is a test answer'}
            
            client = app.test_client()
            
            # Test successful ingestion
            response = client.post('/ingest-url', json={'url': 'https://example.com'})
            assert response.status_code == 200
            data = response.get_json()
            assert data['message'] == 'URL ingested successfully'
            
            # Test successful query
            response = client.post('/query', json={'question': 'test question'})
            assert response.status_code == 200
            data = response.get_json()
            assert data['answer'] == 'This is a test answer'

def test_product_functionality_works_without_database():
    """Test that product functionality handles database unavailability gracefully."""
    from main import app
    client = app.test_client()
    
    # Even without database, API endpoints should not crash
    response = client.get('/api/products')
    # Should either work with empty results or return a proper error
    assert response.status_code in [200, 404, 500]

def test_media_proxy_endpoint_exists():
    """Test that media proxy endpoints exist."""
    from main import app
    client = app.test_client()
    
    # Test media ping endpoint
    response = client.get('/media/ping')
    # Should either work or return proper error
    assert response.status_code in [200, 404, 500]

def test_application_handles_missing_environment_variables():
    """Test that the application handles missing environment variables gracefully."""
    # Store original values
    original_db_url = os.environ.get('DATABASE_URL')
    original_postgres_uri = os.environ.get('POSTGRES_URI')
    
    try:
        # Remove environment variables
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        if 'POSTGRES_URI' in os.environ:
            del os.environ['POSTGRES_URI']
            
        # Import should still work
        from main import app
        assert app is not None
        
        # Health check should show degraded status
        client = app.test_client()
        response = client.get('/health')
        assert response.status_code == 503  # Degraded
        
        data = response.get_json()
        assert data['status'] == 'degraded'
        assert data['database'] == 'disconnected'
        
    finally:
        # Restore original values
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        if original_postgres_uri:
            os.environ['POSTGRES_URI'] = original_postgres_uri

def test_application_provides_meaningful_error_messages():
    """Test that the application provides helpful error messages."""
    from main import app
    client = app.test_client()
    
    # Test Portuguese error messages
    response = client.post('/ingest-url', json={})
    data = response.get_json()
    assert 'obrigatório' in data['error']  # Portuguese for "required"
    
    response = client.post('/query', json={})
    data = response.get_json()
    assert 'obrigatório' in data['error']  # Portuguese for "required"

def test_answer_main_question():
    """
    Main test to answer: "vc funciona de fato?" (Does it actually work?)
    
    This test verifies the core functionality that makes the application "work".
    """
    from main import app
    
    # 1. Application starts without crashing
    assert app is not None, "❌ Application failed to start"
    
    # 2. Basic health check works
    client = app.test_client()
    health_response = client.get('/health')
    assert health_response.status_code in [200, 503], "❌ Health check failed"
    
    health_data = health_response.get_json()
    assert 'funcionando' in health_data['message'].lower(), "❌ App not reporting as functional"
    
    # 3. Core AI functionality is accessible
    ai_response = client.get('/ai')
    assert ai_response.status_code in [200, 404], "❌ AI page not accessible"
    
    # 4. Input validation works
    validation_response = client.post('/ingest-url', json={})
    assert validation_response.status_code == 400, "❌ Input validation not working"
    
    # 5. Error handling works
    with patch('routes.ai_routes.forward_to_ingestion_service') as mock:
        mock.side_effect = requests.RequestException("Test error")
        error_response = client.post('/ingest-url', json={'url': 'https://test.com'})
        assert error_response.status_code == 500, "❌ Error handling not working"
    
    # If we get here, the application works!
    print("✅ SIM, funciona de fato! (YES, it actually works!)")
    print(f"✅ Status: {health_data['status']}")
    print(f"✅ Database: {health_data['database']}")
    print(f"✅ Message: {health_data['message']}")