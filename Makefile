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
	@echo "🔧 Subindo containers Docker em modo desenvolvimento..."
	$(COMPOSE) up -d --build
	@echo ""
	@echo "✅ Ambiente iniciado com sucesso!"
	@echo ""
	@echo "🌐 Acesso local:"
	@echo "   https://localhost:5000"
	@echo ""
	@echo "📋 Comandos úteis:"
	@echo "   make logs-site        - Ver logs em tempo real"
	@echo "   make serve-ngrok      - Expor via ngrok (para webhooks ML)"
	@echo "   make down             - Parar containers"
	@echo ""

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

shell-site:  ## Abre shell bash dentro do container site
	@docker exec -it site /bin/bash

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

oauth-url:  ## Gera URL de autenticação OAuth com ngrok atual
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔑 URL DE AUTENTICAÇÃO OAUTH - MERCADO LIVRE"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@NGROK_URL=$$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url' 2>/dev/null); \
	if [ -z "$$NGROK_URL" ] || [ "$$NGROK_URL" = "null" ]; then \
		echo "❌ Ngrok não está rodando!"; \
		echo ""; \
		echo "Execute primeiro: make serve-ngrok"; \
		exit 1; \
	fi; \
	APP_ID=$$(grep "^ML_APP_ID=" .env | cut -d'=' -f2); \
	AUTH_URL="https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=$$APP_ID&redirect_uri=$$NGROK_URL/auth/mercadolivre/callback"; \
	echo "🌐 URL do ngrok atual:"; \
	echo "   $$NGROK_URL"; \
	echo ""; \
	echo "🔗 Cole esta URL no navegador para autorizar:"; \
	echo ""; \
	echo "$$AUTH_URL"; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "⚠️  IMPORTANTE: Cadastre no painel do Mercado Livre:"
	@echo "   https://developers.mercadolivre.com.br/devcenter"
	@echo ""
	@NGROK_URL=$$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url' 2>/dev/null); \
	echo "   Redirect URI: $$NGROK_URL/auth/mercadolivre/callback"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

update-ngrok-url:  ## Atualiza .env e reinicia containers com nova URL do ngrok
	@echo ""
	@echo "🔄 Atualizando configuração do ngrok..."
	@echo ""
	@NGROK_URL=$$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[0].public_url' 2>/dev/null); \
	if [ -z "$$NGROK_URL" ] || [ "$$NGROK_URL" = "null" ]; then \
		echo "❌ Ngrok não está rodando!"; \
		echo "Execute primeiro: make serve-ngrok"; \
		exit 1; \
	fi; \
	OLD_URL=$$(grep "^ML_REDIRECT_URI=" .env | cut -d'=' -f2); \
	NEW_URL="$$NGROK_URL/auth/mercadolivre/callback"; \
	echo "🔗 URL antiga: $$OLD_URL"; \
	echo "🔗 URL nova:   $$NEW_URL"; \
	echo ""; \
	if [ "$$OLD_URL" = "$$NEW_URL" ]; then \
		echo "✅ URL já está atualizada!"; \
		exit 0; \
	fi; \
	echo "📝 Atualizando .env..."; \
	sed -i "s|^ML_REDIRECT_URI=.*|ML_REDIRECT_URI=$$NEW_URL|" .env; \
	echo "✅ .env atualizado"; \
	echo ""; \
	echo "🔄 Reiniciando containers para carregar nova URL..."; \
	docker-compose down > /dev/null 2>&1; \
	docker-compose up -d > /dev/null 2>&1; \
	sleep 3; \
	echo "✅ Containers reiniciados"; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "⚠️  PRÓXIMOS PASSOS:"; \
	echo ""; \
	echo "1. Cadastre no painel ML: https://developers.mercadolivre.com.br/devcenter"; \
	echo "   Redirect URI: $$NEW_URL"; \
	echo ""; \
	echo "2. Autorize novamente: make oauth-url"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

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


run-py: ## Roda um script Python dentro do container site
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site python3 $(script)

stage: ## Executa o stage_products.py dentro do site
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site python3 scripts/stage_products.py

prepare-publish: ## Gera imagens prontas para publicação no Instagram a partir do staging
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎨 PREPARANDO IMAGENS PARA PUBLICAÇÃO NO INSTAGRAM"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@docker exec -it site python3 scripts/prepare_publish_images.py --all
	@echo ""
	@echo "✅ Imagens prontas! Acesse: services/site/publish_ready/"
	@echo ""

prepare-products: ## Executa generate_staging_json.py dentro do site
	$(MAKE) run-py script=scripts/generate_staging_json.py

prepare-auto: ## Prepara produto via scraping HTML (uso: make prepare-auto URL=https://...)
	@if [ -z "$(URL)" ]; then \
		echo "❌ Erro: URL não fornecida"; \
		echo ""; \
		echo "Uso: make prepare-auto URL=https://mercadolivre.com/sec/ABC123"; \
		exit 1; \
	fi
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "🤖 Preparando produto via scraping..."
	@docker exec -it site python3 scripts/auto_prepare_ml.py "$(URL)"

