# DEF Site

## 🛠️ Organização / Manutenção

| Comando | Função |
|---------|--------|
| `make organize-tags` | Reclassifica produtos por categoria (interativo) |
| `make organize-tags-auto` | Reclassifica silenciosamente |
| `make staging-dedup` | Remove JSONs duplicados no staging |
| `make staging-fix-perms` | Corrige permissões de `/staging` |
| `make clear-minio` | Remove todas imagens do MinIO (com confirmação) |
| `make check-tokens` | Verifica se o token OAuth ML está válido |
| `make tunnel-info` | Mostra URL do túnel ativo |

---

Plataforma de afiliados e comparação de produtos com scraping automático, publicação de conteúdo e arquitetura de agentes de IA baseados em **LangGraph**. O sistema coleta produtos de múltiplas plataformas (Mercado Livre, Shopee, Amazon), organiza os dados em um pipeline de staging, publica no site e — em breve — delega todo esse fluxo a agentes autônomos com raciocínio encadeado via LLM.

Para todos os comandos disponíveis: `make help`

---

## 🗺️ Fluxo principal (uso diário)

```
make serve-cloudflare          ← sobe tudo + túnel HTTPS público
        ↓
make check-tokens              ← verifica se o token ainda está válido
        ↓                         (se sim, pode usar direto — sem reautorizar)
make prepare-ml URL=...        ← coleta 1 produto do Mercado Livre
make prepare-ml                ← coleta lote do list_to_verify.json
        ↓
make verify-product-cheaper    ← confere se é o mais barato no catálogo
        ↓
make stage                     ← publica no site (DB + MinIO)
        ↓
make instagram-post            ← posta no Instagram (opcional)
```

