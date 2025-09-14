import pytest
from flask import Flask

from services.site.routes.ai_routes import ai_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(ai_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception('error')


def test_ingest_url_success(client, monkeypatch):
    """Test successful URL ingestion when service is available."""
    def mock_post(url, json, timeout):
        assert url.endswith('/ingest_from_url')
        assert json['url'] == 'https://exemplo.com'
        return MockResponse({'message': 'ok'})
    monkeypatch.setattr('services.site.routes.ai_routes.requests.post', mock_post)
    resp = client.post('/ingest-url', json={'url': 'https://exemplo.com'})
    assert resp.status_code == 200
    assert resp.get_json() == {'message': 'ok'}


def test_query_success(client, monkeypatch):
    """Test successful query when service is available."""
    def mock_post(url, json, timeout):
        assert url.endswith('/query')
        assert json['question'] == 'qual a data de matrícula?'
        return MockResponse({'answer': '42'})
    monkeypatch.setattr('services.site.routes.ai_routes.requests.post', mock_post)
    resp = client.post('/query', json={'question': 'qual a data de matrícula?'})
    assert resp.status_code == 200
    assert resp.get_json() == {'answer': '42'}


def test_ingest_url_service_unavailable(client, monkeypatch):
    """Test URL ingestion when service is unavailable."""
    import requests
    def mock_post(url, json, timeout):
        raise requests.ConnectionError("Connection refused")
    monkeypatch.setattr('services.site.routes.ai_routes.requests.post', mock_post)
    resp = client.post('/ingest-url', json={'url': 'https://exemplo.com'})
    assert resp.status_code == 503
    data = resp.get_json()
    assert 'error' in data
    assert 'suggestion' in data
    assert data['status'] == 'service_unavailable'


def test_query_service_unavailable(client, monkeypatch):
    """Test query when service is unavailable."""
    import requests
    def mock_post(url, json, timeout):
        raise requests.ConnectionError("Connection refused")
    monkeypatch.setattr('services.site.routes.ai_routes.requests.post', mock_post)
    resp = client.post('/query', json={'question': 'test question'})
    assert resp.status_code == 503
    data = resp.get_json()
    assert 'error' in data
    assert 'suggestion' in data
    assert data['status'] == 'service_unavailable'


def test_ingest_url_missing_url(client):
    """Test URL ingestion with missing URL parameter."""
    resp = client.post('/ingest-url', json={})
    assert resp.status_code == 400
    assert resp.get_json() == {'error': 'url é obrigatório'}


def test_query_missing_question(client):
    """Test query with missing question parameter."""
    resp = client.post('/query', json={})
    assert resp.status_code == 400
    assert resp.get_json() == {'error': 'question é obrigatório'}


def test_ai_status_endpoint(client, monkeypatch):
    """Test the AI status endpoint."""
    # Mock the health check to simulate services offline
    def mock_get(url, timeout):
        raise requests.ConnectionError("Connection refused")
    monkeypatch.setattr('services.site.routes.ai_routes.requests.get', mock_get)
    
    resp = client.get('/ai/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'ingestion_service' in data
    assert 'retrieval_service' in data
    assert 'overall_status' in data
    assert data['overall_status'] == 'degraded'
