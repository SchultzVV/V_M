# Variáveis configuráveis
include .env  # base dev por padrão
export

ifeq ($(MAKECMDGOALS),prd-up)
include .env.prd
endif
ifeq ($(MAKECMDGOALS),prd-down)
include .env.prd
endif
ifeq ($(MAKECMDGOALS),prd-up-ghcr)
include .env.prd
endif


TAG ?= latest
GHCR_USER = $(GITHUB_USERNAME)
GHCR_TOKEN = $(GITHUB_TOKEN)
IMAGE_NAME = ghcr.io/$(GHCR_USER)/site:$(TAG)

COMPOSE = docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml --env-file .env

up:
	$(COMPOSE) up --build

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

docker-login:
	echo $(GHCR_TOKEN) | docker login ghcr.io -u $(GHCR_USER) --password-stdin

build-prd-site:
	docker build -t $(IMAGE_NAME) ./services/site

push-ghcr-site: docker-login build-prd-site
	docker push $(IMAGE_NAME)

pull-prd-ghcr:
	docker pull $(IMAGE_NAME)

prd-up-ghcr:
	@echo "🛑 Parando containers antigos..."
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd down || true
	@echo "📥 Dando pull da imagem do GitHub Container Registry..."
	docker pull $(IMAGE_NAME)
	@echo "🚀 Subindo site com imagem em produção (GHCR)..."
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd up -d
	@echo "🛑 Encerrando ngrok anterior..."
	-pkill ngrok || true
	@echo "🌐 Iniciando túnel com ngrok..."
	@nohup ngrok http 5000 > /dev/null 2>&1 &
	@sleep 3
	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url' | xargs echo "🌍 URL pública gerada:"

local-tests: test-unit test-integration

test-unit:
	PYTHONPATH=. pytest tests/unit --disable-warnings -v

test-integration:
	PYTHONPATH=. pytest tests/integration --disable-warnings -v

run-site-db:
	DATABASE_URL=postgresql://user:password@localhost:5432/produtos_db \
	FLASK_ENV=development \
	python services/site/main.py

psql:
	docker exec -it postgres psql -U user -d produtos_db

stage:
	python3 scripts/stage_products.py
