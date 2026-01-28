# 📖 DefineMe - services/site/staging/

## 🎯 Propósito da Pasta

Pasta de **staging de produtos** - armazena JSONs de produtos preparados aguardando publicação no site. Funciona como uma **fila intermediária** entre a preparação e a publicação.

## 📂 Estrutura de Organização

### Hierarquia por Categorias

```
staging/
├── casa-decoracao/          # Tag: CD
│   ├── banheiro/
│   ├── sala/
│   ├── quarto/
│   ├── cozinha/
│   ├── corredor/
│   ├── garagem/
│   ├── sacada/
│   └── area-servico/
│
├── moda-estilo/             # Tag: ME
│   ├── feminino/
│   ├── masculino/
│   ├── infantil/
│   ├── calcados/
│   ├── acessorios/
│   ├── bolsas/
│   └── relogios/
│
├── eletronicos/             # Tag: E
│   ├── smartphones/
│   ├── computadores/
│   ├── audio/
│   ├── tv/
│   ├── games/
│   ├── cameras/
│   ├── smartwatch/
│   └── acessorios/
│
├── petshop/                 # Tag: PET
│   ├── caes/
│   ├── gatos/
│   ├── racao/
│   ├── brinquedos/
│   ├── higiene/
│   ├── acessorios/
│   └── saude/
│
└── geral/                   # Tag: geral (sem subcategoria)
```

## 📄 Formato do JSON

### Estrutura Padrão

```json
{
  "platform": "mercadolivre",
  "external_id": "MLB3766026070",
  "title": "Robô Varredora Aspirador De Pó 1200pa Automática 3 Em 1",
  "price": "R$ 359,99",
  "oldPrice": "R$ 999,99",
  "images_local": "uploads/robo-varredora-aspirador/",
  "images": [],
  "link": "https://produto.mercadolivre.com.br/MLB-3766026070-...",
  "tag": "CD",
  "subcategory": "sala",
  "disponivel": true,
  "criado_em": "20260128_143022",
  "via_webhook": false
}
```

### Campos Explicados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `platform` | string | Origem: "mercadolivre", "shopee", "amazon" |
| `external_id` | string | ID único no marketplace (ex: MLB123456) |
| `title` | string | Título completo do produto |
| `price` | string | Preço atual formatado (R$ XX,XX) |
| `oldPrice` | string | Preço antigo/promocional (R$ XX,XX) |
| `images_local` | string | Pasta local com imagens baixadas |
| `images` | array | URLs MinIO (preenchido pelo `stage`) |
| `link` | string | URL de afiliado do produto |
| `tag` | string | Categoria: CD, ME, E, PET, geral |
| `subcategory` | string | Subcategoria específica |
| `disponivel` | boolean | Disponibilidade do produto |
| `criado_em` | string | Timestamp: YYYYMMDD_HHMMSS |
| `via_webhook` | boolean | Se foi criado por webhook ML |

## 🔄 Ciclo de Vida do Produto

```
┌─────────────────────────────────────────────────┐
│  1. CRIAÇÃO                                     │
│     • make prepare-products                     │
│     • make api-prepare-product                  │
│     • make prepare-auto                         │
│                                                  │
│  Output: JSON em staging/[categoria]/[subcat]/  │
│          Nome: [slug]_[timestamp].json          │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  2. AGUARDANDO (STAGING)                        │
│     • Arquivo permanece em staging/             │
│     • Imagens em uploads/                       │
│     • Aguarda comando make stage                │
│                                                  │
│  Status: images = []  (vazio)                   │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  3. PUBLICAÇÃO                                  │
│     • make stage                                │
│     • stage_products.py processa JSONs          │
│     • Upload de imagens para MinIO              │
│     • Insert no PostgreSQL                      │
│                                                  │
│  Modificações no JSON:                          │
│  - images = [urls_minio]  (preenchido)          │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  4. PUBLICADO                                   │
│     • Produto visível no site                   │
│     • Imagens acessíveis via MinIO              │
│     • Pronto para Instagram (make instagram-post)│
└─────────────────────────────────────────────────┘
```

