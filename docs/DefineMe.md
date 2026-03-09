# 📖 DefineMe - Raiz do Projeto V_M

## 🎯 Propósito da Pasta

Esta é a **raiz do projeto V_M** - um sistema de automação de e-commerce que integra produtos do Mercado Livre e Shopee com publicação automatizada no Instagram usando agentes LLM.

## 🚀 Comandos Make Disponíveis

### 📦 **PREPARAÇÃO DE PRODUTOS**

#### `make prepare-products`
**O comando mais importante para adicionar produtos ao sistema via modo manual/semi-automático**

##### 🔍 O que faz:
1. **Verifica arquivo de fila**: Procura `services/site/list_to_prepare_and_stage/list_to_prepare.json`
2. **Processa cada link**: Para cada URL na lista:
   - Faz scraping do Mercado Livre
   - Extrai título, preços, imagens, ID do produto
   - Baixa todas as imagens localmente
   - Solicita categoria e subcategoria ao usuário
3. **Gera JSON de staging**: Cria arquivo em `services/site/staging/[categoria]/[produto]_[timestamp].json`
4. **Organiza por categorias**: Armazena em pastas estruturadas

##### 📝 Fluxo Detalhado:

```
┌─────────────────────────────────────────────────────┐
│  make prepare-products                              │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  1. Executa run-py com generate_staging_json.py    │
│     - Verifica se container 'site' está rodando    │
│     - Sobe containers se necessário                 │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  2. Script carrega list_to_prepare.json             │
│     Localização: services/site/                     │
│                  list_to_prepare_and_stage/         │
│                  list_to_prepare.json               │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  3. Para cada link na lista:                        │
│     ┌─────────────────────────────────────────┐    │
│     │ a) Scraping do Mercado Livre            │    │
│     │    - scrape_mercadolivre_product(url)   │    │
│     │    - Extrai: título, preços, imagens    │    │
│     │    - Detecta descontos automaticamente  │    │
│     │    - Extrai External ID (MLB...)        │    │
│     └─────────────────────────────────────────┘    │
│                                                      │
│     ┌─────────────────────────────────────────┐    │
│     │ b) Download de imagens                  │    │
│     │    - download_images()                  │    │
│     │    - Salva em uploads/[slug-produto]/   │    │
│     │    - Todas imagens do anúncio           │    │
│     └─────────────────────────────────────────┘    │
│                                                      │
│     ┌─────────────────────────────────────────┐    │
│     │ c) Solicita ao usuário                  │    │
│     │    - Categoria (CD, ME, E, PET, geral)  │    │
│     │    - Subcategoria (se aplicável)        │    │
│     └─────────────────────────────────────────┘    │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  4. Gera JSON de staging                            │
│     Estrutura do arquivo:                           │
│     {                                                │
│       "platform": "mercadolivre",                   │
│       "external_id": "MLB3766026070",               │
│       "title": "Robô Aspirador...",                 │
│       "price": "R$ 359.99",                         │
│       "oldPrice": "R$ 999.99",                      │
│       "images_local": "uploads/robo-aspirador/",    │
│       "images": [],                                  │
│       "link": "https://...",                        │
│       "tag": "CD",                                   │
│       "subcategory": "sala",                        │
│       "disponivel": true,                           │
│       "criado_em": "20260128_143022",               │
│       "via_webhook": false                          │
│     }                                                │
│                                                      │
│     Salvo em: staging/casa-decoracao/sala/          │
│               robo-aspirador_20260128_143022.json   │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  5. Resumo final                                    │
│     ✅ X arquivo(s) gerado(s)                       │
│     📁 Lista de todos os JSONs criados              │
└─────────────────────────────────────────────────────┘
```

##### 📂 Estrutura de Categorias:

| Tag | Nome Completo | Pasta Staging | Subcategorias Disponíveis |
|-----|--------------|---------------|---------------------------|
| `CD` | Casa & Decoração | `staging/casa-decoracao/` | banheiro, sala, quarto, cozinha, corredor, garagem, sacada, area-servico |
| `ME` | Moda & Estilo | `staging/moda-estilo/` | feminino, masculino, infantil, calcados, acessorios, bolsas, relogios |
| `E` | Eletrônicos | `staging/eletronicos/` | smartphones, computadores, audio, tv, games, cameras, smartwatch, acessorios |
| `PET` | PetShop | `staging/petshop/` | caes, gatos, racao, brinquedos, higiene, acessorios, saude |
| `geral` | Geral | `staging/geral/` | (nenhuma) |

