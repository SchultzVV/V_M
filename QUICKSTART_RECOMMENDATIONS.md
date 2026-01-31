# 🚀 Guia Rápido - Sistema de Recomendações

## Setup em 5 Minutos

### 1. Configurar Credenciais

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar com suas credenciais
nano .env
```

Preencher:
- `INSTAGRAM_APP_ID` - ID do app no Facebook/Instagram
- `INSTAGRAM_APP_SECRET` - Secret do app
- `OPENAI_API_KEY` - Chave da OpenAI

### 2. Iniciar Sistema

```bash
# Subir todos os serviços
make recs-up

# Aguardar ~30s para tudo ficar pronto
# Verificar saúde
make recs-health
```

### 3. Inicializar Banco

```bash
# Popular com produtos de teste
make recs-init-db
```

### 4. Testar API

Acessar: http://localhost:8000/docs

## Fluxo Completo de Teste

### Passo 1: Autenticar Usuário

```bash
# 1. Gerar URL de autorização do Instagram
# Abrir no navegador: https://api.instagram.com/oauth/authorize?client_id=YOUR_APP_ID&redirect_uri=http://localhost:8000/auth/callback&scope=user_profile,user_media&response_type=code

# 2. Após autorizar, você receberá um code
# 3. Trocar code por access_token
curl -X POST http://localhost:8000/auth/instagram \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SEU_CODE_AQUI",
    "redirect_uri": "http://localhost:8000/auth/callback"
  }'

# Response:
# {
#   "user_id": "uuid-123-456",
#   "instagram_id": "17841...",
#   "access_token": "IGQ...",
#   "expires_at": "2026-03-31T..."
# }
```

Salvar o `user_id` retornado!

### Passo 2: Coletar Dados do Instagram

```bash
# Substituir USER_ID pelo retornado acima
export USER_ID="uuid-123-456"

curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\"}"

# Response:
# {
#   "user_id": "uuid-123-456",
#   "profile": {
#     "username": "johndoe",
#     "bio": "Tech lover 💻 Coffee addict ☕",
#     "followers_count": 1234
#   },
#   "captions": [...]
# }
```

### Passo 3: Construir Perfil

```bash
# Executar Profile Builder em modo batch
make recs-profile-batch

# Logs:
# 🔨 Building profile for user: uuid-123-456
# ✅ Profile built for user uuid-123-456
```

### Passo 4: Rastrear Eventos

```bash
# Simular impressões
curl -X POST http://localhost:8000/track \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"event_type\": \"impression\",
    \"item_id\": \"prod-001\"
  }"

# Simular clique
curl -X POST http://localhost:8000/track \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"event_type\": \"click\",
    \"item_id\": \"prod-001\"
  }"

# Response:
# {
#   "event_id": "evt-789",
#   "status": "tracked"
# }
```

### Passo 5: Obter Recomendações

```bash
# Primeira chamada: gera recomendações (mais lento)
curl -s "http://localhost:8000/recommendations?user_id=$USER_ID&limit=5" | jq '.'

# Segunda chamada: usa cache (< 10ms)
curl -s "http://localhost:8000/recommendations?user_id=$USER_ID&limit=5" | jq '.'

# Response:
# {
#   "user_id": "uuid-123-456",
#   "items": [
#     {
#       "product_id": "prod-001",
#       "score": 0.87,
#       "reason": "Match 85% + 25% OFF",
#       "metadata": {
#         "title": "Fone de Ouvido Bluetooth",
#         "price": 299.90,
#         "discount": 25,
#         "category": "electronics"
#       }
#     },
#     ...
#   ],
#   "cache_hit": false,
#   "generated_at": "2026-01-31T..."
# }
```

## Comandos Úteis

### Logs
```bash
# Todos os serviços
make recs-logs

# Serviço específico
make recs-logs-gateway
make recs-logs-auth
make recs-logs-recommendations
```

### Banco de Dados
```bash
# Acessar PostgreSQL
make recs-psql

# Ver usuários
SELECT id, instagram_id, consent_status FROM users;

# Ver perfis
SELECT user_id, last_updated FROM profiles;

# Ver eventos
SELECT user_id, event_type, item_id, timestamp FROM events ORDER BY timestamp DESC LIMIT 10;

# Sair
\q
```

### Redis
```bash
# Acessar Redis
make recs-redis

# Ver chaves de cache
KEYS rec:*

# Ver recomendação cacheada
GET rec:user:uuid-123-456

# Limpar cache
FLUSHDB

# Sair
exit
```

### Kafka
```bash
# Listar tópicos
make recs-kafka-topics

# Consumir eventos
make recs-kafka-consume
# Ctrl+C para parar
```

### Reiniciar Sistema
```bash
# Restart suave
make recs-restart

# Rebuild completo (limpa tudo)
make recs-rebuild
```

## Troubleshooting

### Serviço não inicia
```bash
# Ver logs de erro
make recs-logs

# Verificar se portas estão livres
lsof -i :8000
lsof -i :5432

# Rebuild
make recs-rebuild
```

### Erro de autenticação Instagram
```bash
# Verificar credenciais no .env
cat .env | grep INSTAGRAM

# Verificar no painel do Facebook:
# https://developers.facebook.com/apps/
```

### Erro de embedding (OpenAI)
```bash
# Verificar API key
cat .env | grep OPENAI

# Testar manualmente
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Recomendações sempre genéricas
```bash
# Verificar se perfil foi criado
make recs-psql
SELECT * FROM profiles WHERE user_id = 'uuid-123-456';

# Se vazio, executar profile builder
make recs-profile-batch
```

### Cache não funcionando
```bash
# Verificar Redis
make recs-redis
PING
# Deve retornar PONG

# Limpar cache e testar novamente
FLUSHDB
```

## Próximos Passos

1. ✅ Sistema funcionando localmente
2. 📊 Coletar mais dados de usuários
3. 🔨 Rodar Profile Builder regularmente (cron)
4. 📈 Analisar métricas (CTR, latência)
5. 🚀 Deploy em produção

## Links Úteis

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Kafka: localhost:9092

---

**Problemas?** Consulte [README_RECOMMENDATIONS.md](README_RECOMMENDATIONS.md) ou [ARQUITETURA_RECOMMENDATIONS.md](ARQUITETURA_RECOMMENDATIONS.md)