## 🚀 Comandos Relacionados

### Criar Produtos em Staging

```bash
# Múltiplos produtos de uma vez
make prepare-products

# Um produto via API oficial (melhor)
make api-prepare-product URL="https://mercadolivre.com.br/sec/ABC"

# Um produto via scraping
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-123"

# Produto da Shopee
make shopee-prepare-product URL="https://shopee.com.br/..."
```

### Publicar Produtos

```bash
# Publicar todos os produtos em staging/
make stage
```

### Verificar Estado

```bash
# Verificar integridade de imagens
make check-stage

# Listar produtos em staging
find services/site/staging -name "*.json" -type f
```

## 📊 Exemplo Real

### Produto Criado
**Arquivo:** `staging/casa-decoracao/sala/robo-varredora-aspirador_20260128_143022.json`

```json
{
  "platform": "mercadolivre",
  "external_id": "MLB3766026070",
  "title": "Robô Varredora Aspirador De Pó 1200pa Automática 3 Em 1 Limpeza Doméstica Robótico Inteligente E Silencioso",
  "price": "R$ 359,99",
  "oldPrice": "R$ 999,99",
  "images_local": "uploads/robo-varredora-aspirador-de-po-1200pa-automatica-3-em-1-limpeza-domestica-robotico-inteligente-e-silencioso",
  "images": [],
  "link": "https://produto.mercadolivre.com.br/MLB-3766026070-robo-varredora-aspirador-de-po-1200pa-automatica-3-em-1-limpeza-domestica-robotico-inteligente-e-silencioso",
  "tag": "CD",
  "subcategory": "sala",
  "disponivel": true,
  "criado_em": "20260122_214506",
  "via_webhook": false
}
```

**Imagens Locais:**
```
uploads/robo-varredora-aspirador.../
├── image_0.jpg
├── image_1.jpg
├── image_2.jpg
├── image_3.jpg
├── image_4.jpg
├── image_5.jpg
├── image_6.jpg
└── image_7.jpg
```

### Após `make stage`

O JSON é atualizado:

```json
{
  "platform": "mercadolivre",
  "external_id": "MLB3766026070",
  "title": "Robô Varredora Aspirador De Pó 1200pa...",
  "price": "R$ 359,99",
  "oldPrice": "R$ 999,99",
  "images_local": "uploads/robo-varredora-aspirador.../",
  "images": [
    "http://minio:9000/produtos/robo-varredora-aspirador/image_0.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_1.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_2.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_3.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_4.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_5.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_6.jpg",
    "http://minio:9000/produtos/robo-varredora-aspirador/image_7.jpg"
  ],
  "link": "https://produto.mercadolivre.com.br/MLB-3766026070...",
  "tag": "CD",
  "subcategory": "sala",
  "disponivel": true,
  "criado_em": "20260122_214506",
  "via_webhook": false
}
```

**No Banco de Dados:**
```sql
SELECT id, title, price, tag, subcategory FROM produtos 
WHERE external_id = 'MLB3766026070';

-- Resultado:
-- id | title                    | price      | tag | subcategory
-- 42 | Robô Varredora Aspira... | R$ 359,99  | CD  | sala
```

## 🎯 Boas Práticas

### ✅ Recomendado
- Organizar produtos por categoria e subcategoria
- Sempre preencher `external_id` para rastreamento
- Verificar `disponivel = true` antes de publicar
- Manter `images_local` com imagens de qualidade

### ❌ Evitar
- Criar JSONs diretamente sem usar scripts
- Deixar `images_local` vazio
- Publicar produtos sem categoria
- Modificar JSONs manualmente após `make stage`

## 🔗 Links Relacionados

- [DefineMe Scripts](scripts/DefineMe.md) - Scripts que criam/processam staging
- [DefineMe Raiz](../../DefineMe.md) - Comandos make prepare/stage
- [MAPA_PASTAS.md](../../MAPA_PASTAS.md) - Estrutura completa