##### 💡 Exemplo de Uso:

```bash
# 1. Adicione URLs ao arquivo de fila
echo '{
  "platform": "mercadolivre",
  "links": [
    {
      "url": "https://produto.mercadolivre.com.br/MLB-3766026070-robo-aspirador"
    }
  ]
}' > services/site/list_to_prepare_and_stage/list_to_prepare.json

# 2. Execute o comando
make prepare-products

# 3. Durante execução, será perguntado:
#    🏷️  Escolha a categoria do produto:
#    1. CD - Casa & Decoração
#    2. ME - Moda & Estilo
#    3. E - Eletrônicos
#    4. PET - PetShop
#    5. Geral (padrão)
#    Digite o número da categoria (1-5) [5]: 1
#
#    🔖 Subcategorias disponíveis para CD:
#    1. Banheiro
#    2. Sala
#    3. Quarto
#    ...
#    Digite o número da subcategoria: 2

# 4. Resultado:
#    ✅ Staging salvo em: staging/casa-decoracao/sala/robo-aspirador_20260128_143022.json
#    🏷️  Tag: CD
#    🔖 Subcategoria: sala
#    📦 Plataforma: mercadolivre
#    🔗 External ID: MLB3766026070
```

##### 📊 Evidências de Execução:

**Console Output Real:**
```
🚀 Iniciando preparação de produtos...

📋 Verificando arquivo list_to_prepare.json...

📦 Encontrados 1 links para processar
🌐 Plataforma: mercadolivre

============================================================
📦 Produto 1/1
🔗 URL: https://produto.mercadolivre.com.br/MLB-3766026070...
============================================================

🔄 Coletando informações do produto automaticamente...

============================================================
📋 INFORMAÇÕES COLETADAS
============================================================
📦 Título: Robô Varredora Aspirador De Pó 1200pa Automática 3 Em 1...
💰 Preço: R$ 359,99
💰 Preço Antigo: R$ 999,99
🖼️  Imagens: 8 encontradas
🆔 External ID: MLB3766026070
🎉 Desconto: 64% OFF
============================================================

📥 Baixando imagens do produto...
✅ Imagens salvas em: uploads/robo-varredora-aspirador-de-po/

🏷️  Escolha a categoria do produto:
1. CD - Casa & Decoração
2. ME - Moda & Estilo
3. E - Eletrônicos
4. PET - PetShop
5. Geral (padrão)
Digite o número da categoria (1-5) [5]: 1

🔖 Subcategorias disponíveis para CD:
1. Banheiro
2. Sala
3. Quarto
4. Cozinha
5. Corredor
6. Garagem
7. Sacada
8. Area Servico
9. Nenhuma (pular)
Digite o número da subcategoria (1-9) [9]: 2
✅ Subcategoria selecionada: sala
✅ Categoria selecionada: CD

============================================================
📦 Gerando arquivos de staging para 1 produto(s)...
============================================================

✅ Staging salvo em: staging/casa-decoracao/sala/robo-varredora-aspirador-de-po_20260128_143022.json
🏷️  Tag: CD
🔖 Subcategoria: sala
📦 Plataforma: mercadolivre
🔗 External ID: MLB3766026070
✅ Disponível: Sim

============================================================
✅ Processo concluído!
📁 1 arquivo(s) gerado(s):
   - staging/casa-decoracao/sala/robo-varredora-aspirador-de-po_20260128_143022.json
============================================================
```

**Arquivo JSON Gerado:**
```json
{
  "platform": "mercadolivre",
  "external_id": "MLB3766026070",
  "title": "Robô Varredora Aspirador De Pó 1200pa Automática 3 Em 1 Limpeza Doméstica Robótico Inteligente E Silencioso",
  "price": "R$ 359,99",
  "oldPrice": "R$ 999,99",
  "images_local": "uploads/robo-varredora-aspirador-de-po-1200pa-automatica-3-em-1-limpeza-domestica-robotico-inteligente-e-silencioso",
  "images": [],
  "link": "https://produto.mercadolivre.com.br/MLB-3766026070-robo-varredora-aspirador...",
  "tag": "CD",
  "subcategory": "sala",
  "disponivel": true,
  "criado_em": "20260128_143022",
  "via_webhook": false
}
```