api-prepare-product: ## Prepara produto via API oficial (uso: make api-prepare-product URL=https://...)
	@if [ -z "$(URL)" ]; then \
		echo "❌ Erro: URL não fornecida"; \
		echo ""; \
		echo "Uso: make api-prepare-product URL=https://mercadolivre.com/sec/ABC123"; \
		echo "     make api-prepare-product URL=https://produto.mercadolivre.com.br/MLB-..."; \
		exit 1; \
	fi
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📂 CATEGORIAS DISPONÍVEIS:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "   1. geral    - Produtos gerais (padrão)"
	@echo "   2. E        - Eletrônicos"
	@echo "   3. CD       - Casa & Decoração"
	@echo "   4. ME       - Moda & Estilo"
	@echo "   5. PET      - Pet Shop"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@read -p "🏷️  Digite a categoria (geral/E/CD/ME/PET) ou Enter para 'geral': " CATEGORIA; \
	CATEGORIA=$${CATEGORIA:-geral}; \
	echo ""; \
	echo "🚀 Preparando produto via API oficial..."; \
	echo "📂 Categoria selecionada: $$CATEGORIA"; \
	echo ""; \
	docker exec -it site python3 scripts/api_prepare_ml.py "$(URL)" "$$CATEGORIA"

prepare-all: ## Prepara TODOS os produtos da lista (list_to_prepare.json)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PREPARAÇÃO EM LOTE - TODOS OS PRODUTOS"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@TOTAL=$$(cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq '.links | length'); \
	echo "📦 Total de produtos na fila: $$TOTAL"; \
	echo ""; \
	read -p "⚠️  Deseja continuar? Você escolherá a categoria de cada produto. (s/N): " CONFIRMA; \
	if [ "$$CONFIRMA" != "s" ] && [ "$$CONFIRMA" != "S" ]; then \
		echo "❌ Operação cancelada."; \
		exit 0; \
	fi; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🔄 INICIANDO PROCESSAMENTO..."; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	CONTADOR=0; \
	SUCESSO=0; \
	ERRO=0; \
	cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq -r '.links[].url' | while read URL; do \
		CONTADOR=$$((CONTADOR + 1)); \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "📦 Produto $$CONTADOR/$$TOTAL"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "🔗 URL: $$URL"; \
		echo ""; \
		echo "📂 CATEGORIAS DISPONÍVEIS:"; \
		echo "   1. geral    - Produtos gerais (padrão)"; \
		echo "   2. E        - Eletrônicos"; \
		echo "   3. CD       - Casa & Decoração"; \
		echo "   4. ME       - Moda & Estilo"; \
		echo "   5. PET      - Pet Shop"; \
		echo ""; \
		read -p "🏷️  Categoria para este produto (ou Enter para 'geral'): " CATEGORIA; \
		CATEGORIA=$${CATEGORIA:-geral}; \
		echo ""; \
		echo "✅ Categoria: $$CATEGORIA"; \
		echo ""; \
		if docker exec site python3 scripts/api_prepare_ml.py "$$URL" "$$CATEGORIA"; then \
			echo ""; \
			echo "✅ Produto $$CONTADOR preparado com sucesso!"; \
			SUCESSO=$$((SUCESSO + 1)); \
		else \
			echo ""; \
			echo "❌ Erro ao processar produto $$CONTADOR"; \
			ERRO=$$((ERRO + 1)); \
		fi; \
		echo ""; \
		read -p "⏸️  Pressione Enter para continuar com o próximo produto..."; \
	done; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✅ PROCESSAMENTO CONCLUÍDO!"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	echo "📊 Resumo:"; \
	echo "   Total processados: $$TOTAL produtos"; \
	echo ""; \
	echo "💡 IMPORTANTE: Verifique os JSONs gerados em staging/"; \
	echo ""; \
	echo "📋 Próximo passo:"; \
	echo "   make stage    # Publicar todos os produtos preparados"; \
	echo ""

migrate-tags: ## Executa a migração para adicionar coluna tags
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site python3 scripts/migrate_add_tags.py

migrate-webhook: ## Executa a migração para adicionar campos de webhook
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site python3 scripts/migrate_add_webhook_fields.py


help: ## Mostra esta ajuda
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🛠️  COMANDOS DISPONÍVEIS"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📦 DESENVOLVIMENTO:"
	@awk 'BEGIN {FS = ":.*?## "} /^(up|down|restart-site|redo-site|logs-site):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🌐 NGROK & DEPLOY:"
	@awk 'BEGIN {FS = ":.*?## "} /^(serve-ngrok|serve-render):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🔑 OAUTH MERCADO LIVRE:"
	@awk 'BEGIN {FS = ":.*?## "} /^(oauth-url|update-ngrok-url|test-oauth|check-tokens|test-api):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🤖 PRODUTOS (Mercado Livre):"
	@awk 'BEGIN {FS = ":.*?## "} /^(prepare-auto|api-prepare-product|stage|prepare-products):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🗄️  BANCO DE DADOS:"
	@awk 'BEGIN {FS = ":.*?## "} /^(migrate-tags|migrate-webhook):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🚀 PRODUÇÃO:"
	@awk 'BEGIN {FS = ":.*?## "} /^(prd-up|prd-down|prd-up-ghcr):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🧹 LIMPEZA:"
	@awk 'BEGIN {FS = ":.*?## "} /^(prune|clean-images|clear-minio|clear-minio-force):.*##/ {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "💡 AJUDA DETALHADA:"
	@echo "   make help-products  - Guia completo de produtos"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

