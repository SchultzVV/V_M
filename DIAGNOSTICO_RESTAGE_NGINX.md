# 🔍 Diagnóstico: "Restage não foi para o site do Nginx" 

## ❓ Qual é o problema?

Dev rodou `make restage` mas os dados atualizados não aparecem na UI React servida pelo Nginx.

---

## 📊 O que faz `make restage`?

### Comando
```bash
make restage
# Executa: docker exec -it site python3 scripts/stage_products.py --force
```

### Fluxo Detalhado (4 etapas)

#### 1️⃣ **Lê JSONs do diretório `staging/`**
- Local: `/services/site/staging/categoria/subcategoria/produto.json`
- Exemplo: `staging/eletrônicos/smartphones/iphone-15-pro.json`
- Ignora o arquivo `.processed` (por causa do `--force`)
- Processa **TODOS** os produtos, mesmo já processados

#### 2️⃣ **Faz upload das imagens para MinIO**
- O JSON tem o campo `"images_local": ["/uploads/produto/img1.jpg", "/uploads/produto/img2.jpg"]`
- Script cria bucket público automaticamente
- Upload: `/uploads/produto/img.jpg` → MinIO → URL pública
- URLs são adicionadas ao JSON: `"images": ["http://localhost:9000/produtos/img.jpg", ...]`

#### 3️⃣ **POST `/add_product` → Banco de Dados**
```python
payloadpayload = {
    "title": "iPhone 15 Pro",
    "price": "7999.90",
    "oldPrice": "9999.00",
    "images": ["http://minio:9000/...", ...],
    "link": "https://mercadolivre.com.br/...",
    "tag": "eletrônicos",        # ← Do JSON
    "subcategory": "smartphones",
    "disponivel": true,
    "external_id": "MLB-123456",
    "platform": "mercadolivre"
}

# POST para Flask
requests.post("https://localhost:5000/add_product", json=payload)
```

#### 4️⃣ **Flask salva no PostgreSQL**
```python
# services/site/routes/product_routes.py :: /add_product
product = save_product(
    title=data["title"],
    price=data["price"],             # ← Salvo no banco
    image=json.dumps(data["images"]), # ← Salvo no banco
    # ... resto dos campos
)
# INSERT INTO product (title, price, image, ...) VALUES (...)
```

### Resultado Final
```
staging/eletrônicos/smartphones/iphone-15-pro.json
    ↓ (upload imagens)
MinIO: http://minio:9000/produtos/iphone-15-pro/*
    ↓ (POST /add_product)
PostgreSQL: Product.id = uuid, Product.price = "7999.90", Product.image = "http://minio..."
```

---

## 🔗 Fluxo de Dados com Nginx + React

### Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│ DOCKER NETWORK: backend                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │  Browser        │  │  Nginx       │  │  Flask Backend   │     │
│  │  React App      │  │  Port 443    │  │  Port 5000       │     │
│  │  localhost:443  │  │  Reverse     │  │  /api/products   │     │
│  │                 │  │  Proxy       │  │  Queries DB      │     │
│  └────────┬────────┘  └──────┬───────┘  └────────┬─────────┘     │
│           │                   │                   │               │
│           │ GET / (index.html)│                   │               │
│           ├──────────────────>│                   │               │
│           │                   │                   │               │
│           │ <- /dist/index... │                   │               │
│           │<──────────────────│                   │               │
│           │                   │                   │               │
│           │ fetch('/api/products')                │               │
│           │ with token                            │               │
│           ├──────────────────>│                   │               │
│           │                   │ proxy_pass        │               │
│           │                   │ http://site:5000  │               │
│           │                   ├──────────────────>│               │
│           │                   │                   │               │
│           │                   │                   │ SELECT * FROM │
│           │                   │                   │ Product WHERE │
│           │                   │                   │ disponivel=1  │
│           │                   │                   │               │
│           │                   │ [{"id":"...",     │               │
│           │                   │   "title":"...",  │               │
│           │                   │   "price":7999... │               │
│           │                   │   "images":[...]} │               │
│           │                   │<──────────────────│               │
│           │ <- JSON           │                   │               │
│           │<──────────────────│                   │               │
│           │                   │                   │               │
│           │ React renderiza   │                   │               │
│           │ produtos          │                   │               │
│           │                   │                   │               │
│           │                   │  ┌───────────────────────────┐   │
│           │                   │  │ PostgreSQL (postgres-dev)  │   │
│           │                   │  │ Table: product             │   │
│           │                   │  │ - id (UUID)                │   │
│           │                   │  │ - title (str)              │   │
│           │                   │  │ - price (float)    ← ✅    │   │
│           │                   │  │ - image (JSON)     ← ✅    │   │
│           │                   │  │ - tags (JSON)              │   │
│           │                   │  └───────────────────────────┘   │
│           │                   │                   │               │
└─────────────────────────────────────────────────────────────────────┘

Legend:
- "proxy_pass http://site:5000" = Nginx encaminha /api/* para Flask
- "site:5000" = Docker service name (docker-compose.yaml)
```

### O que já está funcionando ✅

1. **Nginx está servindo React estático**
   - Porta 443 (HTTPS)
   - Archivos em `/app/dist/` (mapeado de `./frontend/dist`)
   - Configuração em [nginx-react.conf](nginx/nginx-react.conf#L65)

2. **Nginx proxeia `/api/*` para Flask**
   ```nginx
   upstream flask_backend {
       server site:5000 max_fails=3 fail_timeout=30s;
   }
   
   location /api/ {
       proxy_pass http://flask_backend;
       # ... headers ...
   }
   ```

3. **Flask retorna dados do banco**
   - Rota: `@product_bp.route("/api/products")` [product_routes.py#L131](services/site/routes/product_routes.py#L131)
   - Query: `SELECT * FROM product WHERE tag=... OR tag='all'`
   - Response: `[{id, title, price, images, ...}]`

4. **React fetches dinamicamente**
   - `frontend/src/services/productService.ts` → `await api.get('/api/products')`
   - Transforma resposta Flask → estrutura React
   - Renderiza componentes com dados

---

## 🐛 Possíveis Problemas & Soluções

### ❌ **Problema 1: `restage` rodou, mas banco não foi populado**

**Causa**: O script Python não conseguiu fazer POST para `/add_product`

**Verificar**:
```bash
# Terminal do container site
docker exec -it site python3 scripts/stage_products.py --force

# Procurar por linhas de erro (❌ [ERRO] ou [FALHA])
# Exemplo:
# ❌ Falha no upload iphone-15-pro.json
# ❌ Product saved: ... (status 500)
```

**Solução**:
```bash
# 1. Verifica se Flask está rodando em 5000
docker exec -it site curl http://localhost:5000/api/products

# 2. Verifica MinIO
docker exec -it site curl http://minio:9000/minio/bootstrap.html

# 3. Restart Flask
make restart-site

# 4. Retry restage
make restage
```

---

### ❌ **Problema 2: Banco foi populado, mas React NÃO mostra dados**

**Causa 1**: React ainda está usando **build desatualizado** (cache do navegador)

**Solução 1a - Limpar cache do navegador**:
```bash
# Chrome DevTools: Settings → Clear browsing data → All time → Images & files
# Ou: Hardrefresh (Ctrl+Shift+R no Linux/Windows, Cmd+Shift+R no Mac)
```

**Solução 1b - Rebuild React**:
```bash
cd frontend
npm run build

# Depois reinicia Nginx
docker compose -f docker-compose.react.yaml restart nginx
```

---

**Causa 2**: **Nginx não está servindo o build atualizado**

**Verificar**:
```bash
# Vê se exist `/app/dist/index.html`
docker exec nginx-react ls -la /app/dist/

# Se vazio ou desatualizado, significa volume não está mapeado corretamente
```

**Solução 2**:
```bash
# docker-compose.react.yaml linha 20
volumes:
  - ./frontend/dist:/app/dist:ro  # ← Deve apontar para o build React

# Rebuild e reinicia
docker compose -f docker-compose.yaml -f docker-compose.react.yaml up -d --build
```

---

**Causa 3**: **Proxy `/api/` não está funcionando**

**Verificar manualmente**:
```bash
# Dentro do container Nginx
docker exec nginx-react curl -k https://localhost/api/products

# Deve retornar JSON dos produtos (lista vazia ou com dados)

# Se der erro 502 ou 504:
# - Flask não está rodando
# - ou Nginx não consegue resolver "site:5000"
```

**Verificar resolução DNS do Docker**:
```bash
docker exec nginx-react nslookup site
# Deve resolver para IP interno (ex: 172.18.0.2)

# Se não resolver:
docker compose -f docker-compose.yaml -f docker-compose.react.yaml down -v
docker compose -f docker-compose.yaml -f docker-compose.react.yaml up -d --build
```

---

**Causa 4**: **React está fazendo request antes do banco estar pronto**

**Verificar** (console do navegador → DevTools → Network):
- GET `/api/products` → Status?
  - ✅ 200 = Funcionando
  - ❌ 502/504 = Flask down ou Nginx não encontra
  - ❌ 0 = CORS ou request bloqueado

**Solução**:
```bash
# Aguarda 5s antes de fazer primeira requisição
# (React já tem retry built-in com exponential backoff)

# Se ainda falhar:
make down
make up  # apenas os containers dev
make restage
make serve-frontend-public  # ou seu comando
```

---

### ✅ **O que deve acontecer passo a passo**

**1. Preparação (antes de `restage`)**
```bash
# Staging contém JSONs com produtos
ls -la services/site/staging/
# Output:
# casa-decoracao/sala/robo-aspirador.json
# eletrônicos/smartphones/iphone-15.json
# ...
```

**2. Execute restage**
```bash
make restage

# Output esperado:
# ⚠️ Reprocessando todo o staging (modo force)...
# 📁 Criando pasta do produto: robo-aspirador
# ✅ Upload: http://minio:9000/produtos/robo-aspirador/timestamp_img1.jpg
# ✅ Upload: http://minio:9000/produtos/robo-aspirador/timestamp_img2.jpg
# [✔] Produto salvo: casa-decoracao/sala/robo-aspirador.json (Tag: CD/sala)
# ... (mais produtos)
# ✅ 15 produto(s) processado(s)
```

**3. Verifica banco**
```bash
make psql

# No psql:
select id, title, price, tags from product limit 5;

# Output:
# id                | title | price | tags
# -----------------+-------+-------+------------------
# 550e8400-... | iPhone | 7999.90 | ["eletrônicos", "smartphones"]
# ...
```

**4. React fetches de Nginx**
```bash
# Browser DevTools → Network tab
# GET https://localhost/
# ← 200 (index.html estático do Nginx)

# GET https://localhost/api/products
# ← 200 (JSON do Flask via proxy do Nginx)
```

**5. React renderiza**
```html
<!-- No navegador -->
<div id="products-container">
  <div class="product-card">
    <h2>iPhone 15 Pro</h2>
    <p>R$ 7999.90</p>
    <img src="http://minio:9000/produtos/..." />
  </div>
  <!-- ... mais produtos -->
</div>
```

---

## 🛠️ Checklist de Verificação

| Item | Comando | Esperado |
|------|---------|----------|
| **Dados no Banco** | `make psql` → `SELECT COUNT(*) FROM product;` | Deve retornar número > 0 |
| **Nginx serve React** | `curl -k https://localhost/` | Status 200, contém `<!DOCTYPE html>` |
| **Proxy Flask** | `curl -k https://localhost/api/products` | Status 200, retorna `[{id, title, ...}]` |
| **MinIO imagens** | `docker exec minio curl http://minio:9000/minio/bootstrap.html` | Status 200 |
| **Flask direto** | `docker exec -it site curl http://localhost:5000/api/products` | Status 200, mesmo JSON |
| **React transpilado** | `ls -la frontend/dist/` | Contém `index.html`, `js/`, `css/` |

---

## 🚀 Solução Completa (Nuclear Option)

Se nada funcionar, force um reset:

```bash
# 1. Para tudo
make down

# 2. Remove volumes (reseta DB)
docker volume prune -f

# 3. Rebuild tudo
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build

# 4. Aguarda inicializa (20s)
sleep 20

# 5. Re-publica dados
make restage

# 6. Verifica banco ou JSON
make psql
# SELECT COUNT(*) FROM product;

# 7. Sobe Nginx + React
docker compose -f docker-compose.yaml -f docker-compose.react.yaml up -d --build

# 8. Acessa no navegador
open https://localhost
```

---

## 📋 Resumo Final

| Pergunta | Resposta |
|----------|----------|
| **O que `restage` muda?** | Lê JSONs do `staging/`, faz upload imagens para MinIO, salva produtos no PostgreSQL via `/add_product` |
| **Dados em MinIO ou DB?** | **Ambos**: Imagens em MinIO, metadados (title, price, tags, URLs) em PostgreSQL |
| **Como Nginx acessa?** | React faz `fetch('/api/products')` → Nginx proxeia `upstream site:5000` → Flask queries PostgreSQL |
| **Fluxo esperado** | `restage` (dados no DB) → React build → Nginx serve React → React fetches `/api/products` → Nginx proxeia Flask → PostgreSQL retorna → Renderiza |
| **Se dados n aparecem** | Verifica: 1) Banco tem dados? 2) `/api/products` retorna JSON? 3) React foi rebuildiado? 4) Nginx serve `/dist/*`? |
