# 🚀 Integração com API do Mercado Livre - Guia Completo

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Passo 1: Configurar Aplicação no Mercado Livre](#passo-1-configurar-aplicação-no-mercado-livre)
4. [Passo 2: Gerar URL HTTPS com Ngrok](#passo-2-gerar-url-https-com-ngrok)
5. [Passo 3: Configurar Variáveis de Ambiente](#passo-3-configurar-variáveis-de-ambiente)
6. [Passo 4: Autenticação OAuth 2.0](#passo-4-autenticação-oauth-20)
7. [Passo 5: Configurar Webhooks (Opcional)](#passo-5-configurar-webhooks-opcional)
8. [Verificação e Testes](#verificação-e-testes)
9. [Troubleshooting](#troubleshooting)

---

## Visão Geral

Este guia explica como integrar completamente sua aplicação com a API do Mercado Livre, incluindo:
- ✅ Autenticação OAuth 2.0
- ✅ Acesso à API com tokens válidos
- ✅ Configuração de webhooks para notificações em tempo real
- ✅ Uso de URLs HTTPS públicas com Ngrok

---

## Pré-requisitos

- Conta no Mercado Livre
- Docker e Docker Compose instalados
- Ngrok instalado (ou conta gratuita em ngrok.com)
- Aplicação registrada no [Mercado Livre Developers](https://developers.mercadolivre.com.br/devcenter)

**Credenciais Atuais:**
```
APP_ID: 3186869212482819
CLIENT_SECRET: nUDITepjvr7PSBwCFVlsgoFP7WoD5k1f
```

---

## Passo 1: Configurar Aplicação no Mercado Livre

### 1.1 Acessar o Painel de Desenvolvedores

1. Acesse: **https://developers.mercadolivre.com.br/devcenter**
2. Faça login com sua conta do Mercado Livre
3. Selecione sua aplicação ou crie uma nova

### 1.2 Configurar Redirect URIs (URLs de Callback)

No painel da aplicação, adicione as seguintes URLs na seção **"Redirect URIs"**:

```
http://localhost:5000/auth/mercadolivre/callback
https://lojinhavem.ngrok-free.app/auth/mercadolivre/callback
```

**⚠️ IMPORTANTE:**
- ✅ Use EXATAMENTE estas URLs (sem espaços ou barras extras no final)
- ✅ Localhost funciona perfeitamente para OAuth
- ✅ Adicione AMBAS as URLs para flexibilidade (local e produção)

### 1.3 Verificar Scopes/Permissões

Certifique-se de que sua aplicação tem os seguintes scopes autorizados:
- ✅ `read` - Leitura de dados de produtos
- ✅ `write` - Criação e modificação de produtos (se necessário)
- ✅ `offline_access` - Token de longa duração (refresh token)

---

## Passo 2: Gerar URL HTTPS com Ngrok

### 2.1 O que é Ngrok?

Ngrok cria um túnel HTTPS público para seu servidor local, permitindo:
- Receber webhooks do Mercado Livre
- Testar OAuth em ambiente de desenvolvimento
- Usar URLs HTTPS sem certificado próprio

### 2.2 Instalar Ngrok

**Linux:**
```bash
# Download
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Verificar instalação
ngrok version
```

### 2.3 Autenticar Ngrok (Obrigatório para Subdomínio Fixo)

1. Crie uma conta em **https://ngrok.com** (gratuita)
2. Obtenha seu token de autenticação no dashboard
3. Configure o token:

```bash
ngrok config add-authtoken SEU_TOKEN_AQUI
```

**Token Atual (já configurado):**
```bash
ngrok config add-authtoken 2xeRMEjVNTQNBMZ6NgIKA6vmcKW_7fMcqFDCSpJU1UfMJ9rUX
```

### 2.4 Gerar URL HTTPS com Subdomínio Fixo

**Opção A: Usando Makefile (Recomendado)**
```bash
make serve-ngrok
```

**Opção B: Manualmente**
```bash
ngrok http --domain=lojinhavem.ngrok-free.app 5000
```

### 2.5 Verificar URL Gerada

Após executar o comando, você verá:

```
ngrok

Session Status                online
Account                       Your Account (Plan: Free)
Version                       3.x.x
Region                        South America (sa)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://lojinhavem.ngrok-free.app -> http://localhost:5000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**🎯 Sua URL pública é:** `https://lojinhavem.ngrok-free.app`

**📊 Interface Web do Ngrok:**
- Acesse: **http://127.0.0.1:4040**
- Monitore todas as requisições em tempo real
- Visualize headers, payloads e respostas

### 2.6 Vantagens do Plano Free do Ngrok

✅ Subdomínio fixo (não muda quando reinicia)  
✅ HTTPS automático  
✅ 40 conexões/minuto (suficiente para desenvolvimento)  
✅ Sem necessidade de servidor externo  

---

## Passo 3: Configurar Variáveis de Ambiente

### 3.1 Atualizar arquivo .env

Edite o arquivo `.env` na raiz do projeto:

```bash
# Configuração do Mercado Livre
ML_APP_ID=3186869212482819
ML_CLIENT_SECRET=nUDITepjvr7PSBwCFVlsgoFP7WoD5k1f
ML_REDIRECT_URI=https://lojinhavem.ngrok-free.app/auth/mercadolivre/callback
ML_ACCESS_TOKEN=
ML_REFRESH_TOKEN=

# Configuração do Ngrok
NGROK_SUBDOMAIN=lojinhavem
NGROK_TKN=2xeRMEjVNTQNBMZ6NgIKA6vmcKW_7fMcqFDCSpJU1UfMJ9rUX
```

**⚠️ IMPORTANTE:**
- `ML_ACCESS_TOKEN` e `ML_REFRESH_TOKEN` começam vazios
- Serão preenchidos automaticamente após o OAuth
- Não compartilhe o `ML_CLIENT_SECRET` publicamente

### 3.2 Reiniciar Containers

Após alterar o `.env`, reinicie os containers:

```bash
docker-compose down
docker-compose up -d
```

---

## Passo 4: Autenticação OAuth 2.0

### 4.1 Como Funciona o OAuth

```
1. Usuário → Inicia autorização
   ↓
2. Redireciona para → Mercado Livre (tela de login)
   ↓
3. Usuário → Autoriza a aplicação
   ↓
4. ML redireciona → Callback com código temporário
   ↓
5. Servidor → Troca código por access_token + refresh_token
   ↓
6. Sistema → Salva tokens em config/ml_tokens.json
   ↓
7. ✅ Pronto! Aplicação autenticada
```

### 4.2 Iniciar Fluxo de Autenticação

#### Método 1: Via Navegador (Recomendado)

1. **Inicie o servidor:**
   ```bash
   docker-compose up -d site
   ```

2. **Inicie o Ngrok:**
   ```bash
   make serve-ngrok
   ```

3. **Acesse no navegador:**
   ```
   https://lojinhavem.ngrok-free.app/auth/mercadolivre/login
   ```

4. **Na página do Mercado Livre:**
   - Faça login (se necessário)
   - Clique em **"Autorizar"**
   - Aguarde o redirecionamento automático

5. **Verificação:**
   - Você será redirecionado para `/auth/mercadolivre/callback`
   - Uma mensagem de sucesso será exibida
   - Tokens salvos automaticamente!

#### Método 2: Localmente (Sem Ngrok)

Se preferir testar localmente primeiro:

1. **Atualize temporariamente o `.env`:**
   ```bash
   ML_REDIRECT_URI=http://localhost:5000/auth/mercadolivre/callback
   ```

2. **Reinicie o servidor:**
   ```bash
   docker-compose restart site
   ```

3. **Acesse:**
   ```
   http://localhost:5000/auth/mercadolivre/login
   ```

### 4.3 Estrutura dos Tokens

Após a autenticação, o arquivo `services/site/config/ml_tokens.json` será criado:

```json
{
  "access_token": "APP_USR-3186869212482819-...",
  "token_type": "Bearer",
  "expires_in": 21600,
  "expires_at": "2026-01-22T20:14:16.123456",
  "refresh_token": "TG-...",
  "user_id": 123456789,
  "scope": "offline_access read write"
}
```

**Informações Importantes:**
- `access_token` - Válido por 6 horas (21600 segundos)
- `refresh_token` - Válido por 6 meses (renova automaticamente)
- `expires_at` - Data/hora de expiração do access_token
- Sistema **renova automaticamente** antes de expirar

### 4.4 Verificar Status da Autenticação

```bash
# Via curl
curl https://lojinhavem.ngrok-free.app/auth/mercadolivre/status

# Resposta esperada:
{
  "status": "authenticated",
  "message": "Autenticado com sucesso",
  "has_token": true,
  "token_preview": "APP_USR-3186869212..."
}
```

---

## Passo 5: Configurar Webhooks (Opcional)

Os webhooks permitem que o Mercado Livre notifique sua aplicação automaticamente quando:
- Um produto é criado/modificado
- Um pedido é recebido
- Uma pergunta é feita
- Pagamento é processado

### 5.1 Cadastrar Webhook no Painel ML

1. Acesse: **https://developers.mercadolivre.com.br/devcenter**
2. Selecione sua aplicação
3. Vá até a seção **"Notificações" ou "Webhooks"**

### 5.2 Configurar URL de Notificação

**URL de retorno de chamada de notificação:**
```
https://lojinhavem.ngrok-free.app/webhook/mercadolivre
```

**Topics (tópicos) disponíveis:**
- ✅ `items` - Produtos (criação, modificação, pausa, exclusão)
- ⬜ `orders` - Pedidos (novo pedido, mudança de status)
- ⬜ `questions` - Perguntas de clientes
- ⬜ `payments` - Pagamentos (aprovação, estorno)

**Recomendação:** Comece apenas com `items` e adicione outros conforme necessidade.

### 5.3 Testar Webhook Manualmente

```bash
# Simular notificação do ML
curl -X POST https://lojinhavem.ngrok-free.app/webhook/mercadolivre \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "items",
    "resource": "https://api.mercadolibre.com/items/MLB123456789"
  }'
```

### 5.4 Monitorar Webhooks no Ngrok

1. Acesse: **http://127.0.0.1:4040**
2. Todas as requisições serão listadas em tempo real
3. Clique em uma requisição para ver:
   - Headers completos
   - Payload JSON
   - Resposta do servidor

---

## Verificação e Testes

### 6.1 Verificar Autenticação

```bash
# Status da autenticação
curl https://lojinhavem.ngrok-free.app/auth/mercadolivre/status

# Renovar token manualmente (se necessário)
curl -X POST https://lojinhavem.ngrok-free.app/auth/mercadolivre/refresh

# Fazer logout
curl -X POST https://lojinhavem.ngrok-free.app/auth/mercadolivre/logout
```

### 6.2 Testar API do Mercado Livre

```bash
# Obter informações do usuário
curl -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  https://api.mercadolibre.com/users/me

# Buscar seus produtos
curl -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  https://api.mercadolibre.com/users/SEU_USER_ID/items/search

# Buscar detalhes de um produto específico
curl -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  https://api.mercadolibre.com/items/MLB123456789
```

### 6.3 Usar Sistema de Preparação de Produtos

Com a autenticação configurada, você pode usar o sistema completo:

```bash
# Preparar produto usando API + Scraping
make api-prepare-product URL="https://produto.mercadolivre.com.br/MLB-123456789"

# O sistema irá:
# 1. Fazer scraping do HTML
# 2. Enriquecer com dados da API (preço real, estoque, imagens HQ)
# 3. Salvar JSON na pasta staging
```

---

## Troubleshooting

### Erro: "redirect_uri_mismatch"

**Causa:** A URL de callback não está cadastrada no painel do ML.

**Solução:**
1. Verifique se a URL está EXATAMENTE igual no painel:
   ```
   https://lojinhavem.ngrok-free.app/auth/mercadolivre/callback
   ```
2. Sem espaços, sem barra no final
3. Protocolo correto (https://)

### Erro: "não foi possível conectar o aplicativo à sua conta"

**Causa:** Configuração incorreta no painel do ML.

**Solução:**
1. Verifique se o app está **ativo** (não suspenso)
2. Confirme os scopes: `read`, `write`, `offline_access`
3. Teste a URL de autorização manualmente no painel ML

### Erro: 403 Forbidden na API

**Causa:** Token inválido ou sem permissões suficientes.

**Solução:**
1. Refaça o fluxo OAuth para obter novo token
2. Verifique se os scopes incluem `read`
3. Confirme que o token não expirou

### URL do Ngrok muda constantemente

**Causa:** Usando ngrok sem subdomínio fixo.

**Solução:**
1. Crie conta gratuita em ngrok.com
2. Configure seu token: `ngrok config add-authtoken SEU_TOKEN`
3. Use subdomínio fixo: `ngrok http --domain=lojinhavem.ngrok-free.app 5000`

### Webhooks não chegam

**Verificações:**
1. Ngrok está rodando? (`ps aux | grep ngrok`)
2. URL está correta no painel ML?
3. Servidor local está ativo? (`docker ps`)
4. Monitore em tempo real: http://127.0.0.1:4040

### Tokens expiram rapidamente

**Comportamento normal:**
- Access token: 6 horas
- Refresh token: 6 meses

**Solução:**
- Sistema renova automaticamente via `ml_auth.get_valid_access_token()`
- Se ficar 6 meses sem usar, refaça o OAuth

---

## Checklist Completo

### ✅ Configuração Inicial
- [ ] App criado no Mercado Livre Developers
- [ ] Redirect URIs cadastradas no painel
- [ ] Scopes configurados (read, write, offline_access)
- [ ] Variáveis de ambiente configuradas no .env
- [ ] Ngrok autenticado com token

### ✅ Autenticação OAuth
- [ ] Ngrok rodando com subdomínio fixo
- [ ] Servidor local ativo (docker-compose up)
- [ ] Acesso à URL de login funcionando
- [ ] Autorização no ML concluída
- [ ] Tokens salvos em config/ml_tokens.json
- [ ] Status de autenticação confirmado

### ✅ Webhooks (Opcional)
- [ ] URL de webhook cadastrada no painel ML
- [ ] Topics selecionados (items recomendado)
- [ ] Teste manual de webhook bem-sucedido
- [ ] Monitoramento via ngrok funcionando

### ✅ Testes Finais
- [ ] API do ML responde com token
- [ ] Dados de produtos sendo enriquecidos
- [ ] Renovação automática de token funciona
- [ ] Sistema completo integrado

---

## Links Úteis

### Documentação Oficial
- [Mercado Livre Developers](https://developers.mercadolivre.com.br/devcenter)
- [Autenticação e Autorização](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)
- [Itens e Buscas](https://developers.mercadolivre.com.br/pt_br/itens-e-buscas)
- [Publicação de Produtos](https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos)
- [Webhooks/Notificações](https://developers.mercadolivre.com.br/pt_br/produto-receba-notificacoes)
- [Erro 403](https://developers.mercadolivre.com.br/pt_br/erro-403)

### Ferramentas
- [Ngrok Download](https://ngrok.com/download)
- [Ngrok Dashboard](https://dashboard.ngrok.com)
- [Interface Web Ngrok](http://127.0.0.1:4040) (quando rodando)

### Endpoints do Sistema
- Login OAuth: `https://lojinhavem.ngrok-free.app/auth/mercadolivre/login`
- Status: `https://lojinhavem.ngrok-free.app/auth/mercadolivre/status`
- Webhook: `https://lojinhavem.ngrok-free.app/webhook/mercadolivre`

---

## Resumo Rápido

**Para começar a usar:**

1. **Configure no painel ML:** Adicione `https://lojinhavem.ngrok-free.app/auth/mercadolivre/callback`
2. **Inicie Ngrok:** `make serve-ngrok`
3. **Inicie servidor:** `docker-compose up -d`
4. **Faça login:** Acesse `https://lojinhavem.ngrok-free.app/auth/mercadolivre/login`
5. **Autorize** no Mercado Livre
6. **Pronto!** Tokens salvos automaticamente ✅

**Para webhooks:**
- Adicione `https://lojinhavem.ngrok-free.app/webhook/mercadolivre` no painel ML
- Selecione topic `items`
- Monitore em http://127.0.0.1:4040

---

**🎉 Integração completa com API do Mercado Livre!**
