# ✅ Checklist de Pastas - DefineMe.md

## 📋 Status da Documentação

### ✅ Nível 0 - Raiz
- [x] `/` - **DefineMe.md criado** ✅
  - Documenta: `prepare-products`, `stage`, `up`, `down`, `instagram-post`, etc.
  - **DESTAQUE:** Documentação completa do `make prepare-products` com evidências ⭐

### 📁 Nível 1 - Principais

- [ ] `services/` - DefineMe.md pendente
  - Container de todos os serviços do projeto

- [ ] `shared/` - DefineMe.md pendente
  - Código compartilhado (containers LLM, routers)

- [ ] `tests/` - DefineMe.md pendente
  - Testes automatizados (`test-unit`, `test-integration`)

- [ ] `uploads/` - DefineMe.md pendente
  - Uploads persistentes de produtos

- [ ] `vector_db/` - DefineMe.md pendente
  - Banco vetorial Qdrant (RAG, embeddings)

- [ ] `documentação de integrações/` - DefineMe.md pendente
  - Documentação de APIs externas (ML, Shopee)

### 📁 Nível 2 - Services/Site

- [ ] `services/site/` - DefineMe.md pendente
  - Aplicação Flask principal

- [x] `services/site/agents/` - **DefineMe.md criado** ✅
  - Agentes LLM (Instagram, Produtos, Enricher)
  - Sistema multi-agente com LangGraph

- [ ] `services/site/config/` - DefineMe.md pendente
  - Configurações (ml_tokens.json, OAuth)

- [ ] `services/site/docs/` - DefineMe.md pendente
  - Documentação técnica interna

- [ ] `services/site/models/` - DefineMe.md pendente
  - Modelos SQLAlchemy (Product, base, etc)

- [ ] `services/site/routes/` - DefineMe.md pendente
  - Rotas da API Flask

- [x] `services/site/scripts/` - **DefineMe.md criado** ✅
  - Scripts de automação (prepare, stage, migrate)
  - Documentação completa de todos os scripts

- [ ] `services/site/services/` - DefineMe.md pendente
  - Serviços de negócio

- [x] `services/site/staging/` - **DefineMe.md criado** ✅
  - JSONs de produtos preparados
  - Estrutura de categorias e fluxo

- [x] `services/site/list_to_prepare_and_stage/` - **DefineMe.md criado** ✅
  - Fila de produtos para processar
  - Formato do list_to_prepare.json

- [ ] `services/site/publish_ready/` - DefineMe.md pendente
  - Imagens prontas para Instagram

- [ ] `services/site/insta_staging/` - DefineMe.md pendente
  - Staging de posts do Instagram

- [ ] `services/site/static/` - DefineMe.md pendente
  - Assets estáticos (CSS, JS, imagens)

- [ ] `services/site/templates/` - DefineMe.md pendente
  - Templates HTML Jinja2

- [ ] `services/site/uploads/` - DefineMe.md pendente
  - Uploads temporários

### 📁 Nível 3 - Tests

- [ ] `tests/unit/` - DefineMe.md pendente
  - Testes unitários

---

## 🎯 Prioridades de Documentação

### 🔥 Alta Prioridade (próximos)
1. ✅ `/` (raiz) - **COMPLETO**
2. `services/site/scripts/` - Scripts mais usados
3. `services/site/staging/` - Fluxo de produtos
4. `services/site/agents/` - Sistema de LLM

### 🔶 Média Prioridade
5. `services/site/routes/` - APIs
6. `services/site/models/` - Banco de dados
7. `services/site/` - App principal
8. `shared/` - Componentes compartilhados

### 🔵 Baixa Prioridade
9. `services/site/static/` - Frontend
10. `services/site/templates/` - UI
11. `tests/` - Testes
12. Demais pastas auxiliares

---

## 📊 Estatísticas

- **Total de pastas**: 22
- **Documentadas**: 5 ✅
- **Pendentes**: 17 ⏳
- **Progresso**: 23% (5/22)

---

## 🎯 Conquistas

### ✅ Documentação Completa Criada

1. **[DefineMe.md](../DefineMe.md)** - Raiz do Projeto
   - Todos os comandos make
   - **FOCO ESPECIAL:** `make prepare-products` com evidências completas
   - Fluxos detalhados com diagramas

2. **[services/site/scripts/DefineMe.md](../services/site/scripts/DefineMe.md)** - Scripts
   - Todos os 12 scripts documentados
   - Fluxo entre scripts
   - Exemplos de uso

3. **[services/site/staging/DefineMe.md](../services/site/staging/DefineMe.md)** - Staging
   - Estrutura de categorias
   - Formato de JSONs
   - Ciclo de vida do produto

4. **[services/site/agents/DefineMe.md](../services/site/agents/DefineMe.md)** - Agentes LLM
   - Sistema multi-agente
   - LangGraph workflow
   - Exemplos de execução real

5. **[services/site/list_to_prepare_and_stage/DefineMe.md](../services/site/list_to_prepare_and_stage/DefineMe.md)** - Fila
   - Como usar list_to_prepare.json
   - Processamento em lote

### 📋 Documentos de Apoio

- **[MAPA_PASTAS.md](../MAPA_PASTAS.md)** - Tabela de navegação completa
- **[CHECKLIST_PASTAS.md](../CHECKLIST_PASTAS.md)** - Este arquivo (status)
- **[README_DEFINEME.md](../README_DEFINEME.md)** - Guia geral do sistema

---

## 🚀 Comandos Make por Pasta

### `/` (Raiz)
```bash
make prepare-products  # Prepara produtos
make stage            # Publica no site
make up               # Sobe containers
make instagram-post   # Posta no Instagram
```

### `services/site/scripts/`
```bash
make run-py script=scripts/generate_staging_json.py
make run-py script=scripts/stage_products.py
make run-py script=scripts/api_prepare_ml.py
```

### `services/site/staging/`
- Recebe JSONs de `prepare-products`
- Lidos por `stage`

### `services/site/list_to_prepare_and_stage/`
- `list_to_prepare.json` - Fila de URLs

---

## 📝 Template DefineMe.md

Cada DefineMe.md deve conter:

```markdown
# 📖 DefineMe - [Nome da Pasta]

## 🎯 Propósito da Pasta
[Descrição breve]

## 🚀 Comandos Make Relacionados
[Lista de comandos]

## 📁 Estrutura Interna
[Arquivos principais]

## 🔄 Fluxo de Dados
[Como interage com outras partes]

## 📊 Exemplos
[Evidências de uso]

## 🔗 Links Relacionados
[Outras documentações]
```
