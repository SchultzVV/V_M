# 🔐 Configuração OAuth - Mercado Livre

## 📋 Configurações no Painel do Mercado Livre

Acesse: https://developers.mercadolivre.com.br/devcenter

### 1️⃣ Redirect URIs (URLs de Callback)

Adicione **APENAS** esta URL:
```
http://localhost:5000/auth/mercadolivre/callback
```

✅ **Localhost funciona perfeitamente para OAuth!** Não precisa de ngrok.

### 2️⃣ Notificações (Webhooks)

**Configuração de notificações:**

**URL de retorno de chamada de notificação:**

Se você tem servidor público/VPS:
```
https://seu-dominio.com/webhook/mercadolivre
```

Se não tem servidor ainda, deixe em branco por enquanto. Você pode:
- Usar ngrok temporário para testes
- Deploy em Heroku/Railway/Render (grátis)
- Configurar depois quando tiver domínio

**Topics (tópicos):**
- ✅ `items` - Produtos (recomendado)
- ⬜ `orders` - Pedidos (opcional)
- ⬜ `payments` - Pagamentos (opcional)

---

## 🚀 Passo a Passo Completo

### 1. Configure no Painel do ML

```
App ID: 3186869212482819
Client Secret: nUDITepjvr7PSBwCFVlsgoFP7WoD5k1f

Redirect URIs:
  ✅ http://localhost:5000/auth/mercadolivre/callback

Notificações:
  URL: (deixe em branco por enquanto ou use ngrok temporário)
  Topics: items
```

### 2. Inicie o servidor local

```bash
cd /home/v/Documents/V_M
docker-compose up -d site
```

### 3. Faça login no navegador

```bash
# Abra esta URL no navegador
open http://localhost:5000/auth/mercadolivre/login
```

### 4. Autorize a aplicação

1. Você será redirecionado para o Mercado Livre
2. Faça login (se necessário)
3. Clique em **"Autorizar"**
4. Será redirecionado de volta para `localhost:5000/auth/mercadolivre/callback`
5. Tokens salvos automaticamente! ✅

### 5. Verifique autenticação

```bash
curl http://localhost:5000/auth/mercadolivre/status
```

---

## 🔄 Para Webhooks (Opcional)

Se quiser testar webhooks AGORA:

### Opção A: Ngrok Temporário (para testes)

```bash
# 1. Inicie ngrok
make serve-ngrok

# 2. Copie a URL gerada (ex: https://abc123.ngrok-free.app)

# 3. Configure no painel do ML:
# URL de notificação: https://abc123.ngrok-free.app/webhook/mercadolivre
# Topic: items

# ⚠️ URL muda toda vez que reinicia ngrok!
```

### Opção B: Deploy Gratuito (recomendado)

**Render.com (grátis):**
```bash
# 1. Crie conta em render.com
# 2. Deploy do repositório
# 3. URL fixa: https://seu-app.onrender.com
# 4. Configure: https://seu-app.onrender.com/webhook/mercadolivre
```

**Railway.app (grátis):**
```bash
# 1. Crie conta em railway.app
# 2. Deploy do repositório
# 3. URL fixa: https://seu-app.railway.app
# 4. Configure: https://seu-app.railway.app/webhook/mercadolivre
```

### Opção C: Sem Webhooks (atualização manual)

Você pode atualizar produtos manualmente via API:
```bash
curl -X POST http://localhost:5000/webhook/mercadolivre \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "items",
    "resource": "https://api.mercadolibre.com/items/MLB123456"
  }'
```

---

## ✅ Checklist Rápido

**Para OAuth (obrigatório):**
- [x] Adicionar `http://localhost:5000/auth/mercadolivre/callback` no painel
- [ ] Rodar `docker-compose up -d site`
- [ ] Acessar `http://localhost:5000/auth/mercadolivre/login`
- [ ] Autorizar no Mercado Livre
- [ ] Verificar tokens salvos

**Para Webhooks (opcional):**
- [ ] Decidir: ngrok temporário, deploy gratuito, ou deixar para depois
- [ ] Configurar URL no painel
- [ ] Testar com produto real

---

## 🎯 Resumo

**OAuth:** ✅ Use localhost - funciona perfeitamente!  
**Webhooks:** ⏳ Configure depois ou use deploy gratuito

Você pode usar todo o sistema de atualização de produtos **SEM** webhooks, fazendo chamadas manuais à API do Mercado Livre.