help-products: ## Mostra ajuda para adicionar produtos
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🤖 FLUXO AUTOMÁTICO - Adicionar Produto do Mercado Livre"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀 MÉTODO RECOMENDADO - API Oficial (OAuth necessário):"
	@echo "   make api-prepare-product URL=\"https://mercadolivre.com/sec/ABC123\""
	@echo ""
	@echo "   ✅ Dados 100% precisos da API oficial"
	@echo "   ✅ Imagens em alta qualidade"
	@echo "   ✅ Preços e descontos reais"
	@echo "   ✅ Vídeos do produto (se houver)"
	@echo "   ✅ Resolve links de afiliado automaticamente"
	@echo ""
	@echo "🔄 MÉTODO ALTERNATIVO - Scraping HTML (sem OAuth):"
	@echo "   make prepare-auto URL=\"https://produto.mercadolivre.com.br/MLB-...\""
	@echo ""
	@echo "   ✅ Funciona sem autenticação"
	@echo "   ⚠️  Imagens podem vir incorretas"
	@echo "   ⚠️  Preços podem estar desatualizados"
	@echo ""
	@echo "📤 PUBLICAR NO SITE:"
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

check-stage: ## Verifica imagens no staging
	@$(MAKE) run-py script=scripts/check_stage_images.py

# =====================
# 📸 Instagram
# =====================

instagram-post: ## Posta produto no Instagram (modo automático)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "📸 Postando automaticamente no Instagram..."
	@curl -X POST "http://localhost:5000/instagram/post/auto?simulate=false" \
		-H "Content-Type: application/json" | jq .

instagram-test: ## Testa postagem Instagram (não posta de verdade)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "🎭 Testando postagem Instagram (modo simulação)..."
	@curl -X POST "http://localhost:5000/instagram/post/auto?simulate=true" \
		-H "Content-Type: application/json" | jq .

instagram-status: ## Verifica status do sistema Instagram
	@echo "🔍 Verificando status do sistema Instagram..."
	@curl -s "http://localhost:5000/instagram/status" | jq .

instagram-history: ## Mostra histórico de posts no Instagram
	@echo "📋 Histórico de posts no Instagram..."
	@curl -s "http://localhost:5000/instagram/history?limit=10" | jq .

instagram-workflow: ## Mostra diagrama do workflow dos agentes
	@curl -s "http://localhost:5000/instagram/workflow" | jq -r '.workflow_diagram'

instagram-test-system: ## Testa todos os componentes do sistema Instagram
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "🧪 Testando sistema completo..."
	@docker exec -it site python3 test_instagram_system.py

stage-and-post: ## Publica no ML e posta automaticamente no Instagram
	@echo "🚀 Executando fluxo completo: ML + Instagram"
	@$(MAKE) stage
	@sleep 2
	@$(MAKE) instagram-post

insta-publish: ## Publica produto no Instagram (sem LLM, direto)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "📸 Publicando no Instagram..."
	@curl -k -X POST "https://localhost:5000/instagram/post/auto?simulate=false" \
		-H "Content-Type: application/json" | jq .

insta-test: ## Testa publicação Instagram (modo simulação)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@echo "🎭 Testando publicação Instagram (simulação)..."
	@curl -k -X POST "https://localhost:5000/instagram/post/auto?simulate=true" \
		-H "Content-Type: application/json" | jq .

clear-minio: ## Remove TODAS as imagens do MinIO (com confirmação)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site python3 scripts/clear_minio_images.py

clear-minio-force: ## Remove TODAS as imagens do MinIO (SEM confirmação - cuidado!)
	@if ! docker ps | grep -q site; then \
		echo "🛠️  Container site não encontrado. Subindo com docker-compose..."; \
		$(COMPOSE) up -d --build site; \
	fi
	@docker exec -it site python3 scripts/clear_minio_images.py --force

prune: ## Remove containers, volumes e imagens não utilizadas
	docker system prune -f --volumes

clean-images: ## Remove TODAS as imagens Docker (cuidado!)
	@if [ -n "$$(docker images -q)" ]; then \
		echo "🔴 Removendo todas as imagens Docker..."; \
		docker stop $$(docker ps -q); \
		docker rmi -f $$(docker images -q); \
	else \
		echo "✅ Nenhuma imagem para remover."; \
	fi
