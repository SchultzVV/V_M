# ============================================================
# 🛠️  V_M — Makefile
# Fluxo principal:
#   1. make serve-cloudflare         → sobe tudo + túnel + auto-OAuth
#   2. make prepare-ml URL=...       → prepara produto do ML
#      make prepare-shopee URL=...   → prepara produto da Shopee
#      make prepare-amazon URL=...   → prepara produto da Amazon
#   3. make stage                    → publica produto no site + DB
#   4. make instagram-post           → posta no Instagram (feed + story)
#   5. make api-update URL=...       → atualiza preço/disponibilidade
# ============================================================

include .env
export

ifeq ($(filter prd-up prd-down prd-up-ghcr,$(MAKECMDGOALS)),$(MAKECMDGOALS))
  include .env.prd
endif

TAG        ?= latest
GHCR_USER   = $(GITHUB_USERNAME)
GHCR_TOKEN  = $(GITHUB_TOKEN)
IMAGE_NAME  = ghcr.io/$(GHCR_USER)/site:$(TAG)
COMPOSE     = docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml --env-file .env

.DEFAULT_GOAL := help

# ============================================================
# 🧪  DEV
# ============================================================

up:  ## Sobe ambiente de desenvolvimento (build + detach)
	@echo "🔧 Subindo containers..."
	$(COMPOSE) up -d --build
	@echo "✅ Backend em https://localhost:5555"
	@echo "✅ Frontend: make frontend-dev (http://localhost:5173)"
	@echo "💡 Para site completo local: make frontup"
	@echo "💡 Para expor público:       make serve-cloudflare"

down:  ## Para containers (preserva volumes/banco de dados)
	$(COMPOSE) down

down-purge:  ## ⚠️  DESTRÓI VOLUMES — apaga banco, minio e redis permanentemente
	@echo ""
	@echo "⚠️  ATENÇÃO: isto vai APAGAR PERMANENTEMENTE:"
	@echo "   • Banco de dados PostgreSQL (produtos, configurações)"
	@echo "   • Imagens do MinIO"
	@echo "   • Cache do Redis"
	@echo ""
	@echo "   Pressione Ctrl+C para cancelar (5 segundos)..."; sleep 5
	$(COMPOSE) down -v
	@echo "✅ Volumes removidos"

restart-site:  ## Reinicia apenas o container site
	$(COMPOSE) restart site

rebuild-site:  ## Rebuild completo apenas do site
	$(COMPOSE) stop site
	$(COMPOSE) rm -f site
	$(COMPOSE) build site
	$(COMPOSE) up -d site

rebuild-info-scrap:  ## Rebuild completo info-scrap (pull + down + rm + up)
	@echo "🔄 Fazendo rebuild completo do info-scrap..."
	@echo "  1. Pull da imagem..."
	@docker pull ghcr.io/schultzvv/info_scrap:latest
	@echo "  2. Parando container..."
	@$(COMPOSE) stop info-scrap 2>/dev/null || true
	@echo "  3. Removendo container..."
	@$(COMPOSE) rm -f info-scrap
	@echo "  4. Subindo com imagem atualizada..."
	@$(COMPOSE) up -d info-scrap
	@sleep 2
	@echo "✅ info-scrap rebuild completo!"
	@echo "   Status:" && docker ps --filter name=info-scrap --format "{{.Names}}: {{.Status}}"

logs:  ## Logs em tempo real do site
	$(COMPOSE) logs -f site

shell:  ## Shell bash dentro do container site
	@docker exec -it site /bin/bash

psql:  ## Terminal psql no container postgres
	docker exec -it postgres-dev psql -U user -d produtos_db

# ============================================================
# 🎨  FRONTEND — React + Vite development
# ============================================================

frontend-install:  ## Instala dependências do frontend
	@echo "📦 Installing npm packages..."
	@cd frontend && npm install

frontend-dev:  ## Inicia dev server frontend (localhost:5173)
	@echo "🚀 Starting frontend dev server..."
	@cd frontend && npm run dev

frontend-build:  ## Build production frontend
	@echo "🏗️  Building frontend for production..."
	@cd frontend && npm run build
	@echo "✅ Build completo em ./frontend/dist/"

frontend-clean:  ## Remove node_modules e dist (limpa cache)
	@rm -rf frontend/node_modules frontend/dist
	@echo "✅ Frontend limpo"

frontend-build-prod:  ## Build React para produção com Nginx (alias melhorado)
	@echo "🏗️  Building React frontend for production..."
	@cd frontend && npm run build
	@echo "✅ Build completo: ./frontend/dist/"
	@echo "   $(shell du -sh frontend/dist)"
	@echo "   Pronto para servir com Nginx!"

