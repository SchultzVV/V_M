# Variáveis configuráveis
include .env
export

ID ?= 1
REGISTRY = registry.gitea.seuservidor.com
USER = seu-usuario
IMAGE_NAME = $(REGISTRY)/$(USER)/site
TAG = latest

COMPOSE = docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml --env-file .env

up:
	$(COMPOSE) up --build -d
down:
	$(COMPOSE) down -v
prd-up:
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd up -d
prd-down:
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd down -v

serve-ngrok:
	@echo "🛑 Encerrando ngrok anterior, se existir..."
	@pkill ngrok || true
	@echo "🔧 Subindo containers Docker..."
	@docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml --env-file .env up -d
	@echo "🚀 Iniciando túnel com ngrok..."
	@ngrok http 5000 > /dev/null &
	@sleep 3
	@echo "🌐 URL pública gerada:"
	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'



restart-site:
	$(COMPOSE) restart site

redo-site:
	$(COMPOSE) stop site
	$(COMPOSE) rm -f site
	$(COMPOSE) build site
	$(COMPOSE) up -d site

logs-site:
	$(COMPOSE) logs -f site

prdlogs-site:
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd logs -f site

build-prd-site:
	docker build -t $(IMAGE_NAME):$(TAG) ./services/site

push-gitea-site: build-prd-site
	docker push $(IMAGE_NAME):$(TAG)

local-tests: test-unit test-integration
test-unit:
	PYTHONPATH=. pytest tests/unit --disable-warnings -v
test-integration:
	PYTHONPATH=. pytest tests/integration --disable-warnings -v