> **Primeira vez ou token expirado?** Siga o [Setup / Reautorização](#️-setup-e-autorização-oauth) abaixo.

---

## ⚙️ Setup inicial (primeira vez)

Esse setup é feito **uma única vez**. Depois disso o fluxo diário usa `make serve-cloudflare-fixed` — URL permanente, sem precisar reautorizar toda vez.

### 1 — Instalar o cloudflared

```bash
make install-cloudflared
```

### 2 — Criar o túnel permanente

```bash
make setup-cloudflare-fixed
```

Isso vai:
1. Abrir o browser para login na sua conta Cloudflare (gratuito)
2. Criar um túnel chamado `vm-site` vinculado à sua conta
3. Gerar o `~/.cloudflared/config.yml` automaticamente

Ao final exibe:
```
✅ Configurado! Use: make serve-cloudflare-fixed
```

> Este passo cria uma URL **fixa e permanente**. Ela **não muda** ao reiniciar — por isso o DevCenter do ML precisa ser configurado apenas uma vez.

### 3 — Pegar a URL permanente do túnel

```bash
cloudflared tunnel info vm-site
```

Copie a URL no formato `https://XXXX.cfargotunnel.com`.

### 4 — Configurar Redirect URI no DevCenter do ML

1. Acesse [developers.mercadolivre.com.br/devcenter](https://developers.mercadolivre.com.br/devcenter)
2. Selecione o seu app → aba **Configuração**
3. Cole no campo **URL de redirecionamento OAuth**:
   ```
   https://XXXX.cfargotunnel.com/auth/mercadolivre/callback
   ```
4. Salve

> ✅ Essa URL nunca muda — você configura o DevCenter **uma vez só**, para sempre.

### 5 — Preencher as credenciais no `.env`

No DevCenter, aba **Credenciais**:

```dotenv
ML_APP_ID=SEU_CLIENT_ID_AQUI
ML_CLIENT_SECRET=SEU_CLIENT_SECRET_AQUI
```

E o ID de afiliado (em [mercadolivre.com.br/afiliados](https://www.mercadolivre.com.br/afiliados)):

```dotenv
MERCADO_LIVRE_AFFILIATE_ID=SEU_ID_DE_AFILIADO
```

### 6 — Reiniciar o container com as novas variáveis

```bash
make rebuild-site
```

### 7 — Subir e autorizar

```bash
make serve-cloudflare-fixed
```

O terminal vai exibir o link de autorização:
```
🔗 Autorize (se ainda não autorizou): https://auth.mercadolivre.com.br/authorization?...
```

1. Abra o link no browser
2. Autorize com sua conta ML
3. O ML redireciona para o callback — o Flask salva os tokens automaticamente

### 8 — Confirmar que funcionou

```bash
make check-tokens   # mostra access_token e refresh_token salvos
make test-api       # faz uma chamada real à API do ML
```

Saída esperada:
```
✅ access_token: APP_USR-...
✅ refresh_token: TG-...
✅ Token válido
```

**Pronto.** A partir de agora use sempre `make serve-cloudflare-fixed` — URL fixa, sem reconfigurar, sem reautorizar (a menos que o token expire por inatividade).

---

## 🌐 Subir servidor (uso diário)

```bash
make serve-cloudflare-fixed
```

- URL sempre a mesma — não precisa reconfigurar o DevCenter
- Tokens renovados automaticamente via `refresh_token`
- Se o `refresh_token` expirar (vários dias sem usar), só reabrir o link de autorização que aparece no terminal

> **Túnel permanente não configurado ainda?** Use `make serve-cloudflare` (URL temporária — muda a cada reinício, exige reautorizar toda vez).

---

## 📦 Coletar produto

```bash
# Mercado Livre — API oficial + OCR preço promocional
make prepare-ml URL="https://produto.mercadolivre.com.br/MLB-..."

# Mercado Livre — lote automático a partir do arquivo
# arquivo: services/site/list_to_prepare_and_stage/list_to_verify.json
make prepare-ml

# Shopee — API + Playwright + OCR
make prepare-shopee URL="https://s.shopee.com.br/..."

# Amazon — Playwright + OCR
make prepare-amazon URL="https://amzn.to/..."
```

O produto é salvo em `services/site/staging/` como JSON com título, preço, imagens, categoria, schema.org, etc.

---

## 💰 Verificar se é o mais barato

Antes de publicar, verifique se o link que você coletou é de fato o menor preço disponível no catálogo do ML. Se houver opção mais barata, o sistema retorna o link do concorrente com o **parâmetro de afiliado** (`matt_tool`) embutido.

```bash
# URL direta
make verify-product-cheaper URL="https://produto.mercadolivre.com.br/MLB-..."

# Link curto ou afiliado (meli.la, etc.)
make verify-product-cheaper URL="https://meli.la/XXXXX"

# Página de catálogo (/p/)
make verify-product-cheaper URL="https://www.mercadolivre.com.br/.../p/MLB..."

# Lote — edite o arquivo e rode sem URL=
# arquivo: services/site/list_to_prepare_and_stage/list_to_verify.json
make verify-product-cheaper
```

**Saída — produto mais caro que o catálogo:**
```
[  1/1] 💸  MLB123456789  R$ 1.000,00 (frete pago)
          Mais barato: R$ 849,90 (🚚 grátis)  [R$ 150,10 mais caro]
          → https://produto.mercadolivre.com.br/MLB987654321
          🔗 Afiliado: https://produto.mercadolivre.com.br/MLB987654321\?matt_tool\=12345678
```

**Saída — já é o mais barato:**
```
[  1/1] ✅  MLB123456789  R$ 849,90 (🚚 grátis)  — já é o mais barato
```

> **Configurar afiliado:** edite `.env` e preencha `MERCADO_LIVRE_AFFILIATE_ID=<seu_id>`.
> Seu ID está em [mercadolivre.com.br/afiliados](https://www.mercadolivre.com.br/afiliados).

---

## 🚀 Publicar no site

```bash
make stage
```

O que acontece:
1. Lê todos os JSONs do `staging/` ainda não processados
2. Faz upload das imagens para o MinIO
3. Salva o produto no PostgreSQL via API Flask
4. Marca os JSONs como `.processed`
5. Roda a deduplicação do staging automaticamente

---

## 📸 Postar no Instagram (opcional)

```bash
make instagram-post
```

---

## 🛠️ Outros comandos úteis

```bash
make up                      # sobe containers sem túnel (dev local)
make down                    # para todos os containers
make rebuild-site            # reconstrói imagem do site e reinicia
make staging-fix-perms       # corrige permissões do staging
make staging-dedup           # deduplicação manual do staging
make logs                    # logs de todos os containers
make prd-up-ghcr             # sobe em produção com imagem do GitHub Container Registry
```

---

## 🧪 Testes

```bash
make test-affiliate          # 28 testes unitários do gerador de links de afiliado
make test-price-validator    # suite completa do price_validator
make test-unit               # todos os testes unitários
```

---

## 🗄️ Product staging pipeline

O fluxo completo de um produto — da URL ao site — passa por quatro camadas:

```mermaid
flowchart LR
    A[URL do produto\nML / Shopee / Amazon] --> B[prepare_*.py\nAPI + OCR + Playwright]
    B --> C[staging/categoria/sub/\nproduto_YYYYMMDD_HHMMSS.json]
    C --> D[staging_dedup.sh\nRemove versões antigas]
    D --> E[stage_products.py]
    E --> F[Upload imagens\nMinIO]
    E --> G[POST /add_product\nFlask API]
    G --> H[save_product\nPostgreSQL]
    H --> I[Redis\nCache de listagens]
    I --> J[/api/products\nFrontend]
```

### O que fica em cada serviço

| Serviço | O que armazena | Detalhes |
|---|---|---|
| **Staging (filesystem)** | JSONs temporários dos produtos | `services/site/staging/{categoria}/{sub}/{slug}_{ts}.json` |
| **MinIO** | Imagens dos produtos (originais + otimizadas) | Bucket `produtos`, paths `/imagens/{slug}/` |
| **PostgreSQL** | Registro completo de cada produto | Tabela `produtos` |
| **Redis** | Cache de listagens da API, pub/sub para webhooks | TTL configurável, canal `produto_events` |

### Campos de um produto no banco

```
id, slug, titulo, descricao, preco, preco_antigo, disponivel,
categoria, subcategoria, tags[], plataforma (ML/Shopee/Amazon),
url_original, url_afiliado, imagens[], thumbnail,
avaliacao, num_avaliacoes, vendedor,
schema_org (JSON-LD para SEO),
criado_em, atualizado_em
```

---
```bash
docker exec site python3 scripts/sync_short_links.py
```
---

## 📚 Documentação

- [Conceito e Arquitetura](docs/conceito.md)
- [Agentes — Visão Geral](docs/DefineMe-agents.md)
- [Scripts de Automação](docs/DefineMe-scripts.md)
- [OAuth Mercado Livre](docs/integrações/OAUTH_MERCADOLIVRE.md)
- [Webhooks](docs/integrações/WEBHOOKS.md)
- [Instagram API](docs/instagram/INSTAGRAM_API_OFICIAL.md)
