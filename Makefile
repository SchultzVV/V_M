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
	@echo "🚀 Iniciando túnel com ngrok (URL aleatória - plano free)..."
	@ngrok http --request-header-add="ngrok-skip-browser-warning:true" https://localhost:5000 > /dev/null &
	@sleep 6
	@echo "🌐 URL pública gerada:"
	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'
	@echo ""
	@echo "⚠️  IMPORTANTE: Copie a URL acima e adicione no painel do Mercado Livre:"
	@echo "   https://developers.mercadolivre.com.br/devcenter"
	@echo "   Redirect URI: <URL_ACIMA>/auth/mercadolivre/callback"

test-oauth:  ## Testa o fluxo OAuth - Abre navegador para autorizar
	@echo "🔑 Testando OAuth do Mercado Livre..."
	@echo ""
	@echo "📋 Configuração atual:"
	@grep "ML_APP_ID" .env | head -1
	@grep "ML_REDIRECT_URI" .env
	@echo ""
	@echo "🌐 Método 1 - Via nosso site (redirect automático):"
	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url' | xargs -I {} echo "{}/auth/mercadolivre/login"
	@echo ""
	@echo "🌐 Método 2 - URL Direta do Mercado Livre:"
	@./test_oauth_direct.sh | grep "https://auth.mercadolivre" | head -1
	@echo ""
	@echo "💡 Recomendado: Use o Método 2 (URL direta) para evitar bloqueios"
	@echo "✅ Após autorizar, verifique os tokens com: make check-tokens"

check-tokens:  ## Verifica se os tokens OAuth foram salvos
	@echo "🔍 Verificando tokens salvos..."
	@echo ""
	@docker exec site cat /app/config/ml_tokens.json 2>/dev/null | jq -r '"✅ User ID: " + (.user_id | tostring), "✅ Token expira em: " + (.expires_in | tostring) + " segundos", "✅ Access Token: " + .access_token[:30] + "...", "✅ Refresh Token: " + .refresh_token[:30] + "..."' || echo "❌ Arquivo de tokens não encontrado"
	@echo ""
	@echo "💡 Para testar o token, use: make test-api"

test-api:  ## Testa chamada à API do Mercado Livre com token OAuth
	@echo "🧪 Testando API do Mercado Livre..."
	@echo ""
	@TOKEN=$$(docker exec site cat /app/config/ml_tokens.json 2>/dev/null | jq -r '.access_token'); \
	if [ -z "$$TOKEN" ]; then \
		echo "❌ Token não encontrado. Execute: make test-oauth"; \
		exit 1; \
	fi; \
	echo "📡 Buscando dados do usuário..."; \
	curl -s -H "Authorization: Bearer $$TOKEN" https://api.mercadolibre.com/users/me | jq '{id, nickname, email, pontos: .points, reputacao: .seller_reputation.level_id}'

serve-render:  ## Deploy no Render.com (produção gratuita)
	@echo "📦 Verificando configuração do Git..."
	@if [ -z "$$(git config user.email)" ]; then \
		echo "⚠️  Configurando Git..."; \
		git config user.email "$(GITHUB_USERNAME)@users.noreply.github.com"; \
		git config user.name "$(GITHUB_USERNAME)"; \
	fi
	@echo "📝 Commitando alterações locais..."
	@git add -A
	@git diff-index --quiet HEAD || git commit -m "Deploy to Render - $$(date '+%Y-%m-%d %H:%M:%S')" || true
	@echo "🚀 Enviando para o GitHub (branch main)..."
	@git push origin $$(git branch --show-current):main || git push origin main
	@echo ""
	@echo "✅ Código enviado para GitHub!"
	@echo ""
	@echo "📋 PRÓXIMOS PASSOS:"
	@echo "1. Acesse: https://dashboard.render.com/"
	@echo "2. Clique em 'New +' → 'Web Service'"
	@echo "3. Conecte seu repositório: schultzvv/V_M"
	@echo "4. Render vai detectar o .render.yaml automaticamente"
	@echo "5. Configure as variáveis de ambiente necessárias"
	@echo "6. Clique em 'Create Web Service'"
	@echo ""
	@echo "⏳ Deploy leva ~5-10 minutos. Sua URL será:"
	@echo "   https://vm-site.onrender.com"
	@echo ""
	@echo "🔗 Use essa URL no Mercado Livre:"
	@echo "   Redirect URI: https://vm-site.onrender.com/auth/mercadolivre/callback"


# serve-ngrok:  ## Inicia túnel ngrok para acessar localmente via web
# 	@echo "🛑 Encerrando ngrok anterior, se existir..."
# 	@pkill ngrok || true
# 	@echo "🔧 Subindo containers Docker..."
# 	@$(COMPOSE) up -d
# 	@echo "🚀 Iniciando túnel com ngrok..."
# 	@ngrok http 5000 > /dev/null &
# 	@sleep 3
# 	@echo "🌐 URL pública gerada:"
# 	@curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'

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

prepare-auto: ## Prepara produto automaticamente do Mercado Livre (uso: make prepare-auto URL=https://...)
	@if [ -z "$(URL)" ]; then \
		echo "❌ Erro: URL não fornecida"; \
		echo ""; \
		echo "Uso: make prepare-auto URL=https://mercadolivre.com/sec/ABC123"; \
		exit 1; \
	fi
	@if ! docker ps | grep -q site-dev; then \
		echo "🛠️  Container site-dev não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "🤖 Preparando produto automaticamente..."
	@docker exec -it site-dev python3 scripts/auto_prepare_ml.py "$(URL)"

migrate-tags: ## Executa a migração para adicionar coluna tags
	@if ! docker ps | grep -q site-dev; then \
		echo "🛠️  Container site-dev não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site-dev python3 scripts/migrate_add_tags.py

migrate-webhook: ## Executa a migração para adicionar campos de webhook
	@if ! docker ps | grep -q site-dev; then \
		echo "🛠️  Container site-dev não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site-dev python3 scripts/migrate_add_webhook_fields.py


help: ## Mostra esta ajuda
	@echo "🛠️  Comandos disponíveis:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9._-]+:.*##/ {printf "👉 \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

help-products: ## Mostra ajuda para adicionar produtos
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🤖 FLUXO AUTOMÁTICO - Adicionar Produto do Mercado Livre"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "1️⃣  Preparar produto automaticamente:"
	@echo "   make prepare-auto URL=\"https://produto.mercadolivre.com.br/MLB-...\""
	@echo ""
	@echo "   ✅ Faz scraping do produto"
	@echo "   ✅ Baixa imagens automaticamente"
	@echo "   ✅ Detecta categoria"
	@echo "   ✅ Gera JSON de staging"
	@echo ""
	@echo "2️⃣  Publicar no site:"
	@echo "   make stage"
	@echo ""
	@echo "   ✅ Upload de imagens para MinIO"
	@echo "   ✅ Adiciona ao banco de dados"
	@echo "   ✅ Produto disponível no site"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📝 MÉTODO MANUAL (legacy):"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "   make prepare-products  # Digite dados manualmente"
	@echo "   make stage             # Publicar"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📚 Documentação completa: services/site/docs/AUTO_PREPARE_PRODUTOS.md"
	@echo ""

check-stage:
	@$(MAKE) run-py script=scripts/check_stage_images.py

prune:clean-images
	docker system prune -f --volumes

clean-images:
	@if [ -n "$$(docker images -q)" ]; then \
		echo "🔴 Removendo todas as imagens Docker..."; \
		docker stop $$(docker ps -q); \
		docker rmi -f $$(docker images -q); \
	else \
		echo "✅ Nenhuma imagem para remover."; \
	fi
