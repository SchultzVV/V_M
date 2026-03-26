# 🔍 DIAGNÓSTICO: Por que `make serve-cloudflare` não funciona

Data: 2026-03-26  
Versão: Completo e Detalhado

---

## ✅ Problemas Identificados

### 🚨 **PROBLEMA PRINCIPAL: Porta Incorreta no Tunnel**

**Status:** ❌ **CRÍTICO**

O comando `make serve-cloudflare` no Makefile tenta conectar Cloudflared em:
```bash
cloudflared tunnel --url https://localhost:5000
```

Mas **Flask **está mapeado em uma porta diferente:

| Componente | Localização | Porto |
|-----------|------------|-------|
| Flask (inside container) | Interior do Docker | `5000` |
| Flask (no host) | Mapeado do Docker | `5555` → 5000 |
| **O que cloudflared precisa** | - | **`5555` ❌ Errado no Makefile** |

**Prova do erro:**
```bash
$ curl -s -k https://localhost:5000  # ❌ Congela (porta não existe no host)
$ curl -s -k https://localhost:5555  # ✅ Funciona! HTTP 200 OK
```

**Output do curl bem-sucedido:**
```
HTTP/1.1 200 OK
Server: Werkzeug/3.1.7 Python/3.10.20
Date: Thu, 26 Mar 2026 22:34:20 GMT
Content-Type: text/html; charset=utf-8
```

**Por que congelava?**
- Cloudflared tentava conectar em `localhost:5000`
- Ninguém está listening na porta 5000 do host
- Conexão ficava congelada/timeout
- Nunca capturava URL do túnel

---

### 🔴 **PROBLEMA SECUNDÁRIO: Buffer QUIC/UDP do Kernel**

**Status:** ⚠️ **AVISO (Não é blocker)**

Cloudflared mostra aviso ao iniciar:
```
failed to sufficiently increase receive buffer size 
(was: 208 kiB, wanted: 7168 kiB, got: 416 kiB)
```

**Causa:** Limite do kernel para UDP buffers muito baixo  
**Impacto:** Possível perda de pacotes em alta carga  
**Solução:** Aumentar `/proc/sys/net/core/rmem_max`

```bash
# Ver valores atuais:
cat /proc/sys/net/core/rmem_max

# Aumentar (requer sudo):
sudo sysctl -w net.core.rmem_max=7168000
```

---

### 🟡 **PROBLEMA TERCIÁRIO: Services de IA em Restart Loop**

**Status:** ⚠️ **SECUNDÁRIO (Não bloqueia serve-cloudflare)**

Dois containers estão com problema:
```
d76414b45be6   ingestion_service    Restarting (1) 19 seconds ago
ca520e6e5199   retrieval_service    Restarting (1) 23 seconds ago
```

**Causa provável:** Problemas internos das imagens ghcr.io  
**Impacto:** Rotas de IA `/ingest-url` e `/query` não funcionam  
**Não bloqueia:** Frontend/Backend outras funcionalidades continuam OK

---

## 📋 Checklist de Status

```
✅ cloudflared instalado: /usr/local/bin/cloudflared (v2026.2.0)
✅ Containers up:
   - site (Flask)
   - postgres-dev
   - redis
   - minio-dev
   - info-scrap
   - vector_db
✅ Flask respondendo em https://localhost:5555 (HTTP 200)
✅ Arquivo .env com credenciais ML presentes
✅ Docker Compose configurado

❌ ERRO: Porta incorreta no cloudflared tunnel (5000 vs 5555)
⚠️  AVISO: ingestion_service e retrieval_service em restart loop
⚠️  AVISO: Buffer QUIC kernel baixo
```

---

## 🔧 SOLUÇÃO IMEDIATA

### Opção 1: Corrigir o Makefile (RECOMENDADO)

Edite a linha no `Makefile` que define a URL do tunnel:

**Antes (ERRADO):**
```makefile
$$CLOUDFLARED_BIN tunnel \
    --url https://localhost:5000 \
```

**Depois (CORRETO):**
```makefile
$$CLOUDFLARED_BIN tunnel \
    --url https://localhost:5555 \
```

ou alternativamente, passar como parâmetro:

```makefile
TUNNEL_PORT ?= 5555
...
$$CLOUDFLARED_BIN tunnel \
    --url https://localhost:$(TUNNEL_PORT) \
```

### Opção 2: Usar manualmente (Quick Fix)

```bash
# Make service:
pkill cloudflared 2>/dev/null || true
cloudflared tunnel --url https://localhost:5555 --no-tls-verify

# Aguardar URL aparecer nos logs
# Copiar URL e adicionar em .env:
# ML_REDIRECT_URI=https://xxxxx.trycloudflare.com/auth/mercadolivre/callback
```

