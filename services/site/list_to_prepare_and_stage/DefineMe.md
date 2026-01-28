# 📖 DefineMe - services/site/list_to_prepare_and_stage/

## 🎯 Propósito da Pasta

Esta pasta funciona como uma **fila de produtos** - contém o arquivo `list_to_prepare.json` que lista URLs de produtos aguardando processamento pelo sistema.

## 📄 Arquivo Principal: `list_to_prepare.json`

### Estrutura do Arquivo

```json
{
  "platform": "mercadolivre",
  "links": [
    {
      "url": "https://produto.mercadolivre.com.br/MLB-3766026070-robo-aspirador..."
    },
    {
      "url": "https://produto.mercadolivre.com.br/MLB-1234567890-outro-produto..."
    },
    {
      "url": "https://mercadolivre.com.br/sec/ABC123"
    }
  ]
}
```

### Campos Explicados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `platform` | string | Marketplace origem: "mercadolivre", "shopee", "amazon" |
| `links` | array | Lista de objetos contendo URLs |
| `links[].url` | string | URL completa do produto |

---

## 🔄 Fluxo de Uso

```
┌─────────────────────────────────────────────────┐
│  1. ADICIONAR URLs                              │
│     • Editar list_to_prepare.json               │
│     • Adicionar URLs de produtos                │
│     • Salvar arquivo                            │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  2. PROCESSAR FILA                              │
│     • make prepare-products                     │
│     • Script lê list_to_prepare.json            │
│     • Processa cada URL sequencialmente         │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  3. GERAÇÃO DE STAGING                          │
│     Para cada URL:                              │
│     • Scraping/API do produto                   │
│     • Download de imagens                       │
│     • Solicita categoria ao usuário             │
│     • Gera JSON em staging/                     │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  4. RESULTADO                                   │
│     • JSONs gerados em staging/                 │
│     • Imagens em uploads/                       │
│     • Produtos prontos para make stage          │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Comandos Relacionados

### Processar Fila Completa

```bash
# Processa TODOS os links do arquivo
make prepare-products
```

**Comportamento:**
- Lê `list_to_prepare.json`
- Para cada URL, faz scraping
- Pergunta categoria para cada produto
- Gera JSONs em `staging/`

---

### Processar URL Única (sem fila)

```bash
# API Oficial (melhor)
make api-prepare-product URL="https://mercadolivre.com.br/sec/ABC123"

# Scraping
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-123"
```

---

### Processar em Lote Interativo

```bash
# Processa todos e pergunta categoria para cada um
make prepare-all
```

---

## 📊 Exemplos Práticos

### Exemplo 1: Adicionar Produtos do Mercado Livre

**1. Editar o arquivo:**
```bash
nano services/site/list_to_prepare_and_stage/list_to_prepare.json
```

**2. Adicionar URLs:**
```json
{
  "platform": "mercadolivre",
  "links": [
    {
      "url": "https://produto.mercadolivre.com.br/MLB-3766026070-robo-varredora-aspirador-de-po-1200pa-automatica-3-em-1-limpeza-domestica-robotico-inteligente-e-silencioso"
    },
    {
      "url": "https://produto.mercadolivre.com.br/MLB-2837465291-aspirador-de-po-vertical-wap-power-speed-turbo-1600w"
    },
    {
      "url": "https://mercadolivre.com.br/sec/1A2B3C"
    }
  ]
}
```

**3. Processar:**
```bash
make prepare-products
```

**4. Resultado:**
```
🚀 Iniciando preparação de produtos...
📦 Encontrados 3 links para processar
🌐 Plataforma: mercadolivre

============================================================
📦 Produto 1/3
🔗 URL: https://produto.mercadolivre.com.br/MLB-3766026070...
============================================================

🔄 Coletando informações do produto automaticamente...
✅ Título: Robô Varredora Aspirador De Pó...
💰 Preço: R$ 359,99
📥 Baixando 8 imagens...
✅ Imagens salvas

🏷️  Escolha a categoria do produto:
1. CD - Casa & Decoração
...
Digite o número da categoria: 1

✅ Staging salvo em: staging/casa-decoracao/sala/robo-varredora_20260128.json

[Repete para produtos 2 e 3]

✅ Processo concluído!
📁 3 arquivo(s) gerado(s)
```

---

### Exemplo 2: Arquivo com Múltiplas Plataformas

**Nota:** Atualmente o script processa apenas uma plataforma por vez.

**Recomendação:** Criar arquivos separados:
- `list_to_prepare_ml.json` - Mercado Livre
- `list_to_prepare_shopee.json` - Shopee

---

## 📁 Outros Arquivos na Pasta

### JSONs de Produtos Individuais

Quando um produto é preparado via `make api-prepare-product`, ele gera um JSON temporário nesta pasta:

```
list_to_prepare_and_stage/
├── list_to_prepare.json
└── robo-varredora-aspirador-de-po_20260122_214506.json
```

Esses arquivos individuais são **rascunhos temporários** antes de serem movidos para `staging/`.

---

## ⚠️ Boas Práticas

### ✅ Recomendado

1. **Validar URLs antes de adicionar:**
   ```bash
   # Teste se a URL abre no navegador
   curl -I "https://produto.mercadolivre.com.br/MLB-..."
   ```

2. **Processar em lotes pequenos:**
   ```json
   // Melhor: 5-10 produtos por vez
   {
     "platform": "mercadolivre",
     "links": [
       {"url": "..."},
       {"url": "..."},
       {"url": "..."}
     ]
   }
   ```

3. **Backup antes de processar:**
   ```bash
   cp list_to_prepare.json list_to_prepare.backup.json
   ```

4. **Limpar após processamento:**
   ```bash
   # Após make prepare-products bem-sucedido
   echo '{"platform":"mercadolivre","links":[]}' > list_to_prepare.json
   ```

### ❌ Evitar

1. **URLs inválidas ou mortas**
2. **Misturar plataformas no mesmo arquivo**
3. **Adicionar duplicatas**
4. **Deixar arquivo vazio** (causa erro)

---

## 🔍 Verificação

### Checar quantos produtos estão na fila

```bash
cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq '.links | length'
```

### Listar URLs da fila

```bash
cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq -r '.links[].url'
```

### Validar formato do JSON

```bash
cat services/site/list_to_prepare_and_stage/list_to_prepare.json | jq .
```

---

## 📈 Estatísticas de Uso

### Monitorar processamento

```bash
# Quantos produtos já foram processados?
find services/site/staging -name "*.json" -type f | wc -l

# Quais categorias têm mais produtos?
find services/site/staging -type d -name "*" | sort | uniq -c
```

---

## 🔗 Links Relacionados

- [DefineMe Raiz](../../DefineMe.md) - Comandos prepare-products
- [DefineMe Scripts](../scripts/DefineMe.md) - Scripts que processam a fila
- [DefineMe Staging](../staging/DefineMe.md) - Destino dos produtos processados
- [MAPA_PASTAS.md](../../MAPA_PASTAS.md) - Estrutura completa
