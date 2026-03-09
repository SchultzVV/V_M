# 📖 DefineMe - services/site/scripts/

## 🎯 Propósito da Pasta

Esta pasta contém **scripts Python de automação** que são executados via comandos `make`. São responsáveis por todo o fluxo de preparação, staging e publicação de produtos.

## 📂 Scripts Disponíveis

### 🔵 Preparação de Produtos (Mercado Livre)

#### `generate_staging_json.py`
**Usado por:** `make prepare-products`

**Função:** Prepara produtos a partir de uma lista de URLs via scraping.

**Fluxo:**
1. Lê `list_to_prepare_and_stage/list_to_prepare.json`
2. Para cada URL:
   - Faz scraping do Mercado Livre
   - Extrai: título, preços, imagens, external_id
   - Baixa imagens localmente em `uploads/`
   - Solicita categoria e subcategoria ao usuário
3. Gera JSON em `staging/[categoria]/[subcategoria]/`

**Input:**
```json
// list_to_prepare_and_stage/list_to_prepare.json
{
  "platform": "mercadolivre",
  "links": [
    {"url": "https://produto.mercadolivre.com.br/MLB-123456"}
  ]
}
```

**Output:**
```json
// staging/casa-decoracao/sala/produto_20260128_143022.json
{
  "platform": "mercadolivre",
  "external_id": "MLB123456",
  "title": "Produto Exemplo",
  "price": "R$ 99,99",
  "oldPrice": "R$ 199,99",
  "images_local": "uploads/produto-exemplo/",
  "images": [],
  "link": "https://...",
  "tag": "CD",
  "subcategory": "sala",
  "disponivel": true,
  "criado_em": "20260128_143022",
  "via_webhook": false
}
```

---

#### `api_prepare_ml.py`
**Usado por:** `make api-prepare-product URL=<url>`

**Função:** Prepara produto usando **API oficial do Mercado Livre** (requer OAuth).

**Vantagens:**
- ✅ Dados 100% precisos
- ✅ Imagens em alta qualidade
- ✅ Vídeos (se houver)
- ✅ Resolve links de afiliado

**Uso:**
```bash
make api-prepare-product URL="https://mercadolivre.com.br/sec/ABC123"
```

**Requisitos:**
- Token OAuth válido em `config/ml_tokens.json`
- Comando: `make test-oauth` (para obter token)

---

#### `auto_prepare_ml.py`
**Usado por:** `make prepare-auto URL=<url>`

**Função:** Prepara produto via **scraping HTML** (sem necessidade de OAuth).

**Limitações:**
- ⚠️ Imagens podem vir incorretas
- ⚠️ Preços podem estar desatualizados

**Uso:**
```bash
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-123456"
```

---

### 🟢 Preparação de Produtos (Shopee)

#### `shopee_prepare.py`
**Usado por:** `make shopee-prepare-product URL=<url>`

**Função:** Prepara produto da Shopee via scraping.

**Diferencial:**
- Solicita preço manualmente (API Shopee é restrita)
- Suporta categorias e subcategorias
- Detecta cupons e descontos

**Uso:**
```bash
make shopee-prepare-product URL="https://shopee.com.br/product/123/456"
# Durante execução:
# - Categoria: E, CD, ME, PET
# - Subcategoria: (ex: smartphones, sala, etc)
# - Preço atual: 49.99
# - Preço antigo: 167.99
```

---

#### `shopee_update_prices.py`
**Usado por:** `make shopee-update-prices URL=<url>`

**Função:** Atualiza preços e disponibilidade de produtos da Shopee já cadastrados.

**Uso:**
```bash
make shopee-update-prices URL="https://s.shopee.com.br/ABC123"
```

---

### 📤 Publicação no Site

#### `stage_products.py`
**Usado por:** `make stage`

**Função:** Publica produtos preparados no site (banco de dados + MinIO).

**Fluxo:**
1. Lê todos os JSONs de `staging/`
2. Para cada produto:
   - Faz upload de imagens para MinIO
   - Atualiza campo `images` no JSON com URLs do MinIO
   - Insere produto no banco de dados PostgreSQL
   - Marca como publicado

**Evidência:**
```
📦 Processando staging/casa-decoracao/sala/robo-aspirador_20260128.json
📸 Fazendo upload de 8 imagens para MinIO...
   ✅ image_0.jpg -> https://minio:9000/produtos/robo-aspirador/image_0.jpg
   ✅ image_1.jpg -> https://minio:9000/produtos/robo-aspirador/image_1.jpg
   ...
💾 Salvando produto no banco de dados...
✅ Produto publicado com sucesso! ID: 42
```

