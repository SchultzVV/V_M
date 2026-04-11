# 📖 DefineMe - services/site/scripts/

## 🎯 Propósito da Pasta

Esta pasta contém **scripts Python de automação** que são executados via comandos `make`. São responsáveis por todo o fluxo de preparação, staging e publicação de produtos.

## 📂 Scripts Disponíveis

### 🔵 Preparação de Produtos (Mercado Livre)

#### `prepare_ml_best.py` ⭐ PRIMARY
**Usado por:** `make prepare-ml URL=<url>` | `make prepare-ml` (lote via list_to_verify.json)

**Função:** Preparação COMPLETA de produto ML. Combina **API Oficial + Screenshot + OCR** para obter o preço promocional preciso.

**Fluxo:**
1. Chama a API oficial do ML para dados do produto (título, imagens, external_id)
2. Tira screenshot da página (via info-scrap) e extrai preço promo via OCR
3. Baixa imagens em `uploads/<slug-produto>/`
4. Solicita tag/subcategoria (ou usa `FORCE_CATEGORY` env var para modo lote)
5. Gera JSON em `staging/<categoria>/<subcategoria>/`

**Dependências:** Token OAuth ML válido + container `info-scrap` rodando

**Uso:**
```bash
make prepare-ml URL="https://produto.mercadolivre.com.br/MLB-3766026070"
make prepare-ml  # Lote: lê list_to_verify.json com FORCE_CATEGORY=geral
```

---

#### `api_prepare_ml.py`
**Usado por:** `make prepare-all` (lote interativo)

**Função:** Prepara produto via **API oficial do ML** (sem OCR de screenshot). Usado no pipeline de lote onde categoria é passada interativamente.

---

#### `auto_prepare_ml.py`
**Usado por:** `make prepare-auto URL=<url>`

**Função:** Prepara produto via **scraping HTML** (sem necessidade de OAuth). Fallback quando API não disponível.

**Limitações:**
- ⚠️ Imagens podem vir incorretas
- ⚠️ Preços podem estar desatualizados

---

#### `generate_staging_json.py`
**Usado por:** interno/legado

**Função:** Prepara produtos a partir de lista de URLs via scraping básico. Substituído pelo `prepare_ml_best.py` como script primário.

---

### 🟢 Preparação de Produtos (Shopee)

#### `shopee_prepare_best.py` ⭐ PRIMARY
**Usado por:** `make prepare-shopee URL=<url>`

**Função:** Preparação COMPLETA de produto Shopee. Combina **API + Playwright + OCR**. Aceita screenshot externo (tirado pelo host via `take_screenshot_host.py`) para OCR de preço mais preciso.

**Uso:**
```bash
make prepare-shopee URL="https://s.shopee.com.br/ABC123"
```

---

#### `shopee_prepare_manual.py`
**Usado por:** uso direto / fallback

**Função:** Entrada **manual** de dados Shopee. Usada quando scraping automático falha (Shopee bloqueia bots). Solicita título, preço, imagens interativamente.

---

#### `shopee_prepare.py`
**Usado por:** legado

**Função:** Versão anterior do prepare Shopee (scraping simples). Substituída por `shopee_prepare_best.py`.

---

#### `shopee_update_prices.py`
**Usado por:** `make shopee-update URL=<url>`

**Função:** Atualiza preços e disponibilidade de produtos da Shopee já cadastrados.

---

### 🟠 Preparação de Produtos (Amazon)

#### `amazon_prepare_best.py` ⭐ PRIMARY
**Usado por:** `make prepare-amazon URL=<url>`

**Função:** Preparação COMPLETA de produto Amazon. Combina **scraping HTML + Screenshot + OCR** para dados mais precisos.

**Uso:**
```bash
make prepare-amazon URL="https://amzn.to/ABC123"
```

---

### 🏷️ Organização de Tags

#### `organize_tags.py` ⭐
**Usado por:** `make organize-tags` | `make organize-tags-auto`

**Função:** Reorganiza tags/categorias dos produtos em staging por análise de título.

**Modos:**
- **Inteligente** (`make organize-tags`): auto-cadastra confiança ≥ 50%, pergunta ao usuário o resto
- **Automático silencioso** (`make organize-tags-auto` via `--auto`): auto-cadastra todo confiança ≥ 50%, pula o resto

**Uso:**
```bash
make organize-tags       # Interativo (recomendado antes do stage)
make organize-tags-auto  # Silencioso (CI/automação)
```

---

#### `organize_interactive.py`
**Usado por:** uso direto / legado

**Função:** Script interativo pontual para reclassificar produtos específicos que ficaram em `geral/`. Mostra título e pede categoria manualmente.

---

### 📤 Publicação no Site

#### `stage_products.py` ⭐
**Usado por:** `make stage` | `make restage`

**Função:** Publica produtos preparados no site (banco de dados PostgreSQL + MinIO).

**Flags:**
- Sem flag (`make stage`): processa apenas JSONs novos (não listados em `staging/.processed`)
- `--force` (`make restage`): reprocessa TODOS os JSONs, ignora `.processed`

