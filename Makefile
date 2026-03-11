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
	@echo "✅ Site em https://localhost:5000"
	@echo "💡 Próximo: make serve-cloudflare  (HTTPS público + auto-OAuth)"

down:  ## Para e remove containers + volumes
	$(COMPOSE) down -v

restart-site:  ## Reinicia apenas o container site
	$(COMPOSE) restart site

rebuild-site:  ## Rebuild completo apenas do site
	$(COMPOSE) stop site
	$(COMPOSE) rm -f site
	$(COMPOSE) build site
	$(COMPOSE) up -d site

logs:  ## Logs em tempo real do site
	$(COMPOSE) logs -f site

shell:  ## Shell bash dentro do container site
	@docker exec -it site /bin/bash

psql:  ## Terminal psql no container postgres
	docker exec -it postgres-dev psql -U user -d produtos_db


# ============================================================
# 🌐  EXPOSE — Túneis HTTPS públicos
# ============================================================

serve-cloudflare:  ## ⭐ Túnel Cloudflare: sobe tudo, captura URL, configura OAuth ML, exibe link
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 CLOUDFLARE TUNNEL  +  AUTO-CONFIG OAUTH MERCADO LIVRE"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@CLOUDFLARED_BIN=$$(command -v cloudflared 2>/dev/null || echo /usr/local/bin/cloudflared); \
	if [ ! -x "$$CLOUDFLARED_BIN" ]; then \
		echo "❌ cloudflared não instalado. Execute: make install-cloudflared"; \
		exit 1; \
	fi; \
	echo "🔧 Subindo containers..."; \
	$(COMPOSE) up -d; \
	sleep 2; \
	echo "✅ Site em https://localhost:5000"; \
	echo ""; \
	echo "🌐 Iniciando túnel em background..."; \
	pkill cloudflared 2>/dev/null || true; \
	sleep 1; \
	LOG=/tmp/cloudflare_tunnel.log; \
	rm -f $$LOG; \
	$$CLOUDFLARED_BIN tunnel \
		--url https://localhost:5000 \
		--no-tls-verify \
		--proxy-connect-timeout 60s \
		--proxy-keepalive-timeout 5m \
		--proxy-keepalive-connections 200 \
		--proxy-tcp-keepalive 60s \
		2>&1 | tee $$LOG & \
	echo "⏳ Aguardando URL..."; \
	CF_URL=""; \
	for i in $$(seq 1 20); do \
		CF_URL=$$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' $$LOG 2>/dev/null | head -1); \
		[ -n "$$CF_URL" ] && break; \
		sleep 2; \
	done; \
	if [ -z "$$CF_URL" ]; then \
		echo "❌ URL não capturada. Veja: cat /tmp/cloudflare_tunnel.log"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✅ TÚNEL ATIVO: $$CF_URL"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	NEW_REDIRECT="$$CF_URL/auth/mercadolivre/callback"; \
	echo "📝 Atualizando ML_REDIRECT_URI no .env..."; \
	sed -i "s|^ML_REDIRECT_URI=.*|ML_REDIRECT_URI=$$NEW_REDIRECT|" .env; \
	echo "🔄 Reiniciando site com nova URI..."; \
	$(COMPOSE) stop site > /dev/null 2>&1; \
	$(COMPOSE) rm -f site > /dev/null 2>&1; \
	$(COMPOSE) up -d site > /dev/null 2>&1; \
	sleep 3; \
	echo "✅ Container reiniciado"; \
	echo ""; \
	APP_ID=$$(grep "^ML_APP_ID=" .env | cut -d'=' -f2); \
	AUTH_URL="https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=$$APP_ID&redirect_uri=$$NEW_REDIRECT"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🔑 AUTORIZAÇÂO OAUTH:"; \
	echo ""; \
	echo "1️⃣  Cadastre no painel ML (se ainda não fez):"; \
	echo "   https://developers.mercadolivre.com.br/devcenter"; \
	echo "   → Redirect URI: $$NEW_REDIRECT"; \
	echo ""; \
	echo "2️⃣  Abra no navegador para autorizar:"; \
	echo ""; \
	echo "   $$AUTH_URL"; \
	echo ""; \
	echo "3️⃣  Após autorizar:  make check-tokens"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "💡 Para parar o túnel: make stop-cloudflare"; \
	echo ""

stop-cloudflare:  ## Para o túnel Cloudflare em background
	@pkill cloudflared 2>/dev/null && echo "✅ Túnel encerrado" || echo "⚠️  Túnel não estava rodando"

serve-ngrok:  ## Túnel ngrok (plano free, URL aleatória)
	@pkill ngrok 2>/dev/null || true
	$(COMPOSE) up -d
	@ngrok http --request-header-add="ngrok-skip-browser-warning:true" https://localhost:5000 > /dev/null &
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
	echo "🔧 Criando túnel permanente 'vm-site'..."; \
	$$CLOUDFLARED_BIN tunnel create vm-site 2>/dev/null || echo "Túnel já existe"; \
	TUNNEL_ID=$$($$CLOUDFLARED_BIN tunnel list | grep vm-site | awk '{print $$1}'); \
	echo "📝 Gerando ~/.cloudflared/config.yml..."; \
	printf "tunnel: %s\ncredentials-file: /home/%s/.cloudflared/%s.json\n\ningress:\n  - service: https://localhost:5000\n    originRequest:\n      noTLSVerify: true\n      connectTimeout: 30s\n      tlsTimeout: 30s\n      tcpKeepAlive: 30s\n      keepAliveConnections: 10\n      keepAliveTimeout: 90s\n" "$$TUNNEL_ID" "$$USER" "$$TUNNEL_ID" > ~/.cloudflared/config.yml; \
	echo "✅ Configurado! Use: make serve-cloudflare-fixed"

