# 🤖 Preparação Automática de Produtos - Mercado Livre

## Visão Geral

Sistema automatizado para adicionar produtos do Mercado Livre ao site, eliminando a necessidade de entrada manual de dados e download manual de imagens.

## Como Usar

### 1. Preparar Produto Automaticamente

```bash
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-..."
```

ou com link curto de afiliado:

```bash
make prepare-auto URL="https://mercadolivre.com/sec/ABC123"
```

**O que acontece:**
- ✅ Faz scraping dos dados do produto (título, preço, imagens)
- ✅ Baixa todas as imagens automaticamente
- ✅ Detecta a categoria do produto (PET, Eletrônicos, Casa, etc.)
- ✅ Gera o JSON de staging pronto para publicação
- ✅ Captura o External ID do Mercado Livre para webhooks

### 2. Publicar no Site

Depois de preparar o produto, publique-o:

```bash
make stage
```

**O que acontece:**
- ✅ Faz upload das imagens para o MinIO
- ✅ Adiciona o produto ao banco de dados
- ✅ Produto fica disponível no site

## Fluxo Completo

```bash
# 1. Preparar produto automaticamente
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-123456-produto-exemplo"

# 2. Verificar o JSON gerado (opcional)
cat services/site/staging/*.json | tail -n 20

# 3. Publicar no site
make stage
```

## Categorias Detectadas Automaticamente

O sistema detecta automaticamente a categoria baseado em palavras-chave:

- **PET** 🐾: ração, gato, cachorro, pet, coleira, areia
- **Eletrônicos** 📱: celular, notebook, fone, airfryer, robô aspirador
- **Casa & Decoração** 🏠: pote, vaso, cortina, organizador
- **Moda & Estilo** 👕: roupa, sapato, bolsa, óculos
- **Geral** 📦: categoria padrão se não detectar

## Estrutura do JSON Gerado

```json
{
  "platform": "mercadolivre",
  "external_id": "MLB-123456789",
  "title": "Produto Exemplo",
  "price": "R$ 99.90",
  "oldPrice": "R$ 149.90",
  "images_local": "uploads/produto-exemplo",
  "images": [],
  "link": "https://mercadolivre.com/sec/ABC123",
  "tag": "PET",
  "disponivel": true,
  "criado_em": "20260112_143050",
  "via_webhook": false
}
```

## Vantagens sobre o Método Manual

### Método Antigo (Manual)
```bash
make prepare-products  # Digite tudo manualmente
# → Título
# → Preço  
# → Link
# → Categoria
# → Pasta de imagens (que você baixou manualmente)
make stage
```

### Método Novo (Automático)
```bash
make prepare-auto URL="https://link-do-produto"
make stage
```

## Troubleshooting

### Erro: Container site-dev não encontrado
O sistema sobe automaticamente, mas se der erro:
```bash
make up
```

### Erro: Falha ao obter dados do produto
- Verifique se a URL está correta
- Tente acessar a URL no navegador primeiro
- Alguns produtos podem ter proteção anti-scraping

### Imagens não foram baixadas
O sistema continuará sem imagens e usará fallback. Você pode:
- Baixar manualmente e colocar em `uploads/nome-do-produto/`
- Executar `make stage` normalmente

## Exemplos de URLs Válidas

```bash
# URL completa do produto
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-1234567890-produto-exemplo"

# Link curto de afiliado
make prepare-auto URL="https://mercadolivre.com/sec/ABC123"

# Com https
make prepare-auto URL="https://www.mercadolivre.com.br/p/MLB1234567890"
```

## Scripts Relacionados

- `services/site/scripts/auto_prepare_ml.py` - Script principal de automação
- `services/site/scripts/generate_staging_json.py` - Método manual (legacy)
- `services/site/scripts/stage_products.py` - Publicação no site

## Próximos Passos

Após executar `make stage`, o produto estará:
- ✅ Cadastrado no banco de dados
- ✅ Com imagens no MinIO
- ✅ Disponível no site
- ✅ Pronto para receber webhooks do Mercado Livre
