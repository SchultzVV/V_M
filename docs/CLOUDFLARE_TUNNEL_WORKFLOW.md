# Cloudflare Tunnel Workflow — Shared Architecture

## 🎯 Overview

O sistema agora usa uma **arquitetura de tunnel único** onde:

1. **Um processo `cloudflared`** conecta a localhost:443 (Nginx)
2. **Nginx atua como reverse proxy** roteando requisições:
   - `/` → React static files (frontend/dist)
   - `/api/*` → Backend Flask (site:5000)
   - `/auth/*` → Backend Flask (site:5000)
   - `/webhook/*` → Backend Flask (site:5000)
3. **Ambos `serve-cloudflare` e `serve-frontend-public`** reutilizam o mesmo tunnel

---

## 📋 Workflow: Usar Backend E Frontend Simultaneamente

### Opção 1️⃣: Começar com Backend

```bash
# Terminal 1: Inicia backend + frontend estático
$ make serve-cloudflare

# Output:
# ✅ Backend em https://localhost:5000
# ✅ Nginx em https://localhost:443
# ✅ TÚNEL ATIVO: https://abc123.trycloudflare.com
# 
# Pode chamar: /api/*, /auth/*, ou acessar o frontend em Jinja2 template
```

```bash
# Terminal 2: Depois, atualizar React e servir pelo Nginx
$ make serve-frontend-public

# Output:
# 🔄 Túnel já está rodando...
# ✅ Reutilizando URL: https://abc123.trycloudflare.com
# ✅ React build completo (fresh)
# ✅ REACT FRONTEND ATIVO: https://abc123.trycloudflare.com
```

**Resultado**: Uma única URL pública serve React + Backend sem conflitos! 🎉

---

### Opção 2️⃣: Começar com Frontend

```bash
# Terminal 1: Inicia frontend + tunnel
$ make serve-frontend-public

# Output:
# ✅ React build completo
# ✅ Nginx em https://localhost:443
# ✅ TÚNEL ATIVO: https://abc123.trycloudflare.com
```

```bash
# Terminal 2: Backend já havia sido iniciado por serve-frontend-public!
# Verificar status:
$ docker ps | grep site

# RESULTADO: Ambos rodando, 1 tunnel, 1 URL!
```

---

## 🛑 Shutdown: 3 Opções

### Opção A: Parar apenas Frontend (preserva Backend + Tunnel)
```bash
$ make stop-frontend-public

# Output:
# ✅ Nginx parado
# ⚠️  Tunnel permanece para Backend
# 💡 Se quiser parar o tunnel: make stop-cloudflare
```

### Opção B: Parar apenas Tunnel (preserva Containers)
```bash
$ make stop-cloudflare

# Output:
# ✅ Túnel encerrado (cloudflared morto)
# ✅ Containers continuam rodando (backend, nginx, dbs, etc)
# 💡 Útil para reiniciar tunnel sem rebuilt
```

### Opção C: Parar TUDO
```bash
$ make stop-all

# Output:
# ✅ Tunnel parado
# ✅ Containers parados
```

---

## 🔄 Como Funciona a Reutilização de Tunnel

### script/tunnel-manager.sh Logic

```bash
# Quando você executa serve-frontend-public:
bash scripts/tunnel-manager.sh

# O script faz:
1. Verifica: " pgrep cloudflared rodando?"
2. SIM:  Reutiliza URL do /tmp/cloudflare_tunnel.log
   NÃO:  Inicia novo tunnel
```

**Isso significa**: Não importa quantas vezes você rode `serve-cloudflare` ou `serve-frontend-public`, há apenas 1 túnel ativo!

---

## ⚠️ ML OAuth URI Handling

### Problema Antigo (Antes)
```
serve-cloudflare  → URL: https://abc123.trycloudflare.com
serve-frontend-public → mata tunnel antigo
serve-frontend-public → URL: https://xyz789.trycloudflare.com ❌ DIFERENTE!
ML OAuth quebrado!
```