---

## 🐛 Por que isso aconteceu?

O Makefile foi criado assumindo que Flask rodaria na **porta 5000 do host**. Mas o `docker-compose.yaml` mapeia:

```yaml
services:
  site:
    ...
    ports:
      - "5555:5000"  # ← Host:Container
```

O Makefile não foi atualizado para refletir esse mapeamento.

---

## 📊 Diagrama de Fluxo Correto

```
┌─────────────────────────────────────────────────────────┐
│                        HOST                             │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ Cloudflared (rodando no host)                  │   │
│  │ URL: --url https://localhost:5555 ← CORRETO  │   │
│  └──────────────┬─────────────────────────────────┘   │
│                 │                                      │
│                 ↓                                      │
│  ┌────────────────────────────────────────────────┐   │
│  │ localhost:5555 (porta mapeada do Docker)       │   │
│  └──────────────┬─────────────────────────────────┘   │
│                 │                                      │
│                 ↓ Docker NAT                          │
└─────────────────────────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────────┐
│                   DOCKER NETWORK                        │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ Container: site                                │   │
│  │ IP: 172.18.0.9:5000                           │   │
│  │ App: Flask (HTTPS)                            │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔗 Fluxo Esperado (Após Fix)

```
1. make serve-cloudflare
   ↓
2. Docker containers sobem ✅
   ↓
3. Flask responde em https://localhost:5555 ✅
   ↓
4. Cloudflared conecta em https://localhost:5555 ✅
   ↓
5. Cloudflared gera URL: https://xxxx.trycloudflare.com ✅
   ↓
6. Makefile captura URL ✅
   ↓
7. .env atualizado com ML_REDIRECT_URI ✅
   ↓
8. Site reiniciado com nova URI ✅
   ↓
9. Token ML verificado (se válido, não precisa reautorizar) ✅
   ↓
10. Túnel ativo e funcionando! 🎉
```

---

## 🛠️ Passos para Fixar Agora

### 1️⃣ **Corrigir o Makefile**

Encontre a linha com `--url https://localhost:5000` (por volta da linha 152) e mude para:

```makefile
--url https://localhost:5555 \
```

### 2️⃣ **Testar a correção**

```bash
cd /home/v/Desktop/V_M
make serve-cloudflare
```

Esperado: Deve capturar URL em segundos e mostrar:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ TÚNEL ATIVO: https://summary-supply-mixing-sum.trycloudflare.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3️⃣ **Parar Cloudflare quando necessário**

```bash
make stop-cloudflare  # Se existir o comando
# Ou manualmente:
pkill cloudflared
```

---

## ⚠️ Problemas Secundários a Resolver

### A. Serviços de IA em Restart Loop

**Containers afetados:**
- `ingestion_service` (ghcr.io/schultzvv/hsmart-ingestion_service:latest)
- `retrieval_service` (ghcr.io/schultzvv/hsmart-retrieval_service:latest)

**Checklist de debug:**
```bash
# Ver logs detalhados
docker logs -f ingestion_service

# Possíveis causas:
# 1. Falta de variáveis de ambiente
# 2. Dependências faltando
# 3. Porta já em uso
# 4. Problema ao conectar com outros serviços
```

**Solução recomendada:**
```bash
# Remover e rebuildar essas imagens
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml \
  down -v  # Remover volumes

# Fazer pull das imagens mais recentes
docker pull ghcr.io/schultzvv/hsmart-ingestion_service:latest
docker pull ghcr.io/schultzvv/hsmart-retrieval_service:latest

# Subir novamente
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d
```

### B. Buffer QUIC (Opcional, Melhoria)

```bash
# Ver limite atual:
cat /proc/sys/net/core/rmem_max

# Aumentar (requer sudo):
sudo bash -c 'echo 7168000 > /proc/sys/net/core/rmem_max'

# Tornar permanente (edit /etc/sysctl.conf):
sudo nano /etc/sysctl.conf
# Adicionar:
net.core.rmem_max=7168000

# Recarregar:
sudo sysctl -p
```

---

## 📞 Resumo

| Item | Status |
|------|--------|
| Cloudflared instalado | ✅ |
| Containers up | ✅ |
| Flask respondendo | ✅ |
| Porta cloudflare | ❌ **ERRADO** (5000 vs 5555) |
| Serviços IA | ⚠️ Restart loop |
| Buffer QUIC | ⚠️ Baixo |

**Ação urgente:** Mudar porta do cloudflared no Makefile de **5000** para **5555**

Depois de fazer isso, `make serve-cloudflare` deve funcionar! 🚀
