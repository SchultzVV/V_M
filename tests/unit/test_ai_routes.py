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


def test_ingest_url(client, monkeypatch):
    def mock_post(url, json, timeout):
        assert url.endswith('/ingest_from_url')
        assert json['url'] == 'https://exemplo.com'
        return MockResponse({'message': 'ok'})
    monkeypatch.setattr('services.site.routes.ai_routes.requests.post', mock_post)
    resp = client.post('/ingest-url', json={'url': 'https://exemplo.com'})
    assert resp.status_code == 200
    assert resp.get_json() == {'message': 'ok'}


def test_query(client, monkeypatch):
    def mock_post(url, json, timeout):
        assert url.endswith('/query')
        assert json['question'] == 'qual a data de matrícula?'
        return MockResponse({'answer': '42'})
    monkeypatch.setattr('services.site.routes.ai_routes.requests.post', mock_post)
    resp = client.post('/query', json={'question': 'qual a data de matrícula?'})
    assert resp.status_code == 200
    assert resp.get_json() == {'answer': '42'}
