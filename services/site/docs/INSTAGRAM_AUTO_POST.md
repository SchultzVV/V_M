# 📸 Sistema de Postagem Automática no Instagram

Sistema inteligente de postagem automática no Instagram usando **LangChain**, **LangGraph** e três agentes especializados, com cache semântico via Redis.

## 🎯 Visão Geral

O sistema é composto por três agentes principais que trabalham em conjunto:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE POSTAGEM INSTAGRAM                   │
└─────────────────────────────────────────────────────────────────┘

1️⃣  [Agente Decisor de Produto]
    ↓
    Analisa todos os produtos no staging/
    Seleciona o melhor produto baseado em:
    - Apelo visual potencial
    - Preço atraente
    - Relevância para audiência
    - Variedade (evita repetição)
    - Histórico de posts
    ↓
    
2️⃣  [Agente Enriquecedor]
    ↓
    Enriquece os dados do produto com LLM:
    - Gera legenda otimizada (100-200 chars)
    - Seleciona 8-12 hashtags relevantes
    - Cria call-to-action personalizado
    - Sugere composição visual
    ↓
    
3️⃣  [Agente Postador Instagram]
    ↓
    - Gera imagem promocional com preço
    - Posta automaticamente no Instagram
    - Registra no histórico (Redis)
    - Retorna URL do post
    ↓
    
✅ [POST NO INSTAGRAM]
```

## 🏗️ Arquitetura

### Agentes (seguem princípios SOLID)

#### 1. ProductDecisionAgent
- **Responsabilidade**: Selecionar o melhor produto para postar
- **Input**: Filtros opcionais (tag, preço, etc)
- **Output**: Produto selecionado com justificativa
- **Cache**: Produtos já postados (Redis)

#### 2. ProductEnricherAgent
- **Responsabilidade**: Enriquecer dados e gerar conteúdo
- **Input**: Produto selecionado
- **Output**: Dados enriquecidos (legenda, hashtags, CTA)
- **Cache**: Enriquecimentos por produto (TTL: 24h)

#### 3. InstagramPosterAgent
- **Responsabilidade**: Gerar imagem e postar
- **Input**: Produto enriquecido
- **Output**: URL do post e métricas
- **Integração**: Instagram API via `instagrapi`

### Orquestrador (LangGraph)

O `InstagramPostOrchestrator` gerencia o fluxo completo usando LangGraph:

```python
workflow = StateGraph(InstagramPostState)
workflow.add_node("decide_product", self._decide_product_node)
workflow.add_node("enrich_product", self._enrich_product_node)
workflow.add_node("post_instagram", self._post_instagram_node)

workflow.set_entry_point("decide_product")
workflow.add_edge("decide_product", "enrich_product")
workflow.add_edge("enrich_product", "post_instagram")
workflow.add_edge("post_instagram", END)
```

## 🚀 Configuração Rápida

### 1. Instalar Dependências

As dependências já estão no `requirements-prd.txt`:
- `langchain` + `langchain-openai` + `langgraph`
- `redis` + `hiredis`
- `Pillow` (geração de imagens)
- `instagrapi` (Instagram API)

### 2. Configurar Credenciais

Execute o script de setup:

```bash
chmod +x setup_instagram.sh
./setup_instagram.sh
```

Ou configure manualmente no `.env`:

```bash
# OpenAI (para agentes LangChain)
OPENAI_API_KEY=sk-your-key-here

# Instagram
INSTAGRAM_USERNAME=seu_usuario
INSTAGRAM_PASSWORD=sua_senha

# Redis
REDIS_URL=redis://redis:6379
```

### 3. Subir o Ambiente

```bash
make up
```

Isso subirá:
- Site (Flask app)
- PostgreSQL
- MinIO
- **Redis** (novo)

## 📝 Uso

### Comandos Make

```bash
# Teste sem postar de verdade
make instagram-test

# Posta automaticamente
make instagram-post

# Verifica status do sistema
make instagram-status

# Histórico de posts
make instagram-history

# Mostra workflow dos agentes
make instagram-workflow

# Fluxo completo: ML + Instagram
make stage-and-post
```

### API Endpoints

#### POST `/instagram/post`
Cria post com controle total:

```bash
curl -X POST http://localhost:5000/instagram/post \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "tag": "geral",
      "min_price": 50,
      "max_price": 500
    },
    "simulate": false,
    "post_type": "photo"
  }'
```

#### POST `/instagram/post/auto`
Postagem automática simplificada:

```bash
# Modo teste
curl -X POST "http://localhost:5000/instagram/post/auto?simulate=true"

# Modo produção
curl -X POST "http://localhost:5000/instagram/post/auto?simulate=false"
```

#### GET `/instagram/status`
Verifica saúde do sistema:

```bash
curl http://localhost:5000/instagram/status
```

Resposta:
```json
{
  "success": true,
  "status": "operational",
  "components": {
    "redis": "ok",
    "instagram": "configured",
    "openai": "configured",
    "agents": "loaded"
  },
  "staging": {
    "products_available": 15
  }
}
```

#### GET `/instagram/history`
Histórico de posts:

```bash
curl "http://localhost:5000/instagram/history?limit=10"
```

#### GET `/instagram/workflow`
Diagrama do workflow:

```bash
curl http://localhost:5000/instagram/workflow
```

#### POST `/instagram/test/image`
Testa geração de imagem:

```bash
curl -X POST http://localhost:5000/instagram/test/image \
  -H "Content-Type: application/json" \
  -d '{"product_id": "MLB19571567"}'
