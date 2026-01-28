# 📚 README - Sistema de Documentação DefineMe

## 🎯 O que é o Sistema DefineMe?

Este é um **sistema de documentação estruturado** que mapeia todas as pastas do projeto V_M e documenta os comandos `make` relacionados a cada uma delas. 

Cada pasta importante do projeto possui um arquivo `DefineMe.md` que explica:
- 🎯 Propósito da pasta
- 🚀 Comandos make relacionados
- 📂 Estrutura de arquivos
- 🔄 Fluxo de dados
- 📊 Exemplos práticos
- 🔗 Links para outras documentações

---

## 📋 Documentos Principais

### 🗺️ [MAPA_PASTAS.md](MAPA_PASTAS.md)
**Visão geral de todo o projeto em forma de tabela**

Mostra:
- Hierarquia completa de pastas
- Links para todos os DefineMe.md
- Comandos make principais
- Fluxo de comandos

---

### ✅ [CHECKLIST_PASTAS.md](CHECKLIST_PASTAS.md)
**Status da documentação**

Rastreia:
- Quais pastas já foram documentadas ✅
- Quais estão pendentes ⏳
- Prioridades de documentação
- Progresso geral

---

### 📖 DefineMe.md Criados

#### ✅ Nível 0 - Raiz

1. **[DefineMe.md](DefineMe.md)** - Raiz do Projeto
   - Todos os comandos make gerais
   - **FOCO ESPECIAL:** `make prepare-products`
   - Documentação completa com evidências
   - Fluxos detalhados

#### ✅ Nível 2 - Funcionalidades Principais

2. **[services/site/scripts/DefineMe.md](services/site/scripts/DefineMe.md)** - Scripts de Automação
   - Todos os scripts Python
   - Como cada um funciona
   - Comandos que os executam
   - Fluxo entre scripts

3. **[services/site/staging/DefineMe.md](services/site/staging/DefineMe.md)** - Área de Staging
   - Organização de produtos preparados
   - Estrutura de categorias
   - Formato dos JSONs
   - Ciclo de vida do produto

4. **[services/site/agents/DefineMe.md](services/site/agents/DefineMe.md)** - Agentes LLM
   - Sistema multi-agente Instagram
   - Orquestrador LangGraph
   - Fluxo de publicação automática
   - Exemplos de execução

5. **[services/site/list_to_prepare_and_stage/DefineMe.md](services/site/list_to_prepare_and_stage/DefineMe.md)** - Fila de Produtos
   - Como adicionar produtos à fila
   - Formato do list_to_prepare.json
   - Processamento em lote

---

## 🚀 Como Usar Este Sistema

### 1. **Entender a estrutura geral**
```bash
# Comece pelo mapa de pastas
cat MAPA_PASTAS.md
```

### 2. **Encontrar o comando que precisa**
```bash
# Veja o DefineMe da raiz
cat DefineMe.md

# Ou use o make help
make help
```

### 3. **Entender um comando específico**
```bash
# Exemplo: entender o prepare-products
# Leia a seção dele no DefineMe.md da raiz
```

### 4. **Aprofundar em uma área**
```bash
# Quer entender os scripts?
cat services/site/scripts/DefineMe.md

# Quer entender o Instagram?
cat services/site/agents/DefineMe.md
```

---

## 📊 Comando `make prepare-products` - Documentação Completa

### 🎯 O que faz?

O `make prepare-products` é o **comando principal para adicionar produtos ao sistema**. Ele:

1. Lê lista de URLs de `list_to_prepare.json`
2. Faz scraping de cada produto
3. Baixa todas as imagens
4. Solicita categoria ao usuário
5. Gera JSONs organizados em `staging/`

### 📝 Evidências de Funcionamento

#### Console Output Real:
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
📦 Título: Robô Varredora Aspirador De Pó 1200pa...
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

✅ Staging salvo em: staging/casa-decoracao/sala/robo-varredora_20260128.json
🏷️  Tag: CD
🔖 Subcategoria: sala
📦 Plataforma: mercadolivre
🔗 External ID: MLB3766026070
✅ Disponível: Sim

============================================================
✅ Processo concluído!
📁 1 arquivo(s) gerado(s):
   - staging/casa-decoracao/sala/robo-varredora_20260128.json
============================================================
```

#### Arquivo JSON Gerado:
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
  "criado_em": "20260122_214506",
  "via_webhook": false
}
```

#### Imagens Baixadas:
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

### 🔄 Fluxo Completo

```
list_to_prepare.json → make prepare-products → staging/[categoria]/[produto].json
                                             → uploads/[produto]/images/
```

---

## 🎓 Fluxo Completo do Sistema

### Da URL ao Instagram

```
1️⃣ PREPARAÇÃO
   URL → list_to_prepare.json
   ↓
   make prepare-products
   ↓
   staging/casa-decoracao/sala/produto.json
   + uploads/produto/images/

2️⃣ PUBLICAÇÃO NO SITE
   make stage
   ↓
   • Upload MinIO
   • Insert PostgreSQL
   ↓
   Produto visível no site

3️⃣ PUBLICAÇÃO NO INSTAGRAM
   make instagram-post
   ↓
   • Agente Decisor (escolhe produto)
   • Agente Enriquecedor (melhora legenda)
   • Agente Postador (publica)
   ↓
   Post no Instagram
```

---

## 📚 Referências Rápidas

### Comandos Mais Usados

```bash
# Preparar produtos
make prepare-products

# Publicar no site
make stage

# Postar no Instagram
make instagram-post

# Subir ambiente
make up

# Ver logs
make logs-site

# Ajuda completa
make help
```

### Arquivos Importantes

| Arquivo | Localização | Para que serve |
|---------|-------------|----------------|
| `list_to_prepare.json` | `services/site/list_to_prepare_and_stage/` | Fila de URLs |
| `staging/*.json` | `services/site/staging/[categoria]/` | Produtos preparados |
| `ml_tokens.json` | `services/site/config/` | Tokens OAuth ML |
| `Makefile` | Raiz | Define todos os comandos |

---

## 🔍 Navegação

### Por Funcionalidade

- **Preparar Produtos:** [DefineMe Raiz](DefineMe.md) + [DefineMe Scripts](services/site/scripts/DefineMe.md)
- **Staging:** [DefineMe Staging](services/site/staging/DefineMe.md)
- **Instagram:** [DefineMe Agents](services/site/agents/DefineMe.md)
- **Visão Geral:** [MAPA_PASTAS.md](MAPA_PASTAS.md)

### Por Pasta

Use o [MAPA_PASTAS.md](MAPA_PASTAS.md) como índice principal.

---

## ✅ Status da Documentação

- **Documentos criados:** 7
- **Pastas documentadas:** 5
- **Comando em destaque:** `make prepare-products` ✅
- **Evidências incluídas:** Sim ✅
- **Exemplos práticos:** Sim ✅

---

## 🎯 Próximos Passos

Para expandir a documentação, consulte [CHECKLIST_PASTAS.md](CHECKLIST_PASTAS.md) e veja quais pastas ainda precisam de DefineMe.md.

---

**Desenvolvido para o projeto V_M - Sistema de E-commerce Automatizado**