**Fluxo:**
1. Lê todos os JSONs de `staging/**/*.json` (recursivo)
2. Pula arquivos já em `.processed` (salvo no modo normal) e arquivos não-produto (sem campos `platform`/`title`/`price`)
3. Para cada produto:
   - Faz upload de imagens para MinIO (bucket = `platform`, ex: `mercadolivre`)
   - URL pública: `http://localhost:9000/<platform>/<slug-produto>/<timestamp>_<filename>`
   - POST `https://localhost:5000/add_product` com payload completo
   - Flask salva em PostgreSQL
4. Atualiza `staging/.processed` com os nomes dos arquivos processados

**Evidência:**
```
📁 Criando pasta do produto: robo-aspirador-robot-w90
✅ Upload: http://localhost:9000/mercadolivre/robo-aspirador.../20260411_183600_image_1.jpg
[✔] Produto salvo: casa-decoracao/sala/robo-aspirador_20260408.json (Tag: CD/sala)
✅ 68 produto(s) processado(s)
```

---

### 🔄 Atualização de Preços e Re-preparação

#### `update_ml_prices.py` ⭐
**Usado por:** `make update-ml-prices` | `make update-ml-prices DRY=1` | `make update-ml-prices ID=MLB...`

**Função:** Percorre TODOS os produtos ML no banco e busca o vendedor mais barato via API oficial. Atualiza preço e link se encontrar oferta melhor.

**Modos:**
- Padrão: atualiza todos os produtos ML ativos
- `DRY=1`: simula sem alterar banco
- `ID=MLB...`: processa apenas um produto específico

---

#### `api_update_ml.py`
**Usado por:** `make api-update URL=<url>`

**Função:** Atualiza um produto existente no banco via API oficial ML. Atualiza: preço, desconto, disponibilidade e mídias.

**Uso:**
```bash
make api-update URL="https://produto.mercadolivre.com.br/MLB-123456"
```

---

#### `reprepare_all_ml.py` ⭐
**Usado por:** `make reprepare-ml` | `make reprepare-ml DRY=1` | `make reprepare-ml ID=MLB...`

**Função:** Re-prepara TODOS os produtos ML do banco usando o pipeline completo (API + OCR + imagens). Mantém tags/categorias existentes. Faz `stage` automático após concluir.

**Quando usar:** Após mudança no pipeline de preparação, ou quando imagens/preços ficaram desatualizados.

---

#### `reprepare_associate_ml.py` ⭐
**Usado por:** `make reprepare-associate-ml`

**Função:** Re-prepara TODOS os produtos ML COM link de afiliado (`meli.la/...`). Usa `ML_SELLER_ID` do `.env`. Preço mais preciso via OCR da página do afiliado.

**Requisito:** `ML_SELLER_ID` preenchido no `.env`

---

### 🖼️ Preparação para Instagram

#### `prepare_publish_images.py`
**Usado por:** `make prepare-publish` | `make prepare-post-image FILE=...`

**Função:** Gera imagens prontas para publicação no Instagram.

**Recursos:**
- Redimensiona para formato Instagram (1080x1080)
- Adiciona marca d'água
- Gera carrossel de imagens
- Salva em `publish_ready/`

---

### 🛠️ Utilitários

#### `take_screenshot_host.py`
**Usado por:** `make prepare-shopee` (internamente)

**Função:** Tira screenshot de URL no **host** (fora do container) usando Playwright. Necessário para contornar bloqueios do Shopee. O screenshot é copiado para o container e usado pelo `shopee_prepare_best.py`.

---

#### `sync_short_links.py`
**Usado por:** uso direto

**Função:** Sincroniza todos os links dos produtos já preparados em staging para o arquivo central `staging/short_link/links.json`.

---

#### `category_selector.py`
**Usado por:** scripts de prepare (importado)

**Função:** Módulo compartilhado de seleção de categoria/subcategoria. Exibe menu interativo para o usuário escolher tag/subcategoria.

---

### 🗄️ Migrações de Banco de Dados

#### `migrate_add_tags.py`
**Usado por:** `make migrate-tags`

**Função:** Adiciona coluna `tags` na tabela de produtos.

---

#### `migrate_add_webhook_fields.py`
**Usado por:** `make migrate-webhook`

**Função:** Adiciona campos de webhook (`external_id`, `platform`, `via_webhook`).

---

#### `migrate_add_subcategory.py`
**Usado por:** `make migrate-subcategory`

**Função:** Adiciona coluna `subcategory` na tabela de produtos.

---

### 🧹 Utilitários

#### `clear_minio_images.py`
**Usado por:** `make clear-minio` ou `make clear-minio-force`

**Função:** Remove TODAS as imagens do MinIO (com ou sem confirmação).

**Uso:**
```bash
make clear-minio        # Pede confirmação
make clear-minio-force  # Força remoção
```

---

#### `check_stage_images.py`
**Usado por:** `make check-stage`

**Função:** Verifica integridade de imagens no staging.

---

## 🔄 Fluxo de Dados Entre Scripts

