# 🚀 Quick Start - Instagram Auto Post

## Setup Rápido (5 minutos)

```bash
# 1. Configure credenciais
./setup_instagram.sh

# 2. Suba o ambiente
make up

# 3. Teste o sistema
make instagram-test-system

# 4. Teste uma postagem (simulação)
make instagram-test

# 5. Poste de verdade
make instagram-post
```

## Comandos Principais

```bash
make instagram-post          # Posta automaticamente no Instagram
make instagram-test          # Testa sem postar de verdade
make instagram-status        # Verifica status do sistema
make instagram-history       # Histórico de posts
make instagram-test-system   # Testa todos os componentes
make stage-and-post          # ML + Instagram em um comando
```

## Estrutura dos Agentes

```
agents/
├── __init__.py                    # BaseAgent (classe abstrata)
├── product_decision_agent.py     # Seleciona produto
├── product_enricher_agent.py     # Enriquece dados
├── instagram_poster_agent.py     # Posta no Instagram
└── instagram_orchestrator.py     # Orquestra tudo (LangGraph)
```

## API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/instagram/post` | POST | Post com controle total |
| `/instagram/post/auto` | POST | Post automático simplificado |
| `/instagram/status` | GET | Status do sistema |
| `/instagram/history` | GET | Histórico de posts |
| `/instagram/workflow` | GET | Diagrama do workflow |
| `/instagram/test/image` | POST | Testa geração de imagem |

## Exemplo de Uso via API

```bash
# Post automático (simulação)
curl -X POST "http://localhost:5000/instagram/post/auto?simulate=true"

# Post com filtros
curl -X POST http://localhost:5000/instagram/post \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {"tag": "geral", "min_price": 50},
    "simulate": false
  }'

# Status
curl http://localhost:5000/instagram/status | jq .
```

## Variáveis de Ambiente Necessárias

```bash
OPENAI_API_KEY=sk-...          # Para agentes LangChain
INSTAGRAM_USERNAME=...          # Usuário Instagram
INSTAGRAM_PASSWORD=...          # Senha Instagram
REDIS_URL=redis://redis:6379   # Cache e memória
```

## Fluxo de Dados

```
Staging JSON → Agente Decisor → Agente Enriquecedor → Agente Postador → Instagram
      ↓              ↓                    ↓                   ↓
   Redis Cache   LLM (GPT)           LLM (GPT)        Instagram API
```

## Troubleshooting Rápido

```bash
# Redis não conecta?
docker ps | grep redis
make down && make up

# OpenAI API Key inválida?
echo $OPENAI_API_KEY

# Instagram não posta?
docker logs site | grep -i instagram

# Teste componente por componente
make instagram-test-system
```

## Documentação Completa

Ver [INSTAGRAM_AUTO_POST.md](INSTAGRAM_AUTO_POST.md) para:
- Arquitetura detalhada
- Casos de uso avançados
- Troubleshooting completo
- Melhores práticas

---

**Meu rei, sistema pronto! 👑📸**
