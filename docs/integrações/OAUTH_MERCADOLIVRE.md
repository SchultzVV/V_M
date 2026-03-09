# OAuth 2.0 - Mercado Livre

Sistema de autenticação OAuth 2.0 para acessar a API do Mercado Livre.

## 🔑 Como Funciona

### 1. **Configuração no Mercado Livre**

Acesse: https://developers.mercadolivre.com.br/devcenter

Na sua aplicação (ID: `3186869212482819`):

1. **Redirect URI** - Adicione as URLs de callback:
   - Desenvolvimento: `http://localhost:5000/auth/mercadolivre/callback`
   - Ngrok: `https://lojinhavem.ngrok.io/auth/mercadolivre/callback`

2. **Notificações** - Configure o webhook:
   - URL: `https://lojinhavem.ngrok.io/webhook/mercadolivre`
   - Topics: `items` (produtos)

### 2. **Fluxo de Autenticação**

```
Usuário → /auth/mercadolivre/login
    ↓
Mercado Livre (tela de autorização)
    ↓
Callback → /auth/mercadolivre/callback
    ↓
Troca code por access_token + refresh_token
    ↓
Salva tokens em config/ml_tokens.json
    ↓
Pronto! ✅
```

### 3. **Usar Localmente (sem ngrok)**

```bash
# 1. Inicie o servidor
docker-compose up -d site

# 2. Acesse no navegador
http://localhost:5000/auth/mercadolivre/login

# 3. Autorize a aplicação no Mercado Livre

# 4. Você será redirecionado de volta
# Tokens salvos automaticamente!
```

### 4. **Usar com Ngrok (recomendado para webhooks)**

```bash
# 1. Configure o redirect_uri no painel do ML
# Adicione: https://lojinhavem.ngrok.io/auth/mercadolivre/callback

# 2. Atualize o .env
ML_REDIRECT_URI=https://lojinhavem.ngrok.io/auth/mercadolivre/callback

# 3. Suba o ambiente
make serve-ngrok

# 4. Acesse
https://lojinhavem.ngrok.io/auth/mercadolivre/login

# 5. Autorize e pronto!
```

## 📡 Endpoints

### Login / Autorização
```
GET /auth/mercadolivre/login
```
Redireciona para a tela de autorização do Mercado Livre.

### Callback (automático)
```
GET /auth/mercadolivre/callback?code=TG-...
```
Recebe o código e troca por tokens. **Não chame diretamente!**

### Status da Autenticação
```bash
curl http://localhost:5000/auth/mercadolivre/status
```

Resposta:
```json
{
  "status": "authenticated",
  "message": "Autenticado com sucesso",
  "has_token": true,
  "token_preview": "APP_USR-3186869212..."
}
```

### Renovar Token (manual)
```bash
curl -X POST http://localhost:5000/auth/mercadolivre/refresh
```

### Logout
```bash
curl -X POST http://localhost:5000/auth/mercadolivre/logout
```

## 🔄 Renovação Automática

O sistema **renova automaticamente** o access_token quando:
- Está a menos de 5 minutos de expirar
- É solicitado via `ml_auth.get_valid_access_token()`

Os tokens são salvos em: `services/site/config/ml_tokens.json`

```json
{
  "access_token": "APP_USR-3186869212482819-...",
  "token_type": "Bearer",
  "expires_in": 21600,
  "expires_at": "2026-01-02T20:14:16.123456",
  "refresh_token": "TG-...",
  "user_id": 123456789,
  "scope": "offline_access read write"
}
```

## 🧪 Testar Autenticação

```bash
# 1. Faça login
open http://localhost:5000/auth/mercadolivre/login

# 2. Verifique status
curl http://localhost:5000/auth/mercadolivre/status

# 3. Teste o webhook (agora com autenticação!)
curl -X POST http://localhost:5000/webhook/mercadolivre \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "items",
    "resource": "https://api.mercadolibre.com/items/MLB3704497069"
  }'
```

## ⚠️ Importante

### Ngrok Free vs Paid

**✅ Ngrok Free funciona!**
- URL estática com subdomain: `lojinhavem.ngrok.io` ✅
- OAuth callbacks funcionam normalmente
- Webhooks funcionam normalmente

**Limitações do Free:**
- 1 subdomain fixo (já configurado: `lojinhavem`)
- 40 conexões/minuto
- Suficiente para desenvolvimento e testes

### Redirect URI no Painel

Você PRECISA adicionar **exatamente** estas URLs no painel:

```
http://localhost:5000/auth/mercadolivre/callback
https://lojinhavem.ngrok.io/auth/mercadolivre/callback
```

Se a URL não estiver cadastrada, você receberá erro:
```
redirect_uri_mismatch
```

### Tokens Expiram

- **Access Token:** 6 horas (21600 segundos)
- **Refresh Token:** 6 meses (não expira se usado regularmente)

O sistema renova automaticamente, mas se você ficar 6 meses sem usar, precisará fazer login novamente.

## 🔒 Segurança

- ✅ Tokens salvos localmente em `config/ml_tokens.json`
- ✅ Arquivo não está no git (`.gitignore`)
- ✅ `CLIENT_SECRET` em variáveis de ambiente
- ✅ Renovação automática antes de expirar

## 📋 Checklist para Usar

- [ ] Adicionar redirect URIs no painel do ML
- [ ] Configurar `ML_REDIRECT_URI` no `.env`
- [ ] Acessar `/auth/mercadolivre/login`
- [ ] Autorizar a aplicação
- [ ] Verificar tokens em `/auth/mercadolivre/status`
- [ ] Testar webhook com produto real

## 🚀 Pronto!

Agora o webhook pode acessar a API do Mercado Livre sem erro 403! 🎉
