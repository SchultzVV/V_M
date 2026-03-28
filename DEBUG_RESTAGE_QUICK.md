# 🧪 Teste Rápido: Debug do Restage + Nginx + React

## ⚡ Começa aqui (10 minutos)

Execute isto em sequência. Copie e cole no terminal.

---

## 1️⃣ Verifica se Flask está UP

```bash
# Testa Flask localmente (dentro do container)
docker exec -it site curl -k https://localhost:5000/api/products 2>&1 | head -20

# ✅ Se retorna JSON: [[...]] ou [{...}]
# ❌ Se retorna erro de conexão: Flask não está rodando → execute:
make restart-site
sleep 3
```

---

## 2️⃣ Verifica dados no Banco

```bash
# Conecta ao PostgreSQL
docker exec -it postgres-dev psql -U user -d produtos_db -c "
SELECT id, title, price FROM product LIMIT 3;
"

# ✅ Se retorna tabela com dados: Banco tem produtos
# ❌ Se retorna "(0 rows)": Banco vazio → execute:
make restage
```

---

## 3️⃣ Verifica MinIO (imagens)

```bash
# Testa acesso MinIO
docker exec -it site curl -s http://minio:9000/minio/bootstrap.html | grep -q "MinIO" && echo "✅ MinIO OK" || echo "❌ MinIO DOWN"

# Lista buckets
docker exec -it site python3 -c "
from minio import Minio
client = Minio('minio:9000', 'minio', 'minio123', secure=False)
buckets = [b.name for b in client.list_buckets()]
print('✅ Buckets:', buckets)
"
```

---

## 4️⃣ Verifica Nginx está UP

```bash
# Testa se Nginx está respondendo
docker ps | grep nginx-react && echo "✅ Nginx container running" || echo "❌ Nginx container down"

# Testa HTTPS
docker exec nginx-react curl -k https://localhost/ 2>&1 | head -5

# ❌ Se erro "Connection refused": Nginx não está up → execute:
docker compose -f docker-compose.yaml -f docker-compose.react.yaml up -d nginx
sleep 3
```

---

## 5️⃣ Verifica Proxy Nginx → Flask

```bash
# Testa se Nginx consegue fazer proxy para Flask
docker exec nginx-react curl -k https://localhost/api/products 2>&1 | head -20

# ✅ Se retorna JSON: Proxy está OK
# ❌ Se retorna 502/504: Nginx não consegue alcançar Flask
  # Tenta resolver "site"
  docker exec nginx-react nslookup site
  # Se falha, significa network problem
```

---

## 6️⃣ Verifica React Build

```bash
# Verifica se frontend foi compilado
ls -la frontend/dist/ | head -10

# ✅ Se tem index.html e js/, css/ folders: Build EXISTS
# ❌ Se vazio ou não existe: Precisa compilar:
cd frontend && npm run build

# Verifica se Nginx está servindo o build
docker exec nginx-react ls -la /app/dist/ | head -5

# ❌ Se vazio: Volume não está mapeado → reinicia:
docker compose -f docker-compose.yaml -f docker-compose.react.yaml down
docker compose -f docker-compose.yaml -f docker-compose.react.yaml up -d
```

---

## 7️⃣ Testa Full Stack via Nginx

```bash
# Simula requisição React
curl -k https://localhost/api/products \
  -H "Accept: application/json" 2>&1 | jq '.[0]' 2>/dev/null

# ✅ Se retorna JSON com produto (title, price, images):
# SUCESSO! Fluxo está OK

# ❌ Se retorna erro ou vazio:
# Vai para diagnostico abaixo
```

---

## 8️⃣ Testa no Navegador

**Abra em seu navegador**:
```
https://localhost
```

### ❌ Se não carrega (connection refused):
```bash
# Verifica se Nginx está respondendo
docker exec nginx-react curl -k https://localhost/ 2>&1

# Se falha, reinicia Nginx:
docker compose -f docker-compose.react.yaml restart nginx
sleep 2
```

### ✅ Se carrega pagina branca mas sem produtos:
**Abra DevTools (F12) → Console:**
```javascript
// Copia isto no console e executa:
fetch('/api/products')
  .then(r => r.json())
  .then(d => {
    console.log('API Response:', d);
    console.log('Count:', d.length);
  })
  .catch(e => console.error('ERROR:', e));
```

**Procura pela resposta**:
- ✅ `API Response: [{...}, {...}]` = Dados chegaram, React problemático
- ❌ `API Response: []` = Banco vazio → `make restage`
- ❌ `ERROR: ...` = Nginx/Flask problemático → volta pro step 5

---

## 📊 Diagrama Rápido de Debug

```
[1] docker exec -it site curl -k https://localhost:5000/api/products
                         ↓
                    Flask OK?
                   /          \
                ✅            ❌ → make restart-site
               /                \
            [2] Banco tem dados?  
              /                \
            ✅                ❌ → make restage
           /                    \
        [3] MinIO OK?
         /              \
       ✅              ❌ → check logs
      /                \
   [4] Nginx UP?
    /              \
  ✅             ❌ → docker compose up -d nginx
 /                \
[5] Proxy OK? (curl https://localhost/api/products)
 /                \
✅              ❌ → docker network ls / inspect
                  \→ nslookup site inside nginx
				   \→ Restart nginx
[6] React Build?
 /               \
✅             ❌ → npm run build
                \→ docker compose up -d
[7] Browser teste
 /             \
✅           ❌ → DevTools F12 → Network tab
              \→ Check CORS errors
              \→ Check HTTPS cert
```

---

## 🔴 SOLUÇÃO FINAL (Se tudo falhar)

```bash
# Nuclear reset - limpa tudo e recomeça

echo "🔄 Stopping everything...
make down

echo "🗑️  Removing volumes..."
docker volume prune -f

echo "🏗️  Rebuilding..."
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
sleep 20

echo "📦 Restaging products..."
make restage

echo "🌐 Starting Nginx + React..."
docker compose -f docker-compose.yaml -f docker-compose.react.yaml up -d

echo "✅ Done! Try: https://localhost"
```

**Depois aceda em**: `https://localhost` no navegador

---

## 💡 Quick Reference

| Comando | Verifica |
|---------|----------|
| `docker ps` | Containers rodando? |
| `make psql` | Dados no banco? |
| `curl -k https://localhost/api/products` | Nginx + Flask OK? |
| `curl -k https://localhost/` | React serve OK? |
| `ls -la frontend/dist/` | React foi compilado? |
| `docker compose -f docker-compose.react.yaml logs nginx` | Logs Nginx |
| `docker compose -f docker-compose.yaml logs site` | Logs Flask |

---

## 📝 Checklist Final

Antes de reportar problema, verifica isto:

- [ ] `docker ps` mostra: nginx-react, site, postgres-dev, minio, redis rodando
- [ ] `make psql` → `SELECT COUNT(*) FROM product;` → Retorna > 0
- [ ] `curl -k https://localhost/api/products` → Retorna JSON valido
- [ ] `curl -k https://localhost/` → Retorna HTML
- [ ] DevTools Console sem erros vermelho 🔴
- [ ] Browser Network tab → `/api/products` → Status 200
- [ ] React carrega e mostra pelo menos 1 produto

Se isso tudo passar ✅, o setup está correto!