frontup:  ## ⭐ Sobe site completo para testes locais (build React + Nginx + Backend)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 FRONTUP — React + Nginx + Backend (local, sem túnel)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🏗️  Buildando React..."
	@rm -rf frontend/dist/assets frontend/dist/*.js frontend/dist/*.css frontend/dist/index.html 2>/dev/null; mkdir -p frontend/dist
	@cd frontend && npm run build > /dev/null 2>&1 || (echo "❌ Build falhou"; exit 1)
	@echo "✅ Build completo"
	@echo ""
	@echo "🐳 Subindo containers..."
	@docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml -f docker-compose.react.yaml --env-file .env up -d --force-recreate nginx
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Site: https://localhost"
	@echo "✅ API:  https://localhost/api/products"
	@echo "✅ Flask direto: https://localhost:5555"
	@echo "✅ MinIO: http://localhost:9000"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""


# ============================================================
# 🌐  EXPOSE — Túneis HTTPS públicos
# ============================================================

serve-cloudflare:  ## ⭐ Túnel Cloudflare (Flask): Backend HTTP + tunnel + auto-OAuth ML
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 CLOUDFLARE TUNNEL  +  FLASK BACKEND  +  AUTO-CONFIG OAUTH"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Step 0️⃣  Housekeeping — removendo config persistente de quick tunnel...";\
	if [ -f ~/.cloudflared/config.yml ]; then \
		mv ~/.cloudflared/config.yml ~/.cloudflared/config.yml.bak; \
		echo "   ✅ Config persistente movida para .bak (evita conflito)"; \
	fi; \
	echo ""
	@echo "Step 1️⃣  Subindo containers (Backend apenas — sem serviços LLM)..."; \
	$(COMPOSE) up -d --no-deps db minio redis site; \
	sleep 2; \
	echo "✅ Backend Flask em https://localhost:5555"; \
	echo ""
	@bash scripts/ensure_products.sh
	@echo "Step 2️⃣  Iniciando túnel Cloudflare..."; \
	bash scripts/tunnel-manager.sh /tmp/cloudflare_tunnel.log "https://127.0.0.1:5555" 20 > /tmp/cf_url.txt; \
	CF_URL=$$(cat /tmp/cf_url.txt); \
	if [ -z "$$CF_URL" ] || ! echo "$$CF_URL" | grep -q "https://"; then \
		echo "❌ Falha ao capturar URL do túnel"; \
		cat /tmp/cloudflare_tunnel.log; \
		exit 1; \
	fi; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✅ TÚNEL ATIVO: $$CF_URL"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "$$CF_URL" > /tmp/cf_active_url.txt; \
	echo "backend" >> /tmp/cf_active_url.txt; \
	echo ""; \
	NEW_REDIRECT="$$CF_URL/auth/mercadolivre/callback"; \
	echo "Step 3️⃣  Atualizando ML_REDIRECT_URI..."; \
	if grep -q '^ML_REDIRECT_URI=' .env; then \
		sed -i "s|^ML_REDIRECT_URI=.*|ML_REDIRECT_URI=$$NEW_REDIRECT|" .env; \
	else \
		echo "ML_REDIRECT_URI=$$NEW_REDIRECT" >> .env; \
	fi; \
	echo "✅ .env atualizado"; \
	echo ""
	@echo "Step 4️⃣  Reiniciando backend com nova URI..."; \
	$(COMPOSE) restart site > /dev/null 2>&1; \
	sleep 2; \
	echo "✅ Backend reiniciado"; \
	echo ""
	@APP_ID=$$(grep "^ML_APP_ID=" .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	TOKEN=$$(docker exec site cat /app/config/ml_tokens.json 2>/dev/null | jq -r '.access_token // empty' 2>/dev/null); \
	TOKEN_OK=0; \
	if [ -n "$$TOKEN" ]; then \
		STATUS=$$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $$TOKEN" https://api.mercadolibre.com/users/me); \
		[ "$$STATUS" = "200" ] && TOKEN_OK=1; \
	fi; \
	CF_URL=$$(cat /tmp/cf_url.txt); \
	NEW_REDIRECT="$$CF_URL/auth/mercadolivre/callback"; \
	AUTH_URL="https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=$$APP_ID&redirect_uri=$$NEW_REDIRECT"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	if [ "$$TOKEN_OK" = "1" ]; then \
		echo "🔑 TOKEN ML: ✅ válido"; \
	else \
		echo "🔑 TOKEN ML: ❌ expirado ou ausente"; \
	fi; \
	echo ""; \
	echo "1️⃣  Cadastre o Redirect URI no DevCenter ML (nova URL a cada run):"; \
	echo "   https://developers.mercadolivre.com.br/devcenter"; \
	echo "   → URL: $$NEW_REDIRECT"; \
	echo ""; \
	echo "2️⃣  Abra no navegador para autorizar (ou re-autorizar):"; \
	echo "   $$AUTH_URL"; \
	echo ""; \
	echo "3️⃣  Após autorizar: make check-tokens"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	echo "🔗 API pública via Cloudflare:"; \
	echo "   $$CF_URL"; \
	echo ""; \
	echo "💡 Para parar: make stop-cloudflare"; \
	echo ""
serve-frontend-public:  ## ⭐ Frontend React (build agressivo + Nginx + reutiliza tunnel)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 REACT FRONTEND  +  NGINX  +  CLOUDFLARE TUNNEL (compartilhado)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "✨ Este comando reutiliza o tunnel de 'make serve-cloudflare'"
	@echo "   Se nenhum tunnel está rodando, um novo será criado"
	@echo ""
	@echo "Step 1️⃣  Limpando build anterior (preservando pasta para inode estável)..."
	@rm -rf frontend/dist/assets frontend/dist/*.js frontend/dist/*.css frontend/dist/index.html 2>/dev/null; mkdir -p frontend/dist
	@echo "✅ Limpeza completa"
	@echo ""
	@echo "Step 2️⃣  Building React frontend (fresh build)..."; \
	cd frontend && npm run build > /dev/null 2>&1 || (echo "❌ Build falhou"; exit 1); \
	echo "✅ React build completo (fresh)"; \
	echo ""
	@echo "Step 3️⃣  Subindo containers (Backend + Nginx — sem serviços LLM)..."; \
	docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml -f docker-compose.react.yaml --env-file .env up -d --no-deps db minio redis site nginx; \
	sleep 2; \
	echo "✅ Flask API em https://localhost:5555"; \
	echo "✅ Site (Nginx/Frontend) em https://localhost"; \
	echo ""
	@bash scripts/ensure_products.sh
	@echo "Step 4️⃣  Iniciando túnel Cloudflare..."; \
	bash scripts/tunnel-manager.sh /tmp/cloudflare_tunnel.log "https://127.0.0.1:443" 20 > /tmp/cf_url.txt; \
	CF_URL=$$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' /tmp/cf_url.txt | head -1); \
	if [ -z "$$CF_URL" ] || ! echo "$$CF_URL" | grep -q "https://"; then \
		echo "❌ Falha ao capturar URL do túnel"; \
		cat /tmp/cloudflare_tunnel.log; \
		exit 1; \
	fi; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✅ REACT FRONTEND ATIVO: $$CF_URL"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "$$CF_URL" > /tmp/cf_active_url.txt; \
	echo "frontend" >> /tmp/cf_active_url.txt; \
	echo ""; \
	NEW_REDIRECT="$$CF_URL/auth/mercadolivre/callback"; \
	echo "Step 5️⃣  Atualizando ML_REDIRECT_URI..."; \
	if grep -q '^ML_REDIRECT_URI=' .env; then \
		sed -i "s|^ML_REDIRECT_URI=.*|ML_REDIRECT_URI=$$NEW_REDIRECT|" .env; \
	else \
		echo "ML_REDIRECT_URI=$$NEW_REDIRECT" >> .env; \
	fi; \
	echo "✅ .env atualizado"; \
	echo ""
	@echo "Step 6️⃣  Reiniciando backend..."; \
	$(COMPOSE) restart site > /dev/null 2>&1; \
	sleep 2; \
	echo "✅ Backend reiniciado"; \
	echo ""
	@APP_ID=$$(grep "^ML_APP_ID=" .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	TOKEN=$$(docker exec site cat /app/config/ml_tokens.json 2>/dev/null | jq -r '.access_token // empty' 2>/dev/null); \
	TOKEN_OK=0; \
	if [ -n "$$TOKEN" ]; then \
		STATUS=$$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $$TOKEN" https://api.mercadolibre.com/users/me); \
		[ "$$STATUS" = "200" ] && TOKEN_OK=1; \
	fi; \
	CF_URL=$$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' /tmp/cf_url.txt | head -1); \
	NEW_REDIRECT="$$CF_URL/auth/mercadolivre/callback"; \
	AUTH_URL="https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=$$APP_ID&redirect_uri=$$NEW_REDIRECT"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	if [ "$$TOKEN_OK" = "1" ]; then \
		echo "🔑 TOKEN ML: ✅ válido"; \
	else \
		echo "🔑 TOKEN ML: ❌ expirado ou ausente"; \
	fi; \
	echo ""; \
	echo "1️⃣  Cadastre o Redirect URI no DevCenter ML (nova URL a cada run):"; \
	echo "   https://developers.mercadolivre.com.br/devcenter"; \
	echo "   → URL: $$NEW_REDIRECT"; \
	echo ""; \
	echo "2️⃣  Abra no navegador para autorizar (ou re-autorizar):"; \
	echo "   $$AUTH_URL"; \
	echo ""; \
	echo "3️⃣  Após autorizar: make check-tokens"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	echo "📱 Frontend via Nginx:"; \
	echo "   $$CF_URL"; \
	echo ""; \
	echo "💡 Para parar: make stop-frontend-public"; \
	echo ""

stop-frontend-public:  ## Parar Frontend React (Nginx apenas — preserva tunnel compartilhado)
	@echo "🛑 Parando Nginx + containers..."
	@echo "⚠️  Nota: Tunnel Cloudflare permanece ativo para outros serviços"
	@docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml -f docker-compose.react.yaml --env-file .env down 2>&1 | grep -E "Removing|Stopping|done" || echo "✅ Containers parados"
	@echo "✅ React frontend encerrado"
	@echo "💡 Se quiser parar o tunnel: make stop-cloudflare"

stop-all:  ## Para ALL: Frontend + Backend + Tunnel
	@echo "🛑 Parando TUDO (containers + tunnel)..."
	@pkill cloudflared 2>/dev/null || true
	@$(COMPOSE) down 2>&1 | grep -E "Removing|Stopping|done" || echo "✅ Containers parados"
	@echo "✅ Sistema completamente encerrado"
stop-cloudflare:  ## Para o túnel Cloudflare em background
	@pkill cloudflared 2>/dev/null && echo "✅ Túnel encerrado" || echo "⚠️  Túnel não estava rodando"

tunnel-info:  ## 🔗 Mostra URL do túnel Cloudflare ativo AGORA (sem alterar nada ML)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 TÚNEL CLOUDFLARE ATIVO"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@LOG=/tmp/cloudflare_tunnel.log; \
	if [ -f "$$LOG" ]; then \
		TUNNEL_URL=$$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' $$LOG | head -1); \
		if [ -n "$$TUNNEL_URL" ]; then \
			echo "✅ TÚNEL ATIVO:"; \
			echo "   🌐 URL: $$TUNNEL_URL"; \
			echo "   🔗 Callback ML: $$TUNNEL_URL/auth/mercadolivre/callback"; \
			echo ""; \
			echo "⚠️  Copie o Callback acima se precisar atualizar o DevCenter ML"; \
			echo "   (mas NÃO mude se o link antigo ainda está funcionando)"; \
		else \
			echo "❌ Tunnel log encontrado mas sem URL. Execute: make serve-cloudflare"; \
		fi; \
	else \
		echo "❌ Nenhum túnel ativo encontrado."; \
		echo "   Execute: make serve-cloudflare"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

serve-ngrok:  ## Túnel ngrok com domínio estático (NGROK_SUBDOMAIN no .env)
	@pkill ngrok 2>/dev/null || true
	$(COMPOSE) up -d
	@SUBDOMAIN=$$(grep '^NGROK_SUBDOMAIN=' .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	if [ -n "$$SUBDOMAIN" ]; then \
		echo "🌐 Usando domínio estático: https://$$SUBDOMAIN.ngrok-free.app"; \
		ngrok http --domain=$$SUBDOMAIN.ngrok-free.app --request-header-add="ngrok-skip-browser-warning:true" https://localhost:5555 > /dev/null 2>&1 & \
	else \
		echo "🌐 Usando URL aleatória (defina NGROK_SUBDOMAIN no .env para URL fixa)"; \
		ngrok http --request-header-add="ngrok-skip-browser-warning:true" https://localhost:5555 > /dev/null 2>&1 & \
	fi
	@sleep 6
	@echo "🌐 URL ngrok:" && curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'

stop-ngrok:  ## Para o túnel ngrok
	@pkill ngrok 2>/dev/null && echo "✅ Ngrok encerrado" || echo "⚠️  Ngrok não estava rodando"

install-cloudflared:  ## Instala cloudflared (necessário para Cloudflare Tunnel)
	@if command -v cloudflared &> /dev/null; then echo "✅ Já instalado: $$(cloudflared --version)"; exit 0; fi
	@wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -O /tmp/cloudflared.deb
	@sudo dpkg -i /tmp/cloudflared.deb && rm /tmp/cloudflared.deb
	@echo "✅ cloudflared instalado: $$(cloudflared --version)"

setup-cloudflare-fixed:  ## Cria túnel Cloudflare com URL permanente (executar 1x)
	@CLOUDFLARED_BIN=$$(command -v cloudflared 2>/dev/null || echo /usr/local/bin/cloudflared); \
	if [ ! -x "$$CLOUDFLARED_BIN" ]; then echo "❌ Execute: make install-cloudflared"; exit 1; fi; \
	echo "🔑 Login Cloudflare (abrirá o browser)..."; \
	$$CLOUDFLARED_BIN login; \
	echo "🔧 Criando túnel 'def'..."; \
	$$CLOUDFLARED_BIN tunnel create def 2>/dev/null || echo "Túnel já existe"; \
	TUNNEL_ID=$$($$CLOUDFLARED_BIN tunnel list | grep ' def ' | awk '{print $$1}'); \
	echo "📝 Gerando ~/.cloudflared/config.yml..."; \
	printf "tunnel: %s\ncredentials-file: /home/%s/.cloudflared/%s.json\n\ningress:\n  - service: https://localhost:5555\n    originRequest:\n      noTLSVerify: true\n      connectTimeout: 30s\n      tlsTimeout: 30s\n      tcpKeepAlive: 30s\n      keepAliveConnections: 10\n      keepAliveTimeout: 90s\n" "$$TUNNEL_ID" "$$USER" "$$TUNNEL_ID" > ~/.cloudflared/config.yml; \
	CF_HOST=$$(grep '^CF_HOSTNAME=' .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	if [ -n "$$CF_HOST" ]; then \
		echo "🌐 Criando rota DNS: $$CF_HOST → túnel def..."; \
		$$CLOUDFLARED_BIN tunnel route dns def $$CF_HOST && echo "✅ CNAME criado!"; \
	fi; \
	echo "✅ Configurado! Use: make serve-cloudflare-fixed"

serve-cloudflare-fixed:  ## ⭐ Túnel Cloudflare URL FIXA: requer CF_HOSTNAME no .env (ex: def.seudominio.com)
	@CLOUDFLARED_BIN=$$(command -v cloudflared 2>/dev/null || echo /usr/local/bin/cloudflared); \
	if [ ! -x "$$CLOUDFLARED_BIN" ]; then echo "❌ Execute: make install-cloudflared"; exit 1; fi; \
	if [ ! -s ~/.cloudflared/config.yml ]; then echo "❌ Execute: make setup-cloudflare-fixed"; exit 1; fi; \
	CF_HOST=$$(grep '^CF_HOSTNAME=' .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	if [ -z "$$CF_HOST" ]; then \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "⚠️  URL FIXA não configurada"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo ""; \
		echo "Para ter URL fixa permanente no Cloudflare você precisa de"; \
		echo "um domínio próprio gerenciado pelo Cloudflare. Depois:"; \
		echo ""; \
		echo "  1. Adicione no .env:  CF_HOSTNAME=def.seudominio.com"; \
		echo "  2. Execute:           make setup-cloudflare-fixed"; \
		echo "     (cria o CNAME automaticamente)"; \
		echo "  3. Execute:           make serve-cloudflare-fixed"; \
		echo ""; \
		echo "Enquanto não tem domínio, use: make serve-cloudflare"; \
		echo "(URL muda mas tudo mais funciona igual)"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🔒 CLOUDFLARE TUNNEL — URL PERMANENTE  +  AUTO-CONFIG OAUTH ML"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	echo "🔧 Subindo containers..."; \
	$(COMPOSE) up -d; \
	sleep 2; \
	echo "✅ Flask API em https://localhost:5555"; \
	echo ""; \
	FIXED_URL="https://$$CF_HOST"; \
	APP_ID=$$(grep "^ML_APP_ID=" .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	NEW_REDIRECT="$$FIXED_URL/auth/mercadolivre/callback"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🌍 URL FIXA : $$FIXED_URL"; \
	echo "🔁 Callback : $$NEW_REDIRECT"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	echo "📝 Atualizando ML_REDIRECT_URI no .env..."; \
	if grep -q '^ML_REDIRECT_URI=' .env; then \
		sed -i "s|^ML_REDIRECT_URI=.*|ML_REDIRECT_URI=$$NEW_REDIRECT|" .env; \
	else \
		echo "ML_REDIRECT_URI=$$NEW_REDIRECT" >> .env; \
	fi; \
	echo "🔄 Reiniciando site com nova URI..."; \
	$(COMPOSE) stop site > /dev/null 2>&1; \
	$(COMPOSE) rm -f site > /dev/null 2>&1; \
	$(COMPOSE) up -d site > /dev/null 2>&1; \
	sleep 3; \
	echo "✅ Container reiniciado"; \
	echo ""; \
	TOKEN=$$(docker exec site cat /app/config/ml_tokens.json 2>/dev/null | jq -r '.access_token // empty' 2>/dev/null); \
	TOKEN_OK=0; \
	if [ -n "$$TOKEN" ]; then \
		STATUS=$$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $$TOKEN" https://api.mercadolibre.com/users/me); \
		[ "$$STATUS" = "200" ] && TOKEN_OK=1; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	if [ "$$TOKEN_OK" = "1" ]; then \
		echo "🔑 TOKEN ML: ✅ válido — não precisa reautorizar"; \
		echo ""; \
		echo "   Pode usar a API direto: make test-api"; \
	else \
		echo "🔑 TOKEN ML: ❌ expirado ou ausente — autorização necessária"; \
		echo ""; \
		AUTH_URL="https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=$$APP_ID&redirect_uri=$$NEW_REDIRECT"; \
		echo "1️⃣  Configure o Redirect URI no DevCenter ML (UMA VEZ só):"; \
		echo "   https://developers.mercadolivre.com.br/devcenter"; \
		echo "   → URL de redirecionamento: $$NEW_REDIRECT"; \
		echo ""; \
		echo "2️⃣  Abra no navegador para autorizar:"; \
		echo ""; \
		echo "   $$AUTH_URL"; \
		echo ""; \
		echo "3️⃣  Após autorizar: make check-tokens"; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🚀 Iniciando túnel (Ctrl+C para parar)..."; \
	echo "💡 Para parar: make stop-cloudflare"; \
	echo ""; \
	pkill cloudflared 2>/dev/null || true; sleep 1; \
	$$CLOUDFLARED_BIN tunnel run


# ============================================================
# 🔑  OAUTH — Mercado Livre
# ============================================================

check-tokens:  ## Verifica tokens OAuth salvos no container
	@docker exec site cat /app/config/ml_tokens.json 2>/dev/null \
		| jq -r '"✅ User ID: " + (.user_id|tostring), "✅ Expira em: " + (.expires_in|tostring) + "s", "✅ Access: " + .access_token[:30] + "...", "✅ Refresh: " + .refresh_token[:30] + "..."' \
		|| echo "❌ Tokens não encontrados. Autorize via: make serve-cloudflare"

links:  ## 🔗 Expõe todos os links importantes: Cloudflare, ML, Instagram, site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 LINKS IMPORTANTES DO PROJETO"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🌐 SITE & TÚNEIS:"
	@echo "  🖥️  Site local  (Nginx) : https://localhost"
	@echo "  🔧 API local   (Flask) : https://localhost:5555"
	@ACTIVE_FILE=/tmp/cf_active_url.txt; \
	LOG_FILE=/tmp/cloudflare_tunnel.log; \
	CF_HOST=$$(grep '^CF_HOSTNAME=' .env 2>/dev/null | cut -d'=' -f2 | cut -d'#' -f1 | xargs); \
	if [ -f "$$ACTIVE_FILE" ]; then \
		CF_URL=$$(head -1 "$$ACTIVE_FILE"); \
		CF_TYPE=$$(sed -n '2p' "$$ACTIVE_FILE"); \
		if [ -n "$$CF_URL" ]; then \
			if [ "$$CF_TYPE" = "frontend" ]; then \
				echo "  ☁️  Cloudflare  (frontend): $$CF_URL"; \
			else \
				echo "  ☁️  Cloudflare  (backend) : $$CF_URL"; \
				echo "  ☁️  Cloudflare  API       : $$CF_URL/api"; \
			fi; \
			echo "  🔁 Callback ML            : $$CF_URL/auth/mercadolivre/callback"; \
		else \
			echo "  ☁️  Cloudflare: arquivo vazio — execute make serve-cloudflare"; \
		fi; \
	elif [ -f "$$LOG_FILE" ]; then \
		CF_URL=$$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' "$$LOG_FILE" | head -1); \
		if [ -n "$$CF_URL" ]; then \
			echo "  ☁️  Cloudflare  (log)     : $$CF_URL"; \
			echo "  🔁 Callback ML            : $$CF_URL/auth/mercadolivre/callback"; \
		fi; \
	elif [ -n "$$CF_HOST" ]; then \
		echo "  ☁️  Cloudflare  (fixo)    : https://$$CF_HOST"; \
		echo "  🔁 Callback ML            : https://$$CF_HOST/auth/mercadolivre/callback"; \
	else \
		echo "  ☁️  Cloudflare: nenhum túnel ativo — execute make serve-cloudflare"; \
	fi
	@echo ""
	@echo "💰 MERCADO LIVRE:"
	@grep '^MERCADO_LIVRE_AFFILIATE_ID=' .env | awk -F'=' '{print "  🆔 Affiliate ID: " $$2}' | cut -d'#' -f1; \
	grep '^ML_APP_ID=' .env | awk -F'=' '{print "  🔐 App ID: " $$2}' | cut -d'#' -f1; \
	echo "  🔗 API: https://api.mercadolibre.com"; \
	echo "  🧪 DevCenter: https://developers.mercadolivre.com.br/devcenter"; \
	echo "  💼 Afiliados: https://www.mercadolivre.com.br/afiliados"; \
	echo "  📊 Seller Center: https://vendas.mercadolivre.com.br"
	@echo ""
	@echo "📸 INSTAGRAM:"
	@echo "  🔐 API v19: https://graph.instagram.com/v19.0"
	@echo "  📚 Docs: https://developers.facebook.com/docs/instagram-api"
	@echo "  ⚙️  Graph Explorer: https://developers.facebook.com/tools/explorer"
	@echo ""
	@echo "🛠️  DASHBOARDS:"
	@echo "  📊 Redis: redis://localhost:6379"
	@echo "   MinIO Console: http://localhost:9001"
	@echo "     (user: minio / pass: minio123)"
	@echo ""
	@echo "📚 DOCUMENTAÇÃO:"
	@echo "  📖 README: ./README.md"
	@echo "  🏗️  Arquitetura: ./docs/DefineMe.md"
	@echo "  📸 Instagram: ./docs/instagram/INSTAGRAM_QUICKSTART.md"
	@echo "  🔌 Webhooks: ./docs/integrações/WEBHOOKS.md"
	@echo "  🔗 Integrações: ./docs/integrações/"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

test-api:  ## Testa chamada à API do Mercado Livre com token atual
	@TOKEN=$$(docker exec site cat /app/config/ml_tokens.json 2>/dev/null | jq -r '.access_token'); \
	if [ -z "$$TOKEN" ]; then echo "❌ Token não encontrado. Execute: make serve-cloudflare"; exit 1; fi; \
	curl -s -H "Authorization: Bearer $$TOKEN" https://api.mercadolibre.com/users/me \
		| jq '{id, nickname, email, reputacao: .seller_reputation.level_id}'


# ============================================================
# 📦  PREPARE — Scraping / API de produto
# ============================================================

_ensure-site:
	@if ! docker ps --format '{{.Names}}' | grep -q '^site$$'; then \
		echo "🛠️  Subindo container site..."; \
		$(COMPOSE) up -d site; \
	fi

_ensure-info-scrap: _ensure-site
	@if ! docker ps --format '{{.Names}}' | grep -q '^info-scrap$$'; then \
		echo "🛠️  Subindo info-scrap..."; \
		$(COMPOSE) up -d info-scrap; \
		sleep 4; \
	fi

prepare-ml:  ## ⭐ Prepara produto ML: API + OCR de preço promo  (URL=https://... | sem URL usa list_to_verify.json)
	@$(MAKE) -s _ensure-info-scrap
	@echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PREPARE ML — API Oficial + Screenshot OCR (preço promo)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ifneq ($(strip $(URL)),)
	@echo "🔗 $(URL)" && echo ""
	@docker exec -it site python3 scripts/prepare_ml_best.py "$(URL)"
else
	@FILE="services/site/list_to_prepare_and_stage/list_to_verify.json"; \
		if [ ! -f "$$FILE" ]; then \
			echo "❌ Arquivo não encontrado: $$FILE"; \
			exit 1; \
		fi; \
		TOTAL=$$(jq '.links | length' "$$FILE"); \
		echo "📦 Modo lote automático (sem URL)"; \
		echo "📄 Fonte: $$FILE"; \
		echo "📦 Total na fila: $$TOTAL"; \
		echo ""; \
		jq -r '.links[]' "$$FILE" | while read PURL; do \
			echo "🔗 $$PURL"; \
			docker exec site env FORCE_CATEGORY=geral python3 scripts/prepare_ml_best.py "$$PURL" || echo "❌ Erro neste produto"; \
			echo ""; \
		done; \
		echo "✅ Lote concluído"
endif
	@docker exec site find /app/staging -type d -exec chmod o+rwx {} \; && docker exec site find /app/staging -name "*.json" -exec chmod o+rw {} \;

prepare-shopee:  ## ⭐ Prepara produto Shopee: API + Playwright + OCR  (URL=https://...)
	@if [ -z "$(URL)" ]; then echo "❌ Uso: make prepare-shopee URL=https://s.shopee.com.br/ABC123"; exit 1; fi
	@$(MAKE) -s _ensure-info-scrap
	@echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PREPARE SHOPEE — API + Playwright + OCR"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 $(URL)" && echo ""
	@SCREENSHOT_HOST=$$(DISPLAY=:1 python3 services/site/scripts/take_screenshot_host.py "$(URL)" 2>/dev/tty); \
	if [ -n "$$SCREENSHOT_HOST" ] && [ -f "$$SCREENSHOT_HOST" ]; then \
		docker cp "$$SCREENSHOT_HOST" site:/tmp/shopee_screenshot_host.png; \
		rm -f "$$SCREENSHOT_HOST"; \
		docker exec -it site python3 scripts/shopee_prepare_best.py "$(URL)" --screenshot /tmp/shopee_screenshot_host.png; \
	else \
		docker exec -it site python3 scripts/shopee_prepare_best.py "$(URL)"; \
	fi
	@docker exec site find /app/staging -type d -exec chmod o+rwx {} \; && docker exec site find /app/staging -name "*.json" -exec chmod o+rw {} \;

prepare-amazon:  ## ⭐ Prepara produto Amazon: Playwright + OCR  (URL=https://...)
	@if [ -z "$(URL)" ]; then echo "❌ Uso: make prepare-amazon URL=https://amzn.to/ABC123"; exit 1; fi
	@$(MAKE) -s _ensure-info-scrap
	@echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PREPARE AMAZON — Scraping + OCR"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 $(URL)" && echo ""
	@docker exec -it site python3 scripts/amazon_prepare_best.py "$(URL)"
	@docker exec site find /app/staging -type d -exec chmod o+rwx {} \; && docker exec site find /app/staging -name "*.json" -exec chmod o+rw {} \;

prepare-all:  ## Prepara lote de produtos (list_to_prepare.json)
	@$(MAKE) -s _ensure-site
	@TOTAL=$$(cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq '.links | length'); \
	echo "📦 Total na fila: $$TOTAL"; \
	read -p "⚠️  Continuar? (s/N): " C; [ "$$C" = "s" ] || [ "$$C" = "S" ] || exit 0; \
	cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq -r '.links[].url' | \
	while read PURL; do \
		echo "" && echo "🔗 $$PURL"; \
		read -p "🏷️  Categoria (geral/E/CD/ME/PET) [geral]: " CAT; CAT=$${CAT:-geral}; \
		docker exec site python3 scripts/api_prepare_ml.py "$$PURL" "$$CAT" || echo "❌ Erro neste produto"; \
		read -p "▶  Enter para próximo..."; \
	done; \
	echo "✅ Lote concluído. Próximo: make organize-tags → make stage"

organize-tags:  ## 🏷️  ⭐ Reorganiza tags dos produtos por TÍTULO (auto-cadastro + pergunta baixa confiança)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🏷️  ORGANIZADOR DE TAGS — Modo Inteligente"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Auto-cadastro: confiança >= 50%"
	@echo "❓ Pergunta ao usuário: confiança < 50%"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/organize_tags.py

organize-tags-auto:  ## 🔍 Reorganiza tags — auto-cadastro SILENCIOSO (não pergunta)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 ORGANIZADOR DE TAGS — Modo Automático Silencioso"
	@echo "  Auto-cadastra todos os produtos com confiança >= 50% (sem perguntar)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/organize_tags.py --auto


# ============================================================
# 📤  STAGE — Publica produto no site + banco de dados
# ============================================================

stage:  ## ⭐ Publica produtos preparados no site (DB + MinIO)
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/stage_products.py
	@./scripts/staging_dedup.sh

restage:  ## Re-publica TODOS os JSONs do staging no banco (ignora .processed, útil após fix de código)
	@$(MAKE) -s _ensure-site
	@echo "⚠️  Reprocessando todo o staging (modo force)..."
	@docker exec -it site python3 scripts/stage_products.py --force

api-update:  ## Atualiza preço/disponibilidade de produto ML  (URL=https://...)
	@if [ -z "$(URL)" ]; then echo "❌ Uso: make api-update URL=https://..."; exit 1; fi
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/api_update_ml.py "$(URL)"

shopee-update:  ## Atualiza preço/disponibilidade de produto Shopee  (URL=https://...)
	@if [ -z "$(URL)" ]; then echo "❌ Uso: make shopee-update URL=https://..."; exit 1; fi
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/shopee_update_prices.py "$(URL)"

check-stage:  ## Verifica imagens no staging antes de publicar
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/check_stage_images.py

verify-prices:  ## 🔍 Verifica preços zerados via OCR → Tesseract → info-scrap (remove se falhar)
	@$(MAKE) -s _ensure-info-scrap
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 VERIFY PRICES — OCR → Tesseract → info-scrap scraping"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then \
		echo "   Modo: DRY-RUN (nenhuma alteração no banco)"; echo ""; \
		if [ -n "$(ID)" ]; then \
			docker exec -it site python3 scripts/verify_prices.py --dry-run --id "$(ID)"; \
		elif [ "$(ALL)" = "1" ]; then \
			docker exec -it site python3 scripts/verify_prices.py --dry-run --all; \
		else \
			docker exec -it site python3 scripts/verify_prices.py --dry-run; \
		fi; \
	else \
		if [ -n "$(ID)" ]; then \
			docker exec -it site python3 scripts/verify_prices.py --id "$(ID)"; \
		elif [ "$(ALL)" = "1" ]; then \
			docker exec -it site python3 scripts/verify_prices.py --all; \
		else \
			docker exec -it site python3 scripts/verify_prices.py; \
		fi; \
	fi

verify-product-cheaper:  ## ⭐ Verifica se o link ML é o menor preço do catálogo  (FILE= ou URL=)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 VERIFICADOR DE PREÇO — Mercado Livre"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@if [ -n "$(URL)" ]; then \
		docker exec -it site python3 scripts/price_validator/main.py --url "$(URL)"; \
	elif [ -n "$(FILE)" ]; then \
		docker exec -it site python3 scripts/price_validator/main.py --file "$(FILE)"; \
	else \
		docker exec -it site python3 scripts/price_validator/main.py; \
	fi

update-ml-prices:  ## ⭐ ML: busca o vendedor mais barato p/ cada produto (DRY=1 simula, ID=MLB... filtra)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔄 UPDATE ML PRICES — varredura de vendedor mais barato"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then \
		echo "   Modo: DRY-RUN (sem alterações no banco)"; echo ""; \
		docker exec -it site python3 scripts/update_ml_prices.py --dry-run; \
	elif [ -n "$(ID)" ]; then \
		echo "   Modo: produto único ($(ID))"; echo ""; \
		docker exec -it site python3 scripts/update_ml_prices.py --id "$(ID)"; \
	else \
		echo "   Modo: TODOS os produtos ML ativos"; echo ""; \
		docker exec -it site python3 scripts/update_ml_prices.py; \
	fi

fix-bad-links:  ## 🔗 Corrige links de produtos ML que apontam para item_id errado (DRY=1 só reporta)
	@$(MAKE) -s _ensure-site
	@docker cp services/site/scripts/fix_bad_links.py site:/app/scripts/fix_bad_links.py
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 FIX BAD LINKS — corrige links de produtos ML"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ "$(DRY)" = "1" ]; then \
		echo "   Modo: DRY-RUN (sem alterar banco)"; echo ""; \
		docker exec -it site python3 scripts/fix_bad_links.py --dry; \
	else \
		echo "   Modo: CORRIGINDO no banco"; echo ""; \
		docker exec -it site python3 scripts/fix_bad_links.py; \
	fi

  ## ⭐ ML: atualiza preço+promo+info via API+DOM texto (sem screenshot/OCR) (DRY=1, ID=MLB..., NO_BROWSER=1)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔄 UPDATE PRICES ML RIGHT — API + DOM texto + regex"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@_ARGS=""; \
	if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then _ARGS="$$_ARGS --dry-run"; fi; \
	if [ -n "$(ID)" ]; then _ARGS="$$_ARGS --id $(ID)"; fi; \
	if [ "$(NO_BROWSER)" = "1" ]; then _ARGS="$$_ARGS --no-browser"; fi; \
	echo "   Args: $$_ARGS"; echo ""; \
	docker exec -it site python3 scripts/update_ml_prices_right.py $$_ARGS

price-oracle:  ## 🤖 Price Oracle: coleta fontes → LLM decide → publica no banco  FILE=links.json ou LINK=https://meli.la/xxx ou ML_ID=MLB123 [DRY=1] [NO_PUBLISH=1]
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🤖 PRICE ORACLE — coleta fontes → hsmart LLM → publica no banco"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -z "$(FILE)" ] && [ -z "$(LINK)" ] && [ -z "$(ML_ID)" ]; then \
		_ID_ARG="--file /app/list_to_prepare_and_stage/links_to_publish.json"; \
	elif [ -n "$(FILE)" ]; then \
		_ID_ARG="--file $(FILE)"; \
	elif [ -n "$(LINK)" ]; then \
		_ID_ARG="--link $(LINK)"; \
	else \
		_ID_ARG="--ml-id $(ML_ID)"; \
	fi; \
	_ARGS="$$_ID_ARG"; \
	if [ "$(DRY)" = "1" ]; then _ARGS="$$_ARGS --dry-run"; fi; \
	if [ "$(NO_PUBLISH)" = "1" ]; then _ARGS="$$_ARGS --no-publish"; fi; \
	echo "   Args: $$_ARGS"; echo ""; \
	docker exec -it site python3 agents/price_oracle_agent.py $$_ARGS

init-qdrant:  ## 🗄️  Cria as 4 coleções Qdrant do projeto (idempotente)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🗄️  INIT QDRANT — Cria coleções: agent_rules, price_history, product_catalog, site_knowledge"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker exec -it site python3 scripts/init_qdrant_collections.py

reprice-all:  ## 🔄 Revisa todos os produtos do banco: atualiza preços + remove itens com valor 0/inválido  [DRY=1] [ZERO_ONLY=1] [BATCH=N]
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔄 REPRICE ALL — atualiza preços + limpa zeros/inválidos"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@_ARGS=""; \
	if [ "$(DRY)" = "1" ]; then _ARGS="$$_ARGS --dry-run"; fi; \
	if [ "$(ZERO_ONLY)" = "1" ]; then _ARGS="$$_ARGS --fix-zero-only"; fi; \
	if [ -n "$(BATCH)" ]; then _ARGS="$$_ARGS --batch-size $(BATCH)"; fi; \
	echo "   Args: $$_ARGS"; echo ""; \
	docker exec -it site python3 agents/reprice_all.py $$_ARGS

prepare-and-publish:  ## ⭐ Pipeline completo: lê links → prepare → organize → stage → update preços  (DRY=1, FILE=caminho, NO_PRICE=1, NO_STAGE=1)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PREPARE & PUBLISH — Pipeline Completo"
	@echo "   Detecta ML/Shopee/Amazon pela URL"
	@echo "   Categoria detectada automaticamente por regex no título"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@_ARGS=""; \
	if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then _ARGS="$$_ARGS --dry-run"; fi; \
	if [ -n "$(FILE)" ]; then _ARGS="$$_ARGS --file $(FILE)"; fi; \
	if [ "$(NO_PRICE)" = "1" ]; then _ARGS="$$_ARGS --no-price-update"; fi; \
	if [ "$(NO_STAGE)" = "1" ]; then _ARGS="$$_ARGS --no-stage"; fi; \
	echo "   Args: $$_ARGS"; echo ""; \
	docker exec -it site python3 scripts/pipeline_publish.py $$_ARGS

publish:  ## ⭐ Publica links_to_publish.json → prepare → LLM tags → stage → archive  (DRY=1, NO_PRICE=1, NO_TAG=1)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PUBLISH — lê links_to_publish.json, insere no site e classifica tags"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@_ARGS=""; \
	if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then _ARGS="$$_ARGS --dry-run"; fi; \
	if [ "$(NO_PRICE)" = "1" ]; then _ARGS="$$_ARGS --no-price-update"; fi; \
	if [ "$(NO_TAG)" = "1" ]; then _ARGS="$$_ARGS --no-tag-classify"; fi; \
	echo "   Args: $$_ARGS"; echo ""; \
	docker exec -it site python3 scripts/pipeline_publish.py $$_ARGS

populate-mf:  ## 🛒 Popula o site via ML: busca mais vendidos por tag/subtag → cheapest → prepare → stage  [TAG=PET] [SUBTAG=gatos] [LIMIT=5] [DRY=1]
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🛒 POPULATE-MF — Mercado Livre: mais vendidos → cheapest seller → site"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@_ARGS=""; \
	if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then _ARGS="$$_ARGS --dry-run"; fi; \
	if [ -n "$(TAG)" ] && [ "$(TAG)" != "ALL" ]; then _ARGS="$$_ARGS --tag $(TAG)"; fi; \
	if [ -n "$(SUBTAG)" ]; then _ARGS="$$_ARGS --subtag $(SUBTAG)"; fi; \
	if [ -n "$(LIMIT)" ]; then _ARGS="$$_ARGS --limit $(LIMIT)"; fi; \
	echo "   Args: $$_ARGS"; echo ""; \
	docker exec -it site python3 agents/ml_populator_agent.py $$_ARGS

tag-classify-db:  ## 🏷️  LLM classifica tag+subtag dos produtos no banco (sem tag ou tag=geral)  [DRY=1] [ID=uuid]
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 agents/tag_classifier_agent.py --db \
		$(if $(filter 1,$(DRY)),--dry-run,) \
		$(if $(ID),--product-id $(ID),)

reprepare-ml:  ## ⭐ ML: refaz prepare (API+OCR+imgs) de todos os produtos, mantém tags, faz stage
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔄 REPREPARE ML — Re-preparação completa (preço + imagens)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then \
		echo "   Modo: DRY-RUN (só lista)"; echo ""; \
		docker exec -it site python3 scripts/reprepare_all_ml.py --dry-run; \
	elif [ -n "$(ID)" ]; then \
		echo "   Modo: produto único ($(ID))"; echo ""; \
		docker exec -it site python3 scripts/reprepare_all_ml.py --id "$(ID)"; \
	else \
		echo "   Modo: TODOS os produtos ML ativos"; echo ""; \
		docker exec -it site python3 scripts/reprepare_all_ml.py; \
	fi

reprepare-associate-ml:  ## ⭐ ML: reprepare COM link de afiliado (preço mais preciso via OCR)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 REPREPARE ASSOCIATE ML — Refaz prepare COM affiliate_link"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@ML_SELLER_ID=$$(grep "^ML_SELLER_ID=" .env | cut -d'=' -f2 | tr -d '[:space:]'); \
	if [ -z "$$ML_SELLER_ID" ]; then \
		echo "❌ ML_SELLER_ID não preenchido no .env"; \
		exit 1; \
	fi; \
	if [ "$(DRY)" = "1" ] || [ "$(DRY_RUN)" = "1" ]; then \
		echo "   Modo: DRY-RUN (só lista)"; echo ""; \
		docker exec -it site python3 scripts/reprepare_associate_ml.py --dry-run; \
	elif [ -n "$(ID)" ]; then \
		echo "   Modo: produto único ($(ID))"; echo ""; \
		docker exec -it site python3 scripts/reprepare_associate_ml.py --id "$(ID)"; \
	else \
		echo "   Modo: TODOS os produtos ML ativos"; echo ""; \
		docker exec -it site python3 scripts/reprepare_associate_ml.py; \
	fi


# ============================================================
# 📸  INSTAGRAM
# ============================================================

instagram-post:  ## ⭐ Posta produto no Instagram (feed + story automáticos)
	@$(MAKE) -s _ensure-site
	@echo "📸 Postando no Instagram..."
	@curl -sX POST "http://localhost:5555/instagram/post/auto?simulate=false" \
		-H "Content-Type: application/json" | jq .

instagram-test:  ## Simula postagem Instagram sem publicar de verdade
	@$(MAKE) -s _ensure-site
	@echo "🎭 Simulando postagem Instagram..."
	@curl -sX POST "http://localhost:5555/instagram/post/auto?simulate=true" \
		-H "Content-Type: application/json" | jq .

instagram-status:  ## Status do sistema Instagram (tokens, permissões)
	@curl -s "http://localhost:5555/instagram/status" | jq .

instagram-history:  ## Histórico de posts no Instagram (últimos 10)
	@curl -s "http://localhost:5555/instagram/history?limit=10" | jq .

prepare-post-image:  ## ⭐ Gera imagem 1080x1080 para post (FILE=caminho.json ou --all)
	@$(MAKE) -s _ensure-site
	@echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎨 PREPARE POST IMAGE — gerador de imagens para Instagram"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -n "$(FILE)" ]; then \
		echo "📄 Arquivo: $(FILE)" && echo ""; \
		docker exec -it site python3 scripts/prepare_publish_images.py \
			--file "$(FILE)" \
			--staging-dir staging \
			--output publish_ready \
			--uploads-dir uploads || true; \
	else \
		echo "📦 Modo: todos os produtos do staging" && echo ""; \
		docker exec -it site python3 scripts/prepare_publish_images.py \
			--all \
			--staging-dir staging \
			--output publish_ready \
			--uploads-dir uploads || true; \
	fi
	@echo ""
	@echo "📁 Imagens disponíveis em: services/site/publish_ready/"
	@docker exec site find /app/publish_ready -name "*.jpg" 2>/dev/null | sort | \
		while read f; do echo "  🖼️  $$(basename $$f)"; done

stage-and-post:  ## Publica no site E posta no Instagram em sequência
	@$(MAKE) stage
	@sleep 2
	@$(MAKE) instagram-post


# ============================================================
# 🗄️  BANCO DE DADOS
# ============================================================

migrate-tags:  ## Migração: adiciona coluna tags no banco
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/migrate_add_tags.py

migrate-webhook:  ## Migração: adiciona campos de webhook no banco
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/migrate_add_webhook_fields.py

migrate-subcategory:  ## Migração: adiciona coluna subcategory nos produtos
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/migrate_add_subcategory.py


# ============================================================
# 🏭  PRODUÇÃO
# ============================================================

prd-up:  ## Sobe ambiente de produção
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd up -d

prd-down:  ## Para ambiente de produção
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd down -v

prd-logs:  ## Logs do site em produção
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd logs -f site

build-prd-site:  ## Build da imagem de produção do site
	docker build -t $(IMAGE_NAME) ./services/site

push-ghcr:  ## Build + push da imagem para GitHub Container Registry
	@echo $(GHCR_TOKEN) | docker login ghcr.io -u $(GHCR_USER) --password-stdin
	$(MAKE) build-prd-site
	docker push $(IMAGE_NAME)

prd-up-ghcr:  ## Sobe produção usando imagem do GHCR
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd down || true
	docker pull $(IMAGE_NAME)
	docker-compose -f docker-compose.yaml -f docker-compose.prd.yaml --env-file .env.prd up -d


# ============================================================
# 🧪  TESTES
# ============================================================

test:  ## Roda todos os testes
	PYTHONPATH=. pytest tests/ --disable-warnings -v

test-unit:  ## Testes unitários
	PYTHONPATH=. pytest tests/unit --disable-warnings -v

test-integration:  ## Testes de integração
	PYTHONPATH=. pytest tests/integration --disable-warnings -v

test-info-scrap:  ## Testa serviço OCR / extração
	@$(MAKE) -s _ensure-info-scrap
	@docker exec -it site python3 scripts/test_info_scrap.py /app/image_example.png

test-affiliate:  ## Testes unitários do gerador de links de afiliado ML
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧪 AFFILIATE LINK GENERATOR — testes unitários"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker exec site python3 -m pytest tests/unit/test_affiliate_link_generator.py -v --tb=short

test-price-validator:  ## Testa todo o módulo price_validator (affiliate + validator + parser)
	@$(MAKE) -s _ensure-site
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧪 PRICE VALIDATOR — suite completa"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker exec site python3 -m pytest tests/unit/ -v --tb=short


# ============================================================
# 🧹  MANUTENÇÃO
# ============================================================

staging-fix-perms:  ## Corrige permissões do staging para que o usuário possa deletar os JSONs
	@if docker ps --format '{{.Names}}' | grep -q '^site$$'; then \
		docker exec site find /app/staging -type d -exec chmod o+rwx {} \;; \
		docker exec site find /app/staging -name "*.json" -exec chmod o+rw {} \;; \
		echo "✅ Permissões corrigidas via Docker"; \
	else \
		sudo chown -R $$USER:$$USER services/site/staging/ && echo "✅ Owner corrigido via sudo"; \
	fi

staging-dedup:  ## Remove JSONs duplicados do staging, mantendo apenas o mais novo por produto
	@./scripts/staging_dedup.sh

clear-minio:  ## Remove TODAS as imagens do MinIO (com confirmação)
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/clear_minio_images.py

clear-minio-force:  ## Remove TODAS as imagens do MinIO SEM confirmação
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/clear_minio_images.py --force

prune:clean-images  ## Remove containers, volumes e imagens não utilizadas
	docker system prune -f --volumes

clean-images:  ## Remove TODAS as imagens Docker (cuidado!)
	@if [ -n "$$(docker images -q)" ]; then \
		docker stop $$(docker ps -q) 2>/dev/null || true; \
		docker rmi -f $$(docker images -q); \
	else \
		echo "✅ Nenhuma imagem para remover"; \
	fi


# ============================================================
# ❓  HELP
# ============================================================

help:  ## Mostra este menu
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  V_M — Comandos disponíveis   (⭐ = fluxo principal)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🧪 DEV"
	@awk 'BEGIN{FS=":.*?## "}/^(up|down|down-purge|restart-site|rebuild-site|logs|shell|psql):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "� FRONTEND (React + Vite)"
	@awk 'BEGIN{FS=":.*?## "}/^(frontend-install|frontend-dev|frontend-build|frontend-build-prod|frontend-clean):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "�🌐 EXPOSE (túneis HTTPS)"
	@awk 'BEGIN{FS=":.*?## "}/^(serve-cloudflare|serve-frontend-public|stop-cloudflare|stop-frontend-public|serve-cloudflare-fixed|serve-ngrok|stop-ngrok|install-cloudflared|setup-cloudflare-fixed):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🔑 OAUTH"
	@awk 'BEGIN{FS=":.*?## "}/^(check-tokens|test-api):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "📦 PREPARE (scraping de produto)"
	@awk 'BEGIN{FS=":.*?## "}/^(prepare-ml|prepare-shopee|prepare-amazon|prepare-all):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "📤 STAGE / ATUALIZAÇÃO"
	@awk 'BEGIN{FS=":.*?## "}/^(stage|restage|api-update|shopee-update|check-stage|verify-prices|verify-product-cheaper|update-ml-prices|fix-bad-links|reprepare-ml|reprepare-associate-ml|organize-tags|organize-tags-auto|publish|populate-mf):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "📸 INSTAGRAM"
	@awk 'BEGIN{FS=":.*?## "}/^(prepare-post-image|instagram-post|instagram-test|instagram-status|instagram-history|stage-and-post):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🗄️  BANCO DE DADOS"
	@awk 'BEGIN{FS=":.*?## "}/^(migrate-tags|migrate-webhook|migrate-subcategory):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🏭 PRODUÇÃO"
	@awk 'BEGIN{FS=":.*?## "}/^(prd-up|prd-down|prd-logs|build-prd-site|push-ghcr|prd-up-ghcr):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🧪 TESTES"
	@awk 'BEGIN{FS=":.*?## "}/^(test|test-unit|test-integration|test-info-scrap|test-affiliate|test-price-validator):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🧹 MANUTENÇÃO"
	@awk 'BEGIN{FS=":.*?## "}/^(staging-dedup|staging-fix-perms|clear-minio|clear-minio-force|prune|clean-images):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