```

## 🎨 Geração de Imagens

O `InstagramImageGenerator` cria imagens promocionais com:

- **Dimensões**: 1080x1080 (square), 1080x1350 (portrait), 1080x566 (landscape)
- **Estilos**: modern, minimal, bold
- **Overlays**: Título, preço, CTA
- **Qualidade**: 95% JPEG otimizado

Exemplo de imagem gerada:

```
┌─────────────────────────────────────┐
│                                     │
│  🔥 Creatina Monohidratada 100%     │
│     Pura Pote 1kg - FTW             │
│                                     │
│         [IMAGEM DO PRODUTO]         │
│                                     │
│                                     │
│  ┌───────────────────────────────┐  │
│  │                               │  │
│  │      R$ 196,00                │  │
│  │                               │  │
│  │   🛒 LINK NA BIO              │  │
│  │                               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 🧠 Cache Semântico

O sistema usa Redis para cache inteligente:

### Cache de Enriquecimento
- **Key**: `cache:product_enricher:{md5_hash}`
- **TTL**: 24 horas
- **Objetivo**: Evita reprocessamento de produtos

### Histórico de Posts
- **Key**: `instagram:posted_products`
- **Tipo**: Lista (LPUSH)
- **Limite**: Últimos 500 produtos
- **Objetivo**: Evita posts duplicados

### Memória dos Agentes
- **Key**: `agent:{agent_name}:memory`
- **Tipo**: Lista (LPUSH)
- **Limite**: Últimas 100 interações
- **Objetivo**: Contexto e debugging

## 🔄 Integração com `make stage`

O sistema pode ser integrado ao fluxo existente:

### Opção 1: Manual
```bash
make stage          # Publica no Mercado Livre
make instagram-post # Posta no Instagram
```

### Opção 2: Automático
```bash
make stage-and-post # Faz tudo de uma vez
```

### Opção 3: Trigger Automático
Adicione ao final do `stage_products.py`:

```python
# No final do script
import requests

try:
    response = requests.post(
        'http://localhost:5000/instagram/post/auto?simulate=false',
        timeout=30
    )
    if response.ok:
        print("✅ Post no Instagram criado automaticamente")
    else:
        print("⚠️  Erro ao postar no Instagram")
except Exception as e:
    print(f"⚠️  Instagram post falhou: {e}")
```

## 📊 Monitoramento

### Verificar Logs dos Agentes

```bash
# Logs do Redis
docker logs redis

# Logs do site (inclui agentes)
docker logs -f site

# Verificar keys no Redis
docker exec -it redis redis-cli KEYS '*instagram*'
```

### Métricas Disponíveis

O sistema rastreia:
- ✅ Total de posts criados
- 📦 Produtos disponíveis no staging
- 🔁 Taxa de cache hit
- ⏱️ Tempo de execução por agente
- ❌ Erros e exceções

## 🔧 Troubleshooting

### Erro: "Credenciais Instagram não configuradas"
```bash
# Verifique o .env
cat .env | grep INSTAGRAM

# Execute o setup novamente
./setup_instagram.sh
```

### Erro: "Redis connection refused"
```bash
# Verifique se Redis está rodando
docker ps | grep redis

# Suba o Redis
make up
```

### Erro: "OpenAI API Key inválida"
```bash
# Teste a key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Erro ao gerar imagem: "Font not found"
O sistema usa fallback automático para fontes, mas você pode instalar fontes melhores:

```bash
# Ubuntu/Debian
docker exec -it site apt-get update
docker exec -it site apt-get install -y fonts-dejavu-core

# Recrie o container
make down && make up
```

## 🎯 Casos de Uso

### 1. Postagem Diária Automática

Crie um cron job:

```bash
# Crontab
0 10 * * * cd /home/v/Documents/V_M && make instagram-post
```

### 2. Postagem após Stage

Integre ao `Makefile`:

```makefile
stage: ## Publica no ML e Instagram
	@docker exec -it site python3 scripts/stage_products.py
	@$(MAKE) instagram-post
```

### 3. Testes A/B de Legendas

Use o agente enriquecedor:

```python
from agents.product_enricher_agent import ProductEnricherAgent
import redis

redis_client = redis.from_url('redis://redis:6379')
enricher = ProductEnricherAgent(redis_client)

# Gera 3 variações de legenda
alternatives = enricher.generate_alternative_captions(product, num_alternatives=3)
```

### 4. Postagem Agendada

```bash
curl -X POST http://localhost:5000/instagram/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": 1234567890,
    "filters": {"tag": "geral"}
  }'
```

## 🏆 Melhores Práticas

1. **Use `simulate=true` primeiro**: Sempre teste antes de postar
2. **Configure filtros**: Use tags e faixas de preço para controle
3. **Monitore o histórico**: Verifique posts anteriores regularmente
4. **Varie os estilos**: Alterne entre 'modern', 'minimal', 'bold'
5. **Respeite rate limits**: Instagram tem limites de posts/hora

## 📚 Referências

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Guide](https://langchain-ai.github.io/langgraph/)
- [Instagram API (instagrapi)](https://github.com/adw0rd/instagrapi)
- [Redis Python Client](https://redis-py.readthedocs.io/)

## 🤝 Contribuindo

Para adicionar novos agentes ao sistema:

1. Herde de `BaseAgent` em `agents/__init__.py`
2. Implemente o método `execute()`
3. Adicione ao `InstagramPostOrchestrator`
4. Crie endpoints na rota correspondente

Exemplo:

```python
from agents import BaseAgent

class MyNewAgent(BaseAgent):
    def execute(self, input_data):
        # Sua lógica aqui
        return {"success": True, "result": "..."}
```

---

**Desenvolvido com ❤️ usando LangChain, LangGraph e princípios SOLID**