---

### 🖼️ Preparação para Instagram

#### `prepare_publish_images.py`
**Usado por:** `make prepare-publish`

**Função:** Gera imagens prontas para publicação no Instagram.

**Recursos:**
- Redimensiona para formato Instagram (1080x1080)
- Adiciona marca d'água
- Gera carrossel de imagens
- Salva em `publish_ready/`

**Uso:**
```bash
make prepare-publish  # Processa todos os produtos
```

---

### 🗄️ Migrações de Banco de Dados

#### `migrate_add_tags.py`
**Usado por:** `make migrate-tags`

**Função:** Adiciona coluna `tags` na tabela de produtos.

---

#### `migrate_add_webhook_fields.py`
**Usado por:** `make migrate-webhook`

**Função:** Adiciona campos de webhook (external_id, platform, via_webhook).

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
│  - list_to_prepare.json                         │
│  - Comando make com URL                         │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  PREPARAÇÃO (Scripts de Scraping)               │
│  ┌───────────────────────────────────────────┐  │
│  │ • generate_staging_json.py                │  │
│  │ • api_prepare_ml.py                       │  │
│  │ • auto_prepare_ml.py                      │  │
│  │ • shopee_prepare.py                       │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Output: JSONs em staging/[categoria]/          │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  STAGING (Validação e Organização)              │
│  📁 staging/                                     │
│     ├── casa-decoracao/                         │
│     │   ├── sala/                               │
│     │   └── cozinha/                            │
│     ├── eletronicos/                            │
│     └── petshop/                                │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  PUBLICAÇÃO (Script de Stage)                   │
│  ┌───────────────────────────────────────────┐  │
│  │ • stage_products.py                       │  │
│  │   - Upload MinIO                          │  │
│  │   - Insert PostgreSQL                     │  │
│  └───────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  SITE PUBLICADO                                  │
│  - Banco de dados PostgreSQL                    │
│  - Imagens no MinIO                             │
│  - Produto visível no site                      │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Comandos Make que Usam Esta Pasta

| Comando Make | Script Executado | Descrição |
|--------------|------------------|-----------|
| `make prepare-products` | `generate_staging_json.py` | Prepara múltiplos produtos |
| `make api-prepare-product` | `api_prepare_ml.py` | Prepara via API oficial ML |
| `make prepare-auto` | `auto_prepare_ml.py` | Prepara via scraping ML |
| `make shopee-prepare-product` | `shopee_prepare.py` | Prepara produto Shopee |
| `make shopee-update-prices` | `shopee_update_prices.py` | Atualiza preços Shopee |
| `make stage` | `stage_products.py` | Publica no site |
| `make prepare-publish` | `prepare_publish_images.py` | Prepara imagens Instagram |
| `make migrate-tags` | `migrate_add_tags.py` | Migração banco |
| `make migrate-webhook` | `migrate_add_webhook_fields.py` | Migração banco |
| `make clear-minio` | `clear_minio_images.py` | Limpa MinIO |

---

## 📊 Exemplo Completo de Fluxo

### 1. Preparar Produto
```bash
# Adicionar URLs ao list_to_prepare.json
echo '{
  "platform": "mercadolivre",
  "links": [
    {"url": "https://produto.mercadolivre.com.br/MLB-3766026070"}
  ]
}' > services/site/list_to_prepare_and_stage/list_to_prepare.json

# Executar preparação
make prepare-products
```

**Resultado:**
- JSON criado em `staging/casa-decoracao/sala/robo-aspirador_20260128.json`
- Imagens em `uploads/robo-aspirador/`

### 2. Publicar no Site
```bash
make stage
```

**Resultado:**
- Imagens no MinIO: `minio:9000/produtos/robo-aspirador/`
- Produto no banco de dados
- Visível em `https://localhost:5000`

### 3. Publicar no Instagram
```bash
make instagram-post
```

**Resultado:**
- Post automático via agentes LLM
- Imagens otimizadas
- Caption gerada por IA

---

## 🔗 Links Relacionados

- [DefineMe Raiz](../../DefineMe.md) - Comandos make gerais
- [DefineMe Staging](../staging/DefineMe.md) - Organização de produtos
- [DefineMe Agents](../agents/DefineMe.md) - Sistema LLM
- [MAPA_PASTAS.md](../../MAPA_PASTAS.md) - Estrutura completa