**Imagens Baixadas:**
```
uploads/robo-varredora-aspirador-de-po/
├── image_0.jpg  (imagem principal)
├── image_1.jpg
├── image_2.jpg
├── image_3.jpg
├── image_4.jpg
├── image_5.jpg
├── image_6.jpg
└── image_7.jpg
```

##### ⚠️ Requisitos:
- Container `site` rodando (criado automaticamente)
- Arquivo `list_to_prepare.json` com URLs válidas
- Conexão com internet para scraping

##### 🔗 Relacionado com:
- `make stage` - Próximo passo: publicar produtos
- `make api-prepare-product` - Alternativa usando API oficial ML
- `make prepare-auto` - Versão para uma URL única

---

#### `make api-prepare-product URL=<url>`
Prepara produto usando a **API oficial do Mercado Livre** (melhor qualidade).

**Vantagens:**
- ✅ Dados 100% precisos da API
- ✅ Imagens em alta qualidade
- ✅ Vídeos do produto (se houver)
- ✅ Resolve links de afiliado

**Uso:**
```bash
make api-prepare-product URL="https://mercadolivre.com.br/sec/ABC123"
```

---

#### `make prepare-auto URL=<url>`
Prepara produto via **scraping HTML** (sem necessidade de OAuth).

**Uso:**
```bash
make prepare-auto URL="https://produto.mercadolivre.com.br/MLB-123456"
```

---

#### `make prepare-all`
Processa **TODOS os produtos** do `list_to_prepare.json` em lote, perguntando categoria para cada um.

---

### 📤 **PUBLICAÇÃO NO SITE**

#### `make stage`
Publica produtos preparados no site:
1. Lê JSONs de `staging/`
2. Faz upload de imagens para MinIO
3. Adiciona produtos ao banco de dados PostgreSQL
4. Marca como publicados

**Script executado:** `scripts/stage_products.py`

---

### 📸 **INSTAGRAM**

#### `make instagram-post`
Publica automaticamente no Instagram usando agentes LLM.

#### `make instagram-test`
Testa publicação sem postar de verdade (modo simulação).

#### `make instagram-status`
Verifica status do sistema Instagram.

---

### 🐳 **DOCKER & DESENVOLVIMENTO**

#### `make up`
Sobe ambiente de desenvolvimento:
- Container `site` (Flask)
- Container `postgres-dev` (PostgreSQL)
- Container `minio` (Object Storage)
- Container `qdrant` (Vector DB)

#### `make down`
Para e remove todos os containers + volumes.

#### `make restart-site`
Reinicia apenas o serviço `site`.

#### `make logs-site`
Mostra logs em tempo real do container `site`.

#### `make shell-site`
Abre shell bash dentro do container `site`.

---

### 🔑 **OAUTH MERCADO LIVRE**

#### `make serve-ngrok`
Inicia túnel ngrok para testes de OAuth localmente.

#### `make oauth-url`
Gera URL de autenticação OAuth do Mercado Livre.

#### `make check-tokens`
Verifica tokens OAuth salvos.

#### `make test-api`
Testa chamada à API do ML com token OAuth.

---

### 🚀 **PRODUÇÃO**

#### `make prd-up`
Sobe ambiente de produção.

#### `make prd-down`
Para ambiente de produção.

---

### 🧹 **LIMPEZA**

#### `make prune`
Remove containers, volumes e imagens não utilizadas.

#### `make clear-minio`
Remove TODAS as imagens do MinIO (com confirmação).

---

## 📁 Arquivos Importantes

| Arquivo | Descrição |
|---------|-----------|
| `Makefile` | Define todos os comandos make |
| `docker-compose.yaml` | Configuração base Docker |
| `docker-compose.dev.yaml` | Override para desenvolvimento |
| `docker-compose.prd.yaml` | Override para produção |
| `.env` | Variáveis de ambiente (dev) |
| `.env.prd` | Variáveis de ambiente (produção) |
| `README.md` | Documentação do projeto |

---

## 🔗 Links Úteis

- [MAPA_PASTAS.md](MAPA_PASTAS.md) - Visão geral de todas as pastas
- [services/site/scripts/DefineMe.md](services/site/scripts/DefineMe.md) - Documentação dos scripts
- [services/site/docs/](services/site/docs/) - Documentação técnica completa
