# =======================
# 🌱 Variáveis de ambiente
# =======================

include .env           # Carrega variáveis de desenvolvimento
export                 # Torna todas disponíveis aos comandos abaixo

# Se o comando for produção, carrega .env.prd
ifeq ($(MAKECMDGOALS),prd-up)
	include .env.prd
endif
ifeq ($(MAKECMDGOALS),prd-down)
	include .env.prd
endif
ifeq ($(MAKECMDGOALS),prd-up-ghcr)
	include .env.prd
endif

# Tags e nomes de imagem para deploy
TAG ?= latest
# Variáveis do GitHub Container Registry (GHCR)
# GHCR_USER e GHCR_TOKEN devem ser definidos no ambiente ou no arquivo .env
# Se não estiverem definidos, assume-se que o usuário e token do GitHub estão disponíveis
# GHCR_USER ?= $(GITHUB_USERNAME)
# GHCR_TOKEN ?= $(GITHUB_TOKEN)

GHCR_USER = $(GITHUB_USERNAME)
GHCR_TOKEN = $(GITHUB_TOKEN)
IMAGE_NAME = ghcr.io/$(GHCR_USER)/site:$(TAG)

# Comando base para dev
COMPOSE = docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml --env-file .env

# =====================
# 🧪 Desenvolvimento
# =====================

up:  ## Sobe o ambiente de desenvolvimento
	$(COMPOSE) up --build

down:  ## Para e remove containers + volumes
	$(COMPOSE) down -v

restart-site:  ## Reinicia apenas o serviço do site
	$(COMPOSE) restart site

redo-site:  ## Rebuild completo apenas do site
	$(COMPOSE) stop site
	$(COMPOSE) rm -f site
	$(COMPOSE) build site
	$(COMPOSE) up -d site

logs-site:  ## Logs em tempo real do site
	$(COMPOSE) logs -f site

serve-ngrok:  ## Inicia túnel ngrok para acessar localmente via web
	@echo "🛑 Encerrando ngrok anterior, se existir..."
	@pkill ngrok || true
	@echo "🔧 Subindo containers Docker..."
	@$(COMPOSE) up -d
	@echo "🚀 Iniciando túnel com ngrok..."
	@ngrok http 5000 > /dev/null &
	@sleep 3
	@echo "🌐 URL pública gerada:"
	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'

definitive-serve-ngrok:  ## Inicia túnel ngrok (modo gratuito, link aleatório)
	@echo "🛑 Encerrando ngrok anterior, se existir..."
	@pkill ngrok || true
	@echo "🔧 Subindo containers Docker..."
	@$(COMPOSE) up -d
	@echo "🚀 Iniciando túnel ngrok (porta $(PORT))..."
	@ngrok http $(PORT) > /dev/null &
	@sleep 3
	@echo "🌐 URL pública gerada:"
	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'


# =====================
# 🚀 Produção
# =====================

prd-up:  ## Sobe o ambiente de produção com docker-compose
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd up -d

prd-down:  ## Para e remove containers de produção
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd down -v

prdlogs-site:  ## Logs do serviço site em produção
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd logs -f site

prd-up-ghcr:  ## Sobe produção usando imagem do GHCR
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

# =====================
# 📦 Docker Hub / GHCR
# =====================

# 🔐 Login no GitHub Container Registry
docker-login-ghcr:
	# echo "$$GITHUB_TOKEN" | docker login ghcr.io -u $$GITHUB_USERNAME --password-stdin

docker-login:  ## Login no GitHub Container Registry (GHCR)
	echo $(GHCR_TOKEN) | docker login ghcr.io -u $(GHCR_USER) --password-stdin

build-prd-site:  ## Build da imagem de produção
	docker build -t $(IMAGE_NAME) ./services/site

push-ghcr-site: docker-login-ghcr build-prd-site  ## Push da imagem para GHCR
	docker push $(IMAGE_NAME)

pull-prd-ghcr:  ## Puxa a imagem de produção do GHCR
	docker pull $(IMAGE_NAME)

# =====================
# 🧪 Testes
# =====================

local-tests: test-unit test-integration  ## Executa todos os testes locais

test-unit:  ## Testes unitários
	PYTHONPATH=. pytest tests/unit --disable-warnings -v

test-integration:  ## Testes de integração
	PYTHONPATH=. pytest tests/integration --disable-warnings -v

# =====================
# 🛠️ Ferramentas e dados
# =====================

run-site-db:  ## Executa manualmente o site com PostgreSQL local
	DATABASE_URL=postgresql://user:password@localhost:5432/produtos_db \
	FLASK_ENV=development \
	python services/site/main.py

psql:  ## Abre terminal psql no container
	docker exec -it postgres-dev psql -U user -d produtos_db

stage_old: ## Executa script de staging dentro do container
	docker exec -it site python3 scripts/stage_products.py


mc-alias:  ## Cria alias do cliente MinIO (MC)
	docker run --rm --network=v_m_backend minio/mc \
	alias set localminio http://minio:9000 minio minio123


run-py: ## Roda um script Python dentro do container site-dev
	@if ! docker ps | grep -q site-dev; then \
		echo "🛠️  Container site-dev não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site-dev python3 $(script)

stage: ## Executa o stage_products.py dentro do site-dev
	@if ! docker ps | grep -q site-dev; then \
		echo "🛠️  Container site-dev não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site-dev python3 scripts/stage_products.py

prepare-products: ## Executa generate_staging_json.py dentro do site-dev
	$(MAKE) run-py script=scripts/generate_staging_json.py


help: ## Mostra esta ajuda
	@echo "🛠️  Comandos disponíveis:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9._-]+:.*##/ {printf "👉 \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-stage:
	@$(MAKE) run-py script=scripts/check_stage_images.py

prune:clean-images
	docker system prune -f --volumes

clean-images:
	@if [ -n "$$(docker images -q)" ]; then \
		echo "🔴 Removendo todas as imagens Docker..."; \
		docker rmi -f $$(docker images -q); \
	else \
		echo "✅ Nenhuma imagem para remover."; \
	fi
