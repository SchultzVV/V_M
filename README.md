# DEF Site

Plataforma de afiliados com scraping automático, pipeline de produtos e publicação no site. Coleta produtos de Mercado Livre, Shopee e Amazon com preços via API + OCR, publica no PostgreSQL/MinIO e exibe via React + Nginx.

Para todos os comandos: `make help`

---

## 🗺️ Fluxo principal (uso diário)

```
make serve-cloudflare-fixed    ← sobe tudo + túnel HTTPS (URL fixa)
        ↓
make check-tokens              ← confirma que o token ML está válido
        ↓
make prepare-ml URL=...        ← coleta produto do Mercado Livre (API + OCR)
make prepare-shopee URL=...    ← coleta produto da Shopee
make prepare-amazon URL=...    ← coleta produto da Amazon
        ↓
make verify-product-cheaper    ← confere se é o mais barato no ML
        ↓
make stage                     ← publica no site (PostgreSQL + MinIO)
        ↓
make instagram-post            ← posta no Instagram (opcional)
```

> **Primeira vez ou token expirado?** Veja [Setup OAuth](#️-setup-e-autorização-oauth) abaixo.

---

## ⚙️ Setup inicial (primeira vez)

### 1 — Instalar cloudflared

```bash
make install-cloudflared
```

### 2 — Criar túnel permanente

```bash
make setup-cloudflare-fixed
```

Abre o browser para login na Cloudflare, cria o túnel `vm-site` e gera `~/.cloudflared/config.yml`.

### 3 — Pegar URL permanente

```bash
cloudflared tunnel info vm-site
```

Copie a URL `https://XXXX.cfargotunnel.com`.

### 4 — Configurar Redirect URI no DevCenter ML

1. [developers.mercadolivre.com.br/devcenter](https://developers.mercadolivre.com.br/devcenter) → seu app → **Configuração**
2. **URL de redirecionamento OAuth**:
   ```
   https://XXXX.cfargotunnel.com/auth/mercadolivre/callback
   ```

### 5 — Preencher `.env`

```dotenv
ML_APP_ID=SEU_CLIENT_ID
ML_CLIENT_SECRET=SEU_CLIENT_SECRET
MERCADO_LIVRE_AFFILIATE_ID=SEU_ID_AFILIADO
CF_HOSTNAME=XXXX.cfargotunnel.com
```

### 6 — Subir e autorizar

```bash
make rebuild-site
make serve-cloudflare-fixed
# Abra o link de autorização exibido no terminal
make check-tokens   # confirma access_token + refresh_token
```

---

## 🌐 Subir servidor

```bash
make serve-cloudflare-fixed    # URL fixa — token renovado automaticamente
make serve-cloudflare          # URL temporária — muda a cada reinício
make serve-frontend-public     # React + Nginx + reutiliza túnel ativo
```

Para parar:
```bash
make stop-cloudflare
make stop-frontend-public
```

---

## 📦 Coletar produto

```bash
make prepare-ml URL="https://produto.mercadolivre.com.br/MLB-..."
make prepare-ml                   # lote via list_to_verify.json
make prepare-shopee URL="https://s.shopee.com.br/..."
make prepare-amazon URL="https://amzn.to/..."
```

O produto é salvo em `services/site/staging/` como JSON com título, preço, imagens, categoria, schema.org.

---

## 💰 Verificar se é o mais barato

```bash
make verify-product-cheaper URL="https://produto.mercadolivre.com.br/MLB-..."
make verify-product-cheaper       # lote via list_to_verify.json
```

Se houver opção mais barata no catálogo ML, retorna o link do concorrente com o parâmetro de afiliado embutido.

---

## 🚀 Publicar no site

```bash
make stage
```

1. Lê JSONs do `staging/` ainda não processados
2. Upload de imagens para MinIO
3. Salva produto no PostgreSQL via Flask
4. Marca JSONs como `.processed`

---

## 🔄 Atualizar produtos existentes

```bash
make update-ml-prices             # busca vendedor mais barato para todos os produtos ML
make update-ml-prices DRY=1       # simula sem salvar
make reprepare-ml                 # refaz prepare completo (API+OCR+imagens) de todos os produtos ML
make reprepare-associate-ml       # reprepare com link de afiliado (OCR mais preciso)
make restage                      # re-publica staging completo no banco
make organize-tags                # reclassifica tags dos produtos (interativo)
make organize-tags-auto           # reclassifica tags silenciosamente
```

---

## 📸 Postar no Instagram (opcional)

```bash
make instagram-post
make prepare-post-image FILE=caminho.json   # gera imagem 1080×1080
make stage-and-post                         # publica no site E posta em sequência
```

---

## 🛠️ Comandos de manutenção

```bash
make down                    # para containers (preserva banco de dados)
make down-purge              # ⚠️  DESTRÓI volumes permanentemente (banco + MinIO)
make rebuild-site            # reconstrói imagem do Flask e reinicia
make staging-fix-perms       # corrige permissões do staging
make staging-dedup           # remove JSONs duplicados do staging
make clear-minio             # remove todas as imagens do MinIO (com confirmação)
make prune                   # limpa containers/imagens/volumes não usados
make logs                    # logs de todos os containers
make psql                    # terminal psql no Postgres
make shell                   # shell bash no container site
```

---

## 🧪 Testes

```bash
make test-affiliate          # testes unitários do gerador de links de afiliado
make test-price-validator    # suite completa do price_validator
make test-unit               # todos os testes unitários
```

---

## 🏭 Produção

```bash
make prd-up-ghcr             # sobe em produção com imagem do GitHub Container Registry
make push-ghcr               # build + push da imagem para GHCR
make prd-down                # para produção
```

---

## 🗄️ Pipeline de staging

```
URL do produto
    ↓
prepare_*.py  (API + OCR + Playwright)
    ↓
staging/{categoria}/{sub}/{slug}_{ts}.json
    ↓
staging_dedup.sh  (remove versões antigas)
    ↓
stage_products.py
    ├── Upload imagens → MinIO
    └── POST /add_product → Flask → PostgreSQL → Redis cache
                                                    ↓
                                            /api/products → Frontend React
```

| Serviço | Armazena |
|---|---|
| **Staging (filesystem)** | JSONs temporários dos produtos |
| **MinIO** | Imagens (`bucket: produtos`, path `/imagens/{slug}/`) |
| **PostgreSQL** | Registro completo (tabela `products`) |
| **Redis** | Cache de listagens da API, pub/sub de eventos |

---

## 📚 Documentação

- [Conceito e Arquitetura](docs/conceito.md)
- [Agentes — Visão Geral](docs/DefineMe-agents.md)
- [Scripts de Automação](docs/DefineMe-scripts.md)
- [OAuth Mercado Livre](docs/integrações/OAUTH_MERCADOLIVRE.md)
- [Webhooks](docs/integrações/WEBHOOKS.md)
- [Instagram API](docs/instagram/INSTAGRAM_API_OFICIAL.md)