```
┌─────────────────────────────────────────────────┐
│  Fonte de Dados (URLs)                          │
│  - URL via make prepare-ml/shopee/amazon        │
│  - list_to_verify.json (lote ML)                │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  PREPARAÇÃO (Scripts de Scraping / API)         │
│  ┌───────────────────────────────────────────┐  │
│  │ ML:     prepare_ml_best.py (API+OCR)      │  │
│  │ Shopee: shopee_prepare_best.py (API+OCR)  │  │
│  │ Amazon: amazon_prepare_best.py (OCR)      │  │
│  │ Lote:   generate_staging_json.py          │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Output: JSONs em staging/<categoria>/          │
│          Imagens em uploads/<slug>/             │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  ORGANIZAÇÃO (Tags / Categorias)                │
│  ┌───────────────────────────────────────────┐  │
│  │ organize_tags.py (auto + interativo)      │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  📁 staging/                                     │
│     ├── casa-decoracao/sala/                    │
│     ├── eletronicos/smartphones/               │
│     ├── moda-estilo/calcados/                  │
│     └── petshop/saude/                         │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  PUBLICAÇÃO (Stage)                             │
│  ┌───────────────────────────────────────────┐  │
│  │ stage_products.py [--force]               │  │
│  │   - Upload MinIO (bucket = platform)      │  │
│  │   - URL: http://localhost:9000/<plat>/... │  │
│  │   - POST /add_product → PostgreSQL        │  │
│  │   - Registra em staging/.processed        │  │
│  └───────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  SITE PUBLICADO                                  │
│  - PostgreSQL: metadata dos produtos            │
│  - MinIO: imagens (http://localhost:9000/...)   │
│  - Nginx → GET /api/products → React exibe     │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  MANUTENÇÃO (Atualização de Preços)             │
│  ┌───────────────────────────────────────────┐  │
│  │ update_ml_prices.py (busca menor preço)   │  │
│  │ api_update_ml.py (atualiza individual)    │  │
│  │ reprepare_all_ml.py (refaz tudo API+OCR)  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Comandos Make que Usam Esta Pasta

| Comando Make | Script Executado | Descrição |
|--------------|------------------|-----------|
| `make prepare-ml` ⭐ | `prepare_ml_best.py` | Prepara produto ML (API + OCR) |
| `make prepare-ml` (sem URL) | `prepare_ml_best.py` + `list_to_verify.json` | Lote ML silencioso |
| `make prepare-shopee` ⭐ | `shopee_prepare_best.py` | Prepara produto Shopee (API + OCR) |
| `make prepare-amazon` ⭐ | `amazon_prepare_best.py` | Prepara produto Amazon (scraping + OCR) |
| `make prepare-all` | `api_prepare_ml.py` | Lote ML interativo |
| `make prepare-auto` | `auto_prepare_ml.py` | Prepara ML via scraping |
| `make organize-tags` ⭐ | `organize_tags.py` | Organiza tags (interativo) |
| `make organize-tags-auto` | `organize_tags.py --auto` | Organiza tags (silencioso) |
| `make stage` ⭐ | `stage_products.py` | Publica no site (somente novos) |
| `make restage` | `stage_products.py --force` | Re-publica TUDO no site |
| `make api-update` | `api_update_ml.py` | Atualiza produto ML individual |
| `make shopee-update` | `shopee_update_prices.py` | Atualiza preços Shopee |
| `make update-ml-prices` ⭐ | `update_ml_prices.py` | Busca menor preço ML (todos) |
| `make reprepare-ml` ⭐ | `reprepare_all_ml.py` | Refaz prepare completo todos ML |
| `make reprepare-associate-ml` | `reprepare_associate_ml.py` | Refaz prepare COM afiliado ML |
| `make check-stage` | `check_stage_images.py` | Verifica imagens no staging |
| `make prepare-post-image` | `prepare_publish_images.py` | Gera imagem Instagram |
| `make migrate-tags` | `migrate_add_tags.py` | Migração banco — coluna tags |
| `make migrate-webhook` | `migrate_add_webhook_fields.py` | Migração banco — campos webhook |
| `make migrate-subcategory` | `migrate_add_subcategory.py` | Migração banco — coluna subcategory |
| `make clear-minio` | `clear_minio_images.py` | Limpa MinIO (com confirmação) |
| `make clear-minio-force` | `clear_minio_images.py` | Limpa MinIO (sem confirmação) |

---

## 📊 Exemplo Completo de Fluxo Atual

```bash
# 1. Preparar produto ML
make prepare-ml URL="https://produto.mercadolivre.com.br/MLB-3766026070"

# 2. Organizar tags (recomendado)
make organize-tags

# 3. Publicar no site
make stage

# 4. Verificar no frontend
# https://localhost → produtos aparecem via React + Nginx
```

---

## 🔗 Links Relacionados

- [DefineMe Raiz](DefineMe.md) - Visão geral da stack
- [DefineMe Agents](DefineMe-agents.md) - Sistema LLM para Instagram
- [shared/make_commands.md](../agents/shared/make_commands.md) - Referência completa de make
