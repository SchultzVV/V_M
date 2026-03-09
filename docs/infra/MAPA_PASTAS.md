# 🗺️ Mapa de Pastas do Projeto V_M

## 📋 Tabela de Estrutura de Pastas e Documentação

| Nível | Pasta | DefineMe.md | Comandos Make Principais | Descrição |
|-------|-------|-------------|--------------------------|-----------|
| 0 | `/` (raiz) | [DefineMe.md](DefineMe.md) | `prepare-products`, `stage`, `up`, `down` | Raiz do projeto - Orquestração geral |
| 1 | `services/` | [services/DefineMe.md](services/DefineMe.md) | - | Container de todos os serviços |
| 2 | `services/site/` | [services/site/DefineMe.md](services/site/DefineMe.md) | `run-site-db` | Aplicação web principal (Flask) |
| 3 | `services/site/agents/` | [services/site/agents/DefineMe.md](services/site/agents/DefineMe.md) | - | Agentes LLM (Instagram, Produtos) |
| 3 | `services/site/config/` | [services/site/config/DefineMe.md](services/site/config/DefineMe.md) | - | Arquivos de configuração (tokens OAuth) |
| 3 | `services/site/docs/` | [services/site/docs/DefineMe.md](services/site/docs/DefineMe.md) | - | Documentação técnica interna |
| 3 | `services/site/models/` | [services/site/models/DefineMe.md](services/site/models/DefineMe.md) | - | Modelos de dados (SQLAlchemy) |
| 3 | `services/site/routes/` | [services/site/routes/DefineMe.md](services/site/routes/DefineMe.md) | - | Rotas da API Flask |
| 3 | `services/site/scripts/` | [services/site/scripts/DefineMe.md](services/site/scripts/DefineMe.md) | `prepare-products`, `stage`, `prepare-auto` | Scripts de automação |
| 3 | `services/site/services/` | [services/site/services/DefineMe.md](services/site/services/DefineMe.md) | - | Serviços de negócio |
| 3 | `services/site/staging/` | [services/site/staging/DefineMe.md](services/site/staging/DefineMe.md) | `stage` | Produtos preparados (JSONs) |
| 3 | `services/site/list_to_prepare_and_stage/` | [services/site/list_to_prepare_and_stage/DefineMe.md](services/site/list_to_prepare_and_stage/DefineMe.md) | `prepare-products`, `prepare-all` | Fila de produtos a processar |
| 3 | `services/site/publish_ready/` | [services/site/publish_ready/DefineMe.md](services/site/publish_ready/DefineMe.md) | `prepare-publish` | Imagens prontas para Instagram |
| 3 | `services/site/insta_staging/` | [services/site/insta_staging/DefineMe.md](services/site/insta_staging/DefineMe.md) | `instagram-post` | Staging de posts do Instagram |
| 3 | `services/site/static/` | [services/site/static/DefineMe.md](services/site/static/DefineMe.md) | - | Arquivos estáticos (CSS, JS, imgs) |
| 3 | `services/site/templates/` | [services/site/templates/DefineMe.md](services/site/templates/DefineMe.md) | - | Templates HTML (Jinja2) |
| 3 | `services/site/uploads/` | [services/site/uploads/DefineMe.md](services/site/uploads/DefineMe.md) | - | Uploads temporários de usuários |
| 1 | `shared/` | [shared/DefineMe.md](shared/DefineMe.md) | - | Código compartilhado (containers LLM) |
| 1 | `tests/` | [tests/DefineMe.md](tests/DefineMe.md) | `test-unit`, `test-integration` | Testes automatizados |
| 2 | `tests/unit/` | [tests/unit/DefineMe.md](tests/unit/DefineMe.md) | `test-unit` | Testes unitários |
| 1 | `uploads/` | [uploads/DefineMe.md](uploads/DefineMe.md) | - | Uploads persistentes |
| 1 | `vector_db/` | [vector_db/DefineMe.md](vector_db/DefineMe.md) | - | Banco vetorial (Qdrant) |
| 1 | `documentação de integrações/` | [documentação de integrações/DefineMe.md](documentação%20de%20integrações/DefineMe.md) | - | Docs de integrações externas |

## 🎯 Legenda

- **Nível**: Profundidade da pasta na hierarquia (0 = raiz)
- **Pasta**: Caminho relativo da pasta
- **DefineMe.md**: Link para documentação específica da pasta
- **Comandos Make**: Comandos principais executados a partir desta pasta
- **Descrição**: Breve descrição do propósito

## 📚 Fluxo de Comandos Principais

### 1️⃣ Preparação de Produtos (Mercado Livre)
```bash
make prepare-products  # Manual: gera JSON em staging/
make prepare-auto URL=<url>  # Scraping: extrai de URL ML
make api-prepare-product URL=<url>  # API Oficial: melhor qualidade
```

### 2️⃣ Publicação no Site
```bash
make stage  # Upload MinIO + Adiciona ao banco de dados
```

### 3️⃣ Publicação no Instagram
```bash
make instagram-post  # Publica automaticamente
make instagram-test  # Modo simulação
```

### 4️⃣ Desenvolvimento
```bash
make up  # Sobe ambiente Docker
make down  # Para containers
make logs-site  # Ver logs em tempo real
```

## 🔗 Navegação Rápida

- [DefineMe Raiz - Comandos Gerais](DefineMe.md)
- [DefineMe Scripts - Detalhes de Automação](services/site/scripts/DefineMe.md)
- [DefineMe Staging - Gestão de Produtos](services/site/staging/DefineMe.md)