serve-cloudflare-fixed:  ## Túnel Cloudflare com URL PERMANENTE (requer setup-cloudflare-fixed)
	@CLOUDFLARED_BIN=$$(command -v cloudflared 2>/dev/null || echo /usr/local/bin/cloudflared); \
	if [ ! -x "$$CLOUDFLARED_BIN" ]; then echo "❌ Execute: make install-cloudflared"; exit 1; fi; \
	if [ ! -s ~/.cloudflared/config.yml ]; then echo "❌ Execute: make setup-cloudflare-fixed"; exit 1; fi; \
	echo "🔧 Subindo containers..."; \
	$(COMPOSE) up -d; \
	sleep 2; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🌐 Túnel PERMANENTE (URL sempre a mesma)"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	$$CLOUDFLARED_BIN tunnel run


# ============================================================
# 🔑  OAUTH — Mercado Livre
# ============================================================

check-tokens:  ## Verifica tokens OAuth salvos no container
	@docker exec site cat /app/config/ml_tokens.json 2>/dev/null \
		| jq -r '"✅ User ID: " + (.user_id|tostring), "✅ Expira em: " + (.expires_in|tostring) + "s", "✅ Access: " + .access_token[:30] + "...", "✅ Refresh: " + .refresh_token[:30] + "..."' \
		|| echo "❌ Tokens não encontrados. Autorize via: make serve-cloudflare"

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

prepare-ml:  ## ⭐ Prepara produto ML: API oficial + OCR preço promo  (URL=https://...)
	@if [ -z "$(URL)" ]; then echo "❌ Uso: make prepare-ml URL=https://mercadolivre.com/sec/ABC123"; exit 1; fi
	@$(MAKE) -s _ensure-info-scrap
	@echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 PREPARE ML — API Oficial + Screenshot OCR (preço promo)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 $(URL)" && echo ""
	@docker exec -it site python3 scripts/prepare_ml_best.py "$(URL)"
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
	echo "✅ Lote concluído. Próximo: make stage"


# ============================================================
# 📤  STAGE — Publica produto no site + banco de dados
# ============================================================

stage:  ## ⭐ Publica produtos preparados no site (DB + MinIO)
	@$(MAKE) -s _ensure-site
	@docker exec -it site python3 scripts/stage_products.py
	@./scripts/staging_dedup.sh

restage:  ## Re-publica TODOS os produtos do staging (ignora .processed — útil após correção de código)
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

verify-product-cheaper:  ## ⭐ Verifica se os links são o menor preço do catálogo ML  (FILE= ou URL=)
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


# ============================================================
# 📸  INSTAGRAM
# ============================================================

instagram-post:  ## ⭐ Posta produto no Instagram (feed + story automáticos)
	@$(MAKE) -s _ensure-site
	@echo "📸 Postando no Instagram..."
	@curl -sX POST "http://localhost:5000/instagram/post/auto?simulate=false" \
		-H "Content-Type: application/json" | jq .

instagram-test:  ## Simula postagem Instagram sem publicar de verdade
	@$(MAKE) -s _ensure-site
	@echo "🎭 Simulando postagem Instagram..."
	@curl -sX POST "http://localhost:5000/instagram/post/auto?simulate=true" \
		-H "Content-Type: application/json" | jq .

instagram-status:  ## Status do sistema Instagram (tokens, permissões)
	@curl -s "http://localhost:5000/instagram/status" | jq .

instagram-history:  ## Histórico de posts no Instagram (últimos 10)
	@curl -s "http://localhost:5000/instagram/history?limit=10" | jq .

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
	@awk 'BEGIN{FS=":.*?## "}/^(up|down|restart-site|rebuild-site|logs|shell|psql):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🌐 EXPOSE (túneis HTTPS)"
	@awk 'BEGIN{FS=":.*?## "}/^(serve-cloudflare|serve-cloudflare-fixed|stop-cloudflare|serve-ngrok|stop-ngrok|install-cloudflared|setup-cloudflare-fixed):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🔑 OAUTH"
	@awk 'BEGIN{FS=":.*?## "}/^(check-tokens|test-api):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "📦 PREPARE (scraping de produto)"
	@awk 'BEGIN{FS=":.*?## "}/^(prepare-ml|prepare-shopee|prepare-amazon|prepare-all):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "📤 STAGE / ATUALIZAÇÃO"
	@awk 'BEGIN{FS=":.*?## "}/^(stage|api-update|shopee-update|check-stage|verify-product-cheaper):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
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
	@awk 'BEGIN{FS=":.*?## "}/^(test|test-unit|test-integration|test-info-scrap):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "🧹 MANUTENÇÃO"
	@awk 'BEGIN{FS=":.*?## "}/^(staging-dedup|staging-fix-perms|clear-minio|clear-minio-force|prune|clean-images):.*##/{printf "  \033[36m%-26s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