### Solução Nova (Agora)
```
serve-cloudflare  → URL: https://abc123.trycloudflare.com
                  → ML_REDIRECT_URI = https://abc123.trycloudflare.com/auth/mercadolivre/callback

serve-frontend-public → Detecta tunnel já existe
                      → Reutiliza MESMA URL: https://abc123.trycloudflare.com
                      → ML_REDIRECT_URI não muda! ✅
```

---

## 🧪 Teste: Verificar que Funciona

```bash
# Terminal 1
$ make serve-cloudflare
# Output:
# ↳ Tunnel: https://abc123.trycloudflare.com
# ↳ Pode usar: /api/products via Nginx

# Abrir no navegador
$ open "https://abc123.trycloudflare.com/api/products"
# Response: JSON do backend ✅


# Terminal 2 (sem encerrar Terminal 1)
$ make serve-frontend-public
# Output:
# 🔄 Túnel já está rodando...
# ✅ Reutilizando URL: https://abc123.trycloudflare.com


# Verificar que Frontend está atualizado
$ open "https://abc123.trycloudflare.com"
# Vê React SPA novo (não mais Jinja2!) ✅
```

---

## 📊 Architecture Diagram

```
Internet (Users)
    ↓
https://abc123.trycloudflare.com
    ↓
┌─────────────────────────────────────────┐
│    Cloudflare Tunnel (cloudflared)      │
│    ↓ Apontando para                     │
│    localhost:443 (Nginx)                │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│         Nginx (Reverse Proxy)           │
│  localhost:443                          │
├─────────────────────────────────────────┤
│ /                  → /frontend/dist (React SPA)
│ /api/*             → site:5000 (Flask Backend)
│ /auth/*            → site:5000 (Flask Backend)
│ /webhook/*         → site:5000 (Flask Backend)
└─────────────────────────────────────────┘
    ↓ (via Docker network 'backend')
┌─────────────────────────────────────────┐
│  site:5000 (Flask Backend)              │
│  + database, redis, vector_db, etc      │
└─────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### Q: Rodei `serve-frontend-public` mas Frontend não atualiza
**A**: Frontend build pode ter falhado silenciosamente
```bash
$ cd frontend && npm run build
# Se houver erro, corrigir e tentar novamente
$ make serve-frontend-public
```

### Q: Tunnel URL mudou entre os dois comandos
**A**: `tunnel-manager.sh` detectou processo antigo e iniciou novo. Verificar:
```bash
$ ps aux | grep cloudflared
# Deve haver apenas 1 processo cloudflared rodando
```

### Q: Nginx mostra erro 502 (Bad Gateway)
**A**: Backend não está pronto. Verificar:
```bash
$ docker exec site curl https://localhost:5000/api/products \
  -k  # ignore SSL error

# Se não responder, backend precisa mais tempo para iniciar
# Aguarde 10s e tente novamente
```

### Q: "ML_REDIRECT_URI não atualiza"
**A**: Verificar que .env é lido apenas no startup do container
```bash
# Se mudou .env, precisa reiniciar:
$ docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml restart site
```

---

## 📝 Summary

| Aspecto | Antes | Depois |
|--------|--------|--------|
| Tunnels | 2 separados | 1 compartilhado |
| Conflitos | pkill mata anterior | tunnel-manager.sh detecta |
| URLs ML | Podem divergir | Sempre mesma |
| Backend + Frontend | Mutuamente exclusivos | Simultâneos! |
| Ease of Use | Complexo | Simples |

---

## 🚀 Next Steps

1. **Testar o workflow** acima
2. **Confirmar que** `serve-frontend-public` reutiliza tunnel corretamente
3. **Deletar** `docker-compose.react.yaml` (não usado mais)
4. **Documentar** em team wiki: "Use serve-frontend-public DEPOIS de serve-cloudflare"
