# 🚀 Quick Start - Sistema de Recomendações Unificado

## 📦 Estrutura Consolidada

Todo o sistema foi consolidado em:

```
services/recommendations-system/
```

**Uma única pasta = Uma única imagem Docker** ✅

## ⚡ Comandos Rápidos

### 1. Build local

```bash
make recs-unified-build
```

Ou diretamente:

```bash
cd services/recommendations-system
./build.sh
```

### 2. Build e Push para Registry

```bash
# Docker Hub
make recs-unified-push DOCKER_USER=seuusuario

# Registry privado
make recs-unified-push DOCKER_USER=team DOCKER_REGISTRY=registry.example.com
```

### 3. Testar localmente

```bash
make recs-unified-test
```

Isso vai:
- Rodar a imagem localmente
- Expor todas as portas (8000-8005)
- Fazer health check automático

Para parar:

```bash
make recs-unified-stop-test
```

### 4. Ver documentação

```bash
make recs-unified-docs
```

Ou abrir diretamente:

```bash
cat services/recommendations-system/README.md
```

## 🎯 Integração no Site

### Adicionar ao docker-compose.yaml do site:

```yaml
services:
  recommendations:
    image: seuusuario/recommendations-system:latest
    ports:
      - "8000:8000"
    environment:
      SERVICE: all
      DATABASE_URL: postgresql://user:password@postgres:5432/recommendations_db
      REDIS_URL: redis://redis:6379/0
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      INSTAGRAM_APP_ID: ${INSTAGRAM_APP_ID}
      INSTAGRAM_APP_SECRET: ${INSTAGRAM_APP_SECRET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
      - kafka
```

### Usar no código Python:

```python
import httpx

async def get_recommendations(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://recommendations:8000/recommendations",
            params={"user_id": user_id, "limit": 10}
        )
        return response.json()
```

## 📋 Checklist

- [ ] Configurar credenciais no `.env`:
  ```env
  INSTAGRAM_APP_ID=seu_app_id
  INSTAGRAM_APP_SECRET=seu_secret
  OPENAI_API_KEY=sua_chave
  ```

- [ ] Build da imagem:
  ```bash
  make recs-unified-build
  ```

- [ ] Testar localmente:
  ```bash
  make recs-unified-test
  curl http://localhost:8000/health
  ```

- [ ] Push para registry:
  ```bash
  make recs-unified-push DOCKER_USER=seuusuario
  ```

- [ ] Integrar no docker-compose do site

- [ ] Atualizar código do site para usar API

- [ ] Deploy! 🚀

## 🌐 Endpoints Principais

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Health check |
| `/docs` | GET | Documentação interativa |
| `/auth/instagram` | POST | Autenticar usuário |
| `/ingest` | POST | Coletar dados do Instagram |
| `/track` | POST | Rastrear evento |
| `/recommendations` | GET | Obter recomendações |

## 🔗 Arquivos Importantes

- **README.md** - Documentação completa
- **Dockerfile** - Imagem Docker única
- **build.sh** - Script de build e push
- **docker-compose.site-integration.yaml** - Exemplo de integração
- **main.py** - Entry point que inicia todos os serviços

## 💡 Dicas

### Rodar apenas um serviço específico:

```bash
docker run -e SERVICE=api -p 8000:8000 recommendations-system:latest
```

Serviços disponíveis: `all`, `api`, `auth`, `ingest`, `tracking`, `recommendations`, `profile_builder`

### Ver logs:

```bash
docker logs -f <container_name>
```

### Debug:

```bash
docker exec -it <container_name> bash
```

## 🎯 Fluxo Completo

```mermaid
graph LR
    A[Build] --> B[Test Local]
    B --> C[Push Registry]
    C --> D[Pull no Site]
    D --> E[Deploy]
    E --> F[Usar API]
```

1. **Build** - `make recs-unified-build`
2. **Test** - `make recs-unified-test`
3. **Push** - `make recs-unified-push DOCKER_USER=xxx`
4. **Pull** - Site baixa do registry
5. **Deploy** - `docker-compose up`
6. **Use** - Chamar endpoints via HTTP

---

**Pronto para produção! 🚀**

Qualquer dúvida, consulte:
- [README completo](services/recommendations-system/README.md)
- [Exemplo de integração](services/recommendations-system/docker-compose.site-integration.yaml)
- [Documentação da API](http://localhost:8000/docs)
