# Guia Prático: Configurar Instagram Business e Graph API

## 🎯 Objetivo
Preparar tudo para usar a **Instagram Graph API** oficialmente, permitindo publicações automáticas sem risco de bloqueio.

---

## ⏱️ Tempo estimado: 30-45 minutos

---

## 📋 Checklist de Pré-requisitos

Antes de começar, certifique-se de ter:

- [ ] Conta Instagram ativa (será convertida para Business)
- [ ] Conta Facebook ativa
- [ ] Acesso de administrador à conta Instagram
- [ ] Número de telefone para verificação (pode ser necessário)

---

## 🚀 Passo a Passo

### Etapa 1: Converter para Instagram Business Account (5 min)

1. **Abra o app Instagram** no celular
2. Vá em **Perfil** → **☰ Menu** → **⚙️ Configurações**
3. Clique em **Conta**
4. Clique em **Mudar para conta profissional**
5. Escolha **Empresa** (ou **Criador de conteúdo**)
6. Siga as instruções na tela
7. ✅ Anote o **nome de usuário Instagram Business**

**Verificação**: Seu perfil agora tem "Editar perfil profissional" e botões de contato.

---

### Etapa 2: Criar Facebook Page (3 min)

1. Acesse: https://www.facebook.com/pages/create
2. Clique em **Criar página**
3. Preencha:
   - **Nome da página**: Use o mesmo nome do Instagram
   - **Categoria**: "Varejo" ou "Empresa local"
   - **Bio**: Opcional
4. Clique em **Criar página**
5. ✅ Anote o **ID da página** (aparece na URL)

**Exemplo URL**: `facebook.com/YourPage-123456789012345/`
- O ID é: `61586618681178`

---

### Etapa 3: Conectar Instagram à Facebook Page (5 min)

1. Na **Facebook Page** criada, vá em **Configurações**
2. No menu esquerdo, clique em **Instagram**
3. Clique em **Conectar conta**
4. Faça login com sua conta Instagram Business
5. Autorize a conexão
6. ✅ Verifique que aparece "Conectado a @seu_usuario"

**Alternativa via Instagram**:
1. App Instagram → **Configurações** → **Empresa**
2. **Página do Facebook**
3. **Conectar sua página** → Selecione a página criada

---
# PAREI AQUI NESSE CARALHO META É RIDICULO DE RUIM RAPAZ
### Etapa 4: Criar App no Meta for Developers (10 min)

1. Acesse: https://developers.facebook.com/apps/
2. Clique em **Criar app**
3. Selecione **Outro** → **Próximo**
4. Escolha **Business** → **Próximo**
5. Preencha:
   - **Nome do app**: `Instagram Auto Poster` (ou seu nome)
   - **Email de contato**: seu email
   - **Vincular conta comercial**: Opcional (pode pular)
6. Clique em **Criar app**
7. Complete o captcha se solicitado
8. ✅ Anote o **App ID** e **App Secret** (Dashboard do app)

---

### Etapa 5: Adicionar Instagram Graph API ao App (5 min)

1. No Dashboard do app, vá em **Adicionar produtos**
2. Procure **Instagram Graph API**
3. Clique em **Configurar**
4. Em **Permissões do app**, adicione:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`
5. Salve as alterações

---

### Etapa 6: Obter Access Token (10 min)

Existem duas formas:

#### Opção A: Via Graph API Explorer (Rápido - Para Testes)

1. Acesse: https://developers.facebook.com/tools/explorer/
2. Selecione seu **App** no topo
3. Em **Permissões**, adicione:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`
4. Clique em **Generate Access Token**
5. Autorize as permissões
6. Copie o **Access Token** (curto prazo)
7. Clique em **ℹ️** ao lado do token
8. Clique em **Open in Access Token Tool**
9. Clique em **Extend Access Token** para obter **Long-Lived Token** (60 dias)
10. ✅ Copie o **Long-Lived Token**

#### Opção B: Via Facebook Login (Produção - Implementar depois)

Implementar fluxo OAuth completo na aplicação (explicado na próxima seção).

---

### Etapa 7: Obter Instagram Business Account ID (5 min)

Com o access token obtido, faça uma chamada à API:

```bash
curl -X GET \
  "https://graph.facebook.com/v21.0/me/accounts?access_token={ACCESS_TOKEN}"
```

Na resposta, pegue o `id` da sua página. Depois:

```bash
curl -X GET \
  "https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={ACCESS_TOKEN}"
```

Na resposta, copie o **`instagram_business_account.id`**.

**OU** use o código Python:

```python
import requests

ACCESS_TOKEN = "seu_token_aqui"

# 1. Pegar Page ID
response = requests.get(
    f"https://graph.facebook.com/v21.0/me/accounts",
    params={"access_token": ACCESS_TOKEN}
)
page_id = response.json()['data'][0]['id']
print(f"Page ID: {page_id}")

# 2. Pegar Instagram Business Account ID
response = requests.get(
    f"https://graph.facebook.com/v21.0/{page_id}",
    params={
        "fields": "instagram_business_account",
        "access_token": ACCESS_TOKEN
    }
)
ig_account_id = response.json()['instagram_business_account']['id']
print(f"Instagram Account ID: {ig_account_id}")
```

✅ Anote o **Instagram Business Account ID**

---

### Etapa 8: Configurar Variáveis de Ambiente (3 min)

Adicione ao seu `.env`:

```bash
# Instagram Graph API (Oficial)
INSTAGRAM_GRAPH_API_VERSION=v21.0
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400000000000  # ID obtido na Etapa 7
FACEBOOK_PAGE_ID=123456789012345                  # ID da Etapa 2
META_APP_ID=123456789012345                       # App ID da Etapa 4
META_APP_SECRET=abc123def456...                   # App Secret da Etapa 4
INSTAGRAM_ACCESS_TOKEN=EAABwzLix...               # Long-Lived Token da Etapa 6

# Manter para testes legacy (opcional)
# INSTAGRAM_USERNAME=vem.sm
# INSTAGRAM_PASSWORD=07012025
```

---

### Etapa 9: Testar a API (5 min)

Teste básico para verificar se está tudo funcionando:

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
IG_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')

# Teste: Buscar informações da conta
response = requests.get(
    f"https://graph.facebook.com/v21.0/{IG_ACCOUNT_ID}",
    params={
        "fields": "username,profile_picture_url,followers_count,media_count",
        "access_token": ACCESS_TOKEN
    }
)

if response.status_code == 200:
    data = response.json()
    print("✅ Autenticação funcionando!")
    print(f"Username: {data.get('username')}")
    print(f"Followers: {data.get('followers_count')}")
    print(f"Posts: {data.get('media_count')}")
else:
    print(f"❌ Erro: {response.status_code}")
    print(response.json())
```

---

## 📝 Resumo das Credenciais

Ao final, você deve ter:

```
✅ Instagram Business Account ID: 17841400000000000
✅ Facebook Page ID: 123456789012345
✅ Meta App ID: 123456789012345
✅ Meta App Secret: abc123...
✅ Access Token (Long-Lived): EAABwzLix...
✅ Instagram Username: @vem.sm
```

---

## ⚠️ Notas Importantes

### Renovação de Token
- **Short-lived token**: expira em 1 hora
- **Long-lived token**: expira em 60 dias
- Implementar renovação automática antes de expirar

### App Review
- Para produção com múltiplos usuários, pode ser necessário **App Review**
- Para uso próprio (1 conta), não precisa de aprovação

### Sandbox vs Produção
- App começa em modo **Development** (sandbox)
- Funciona normalmente para admins/testadores do app
- Para lançar publicamente, precisa passar para **Live** (requer App Review)

### Rate Limits
- **100 posts por 24 horas** por conta Instagram
- Use `/{IG_ACCOUNT_ID}/content_publishing_limit` para monitorar

---

## 🆘 Problemas Comuns

### "Conta Instagram não é Business"
→ Volte à Etapa 1 e converta para Business/Creator

### "Não encontro opção para conectar Instagram"
→ Certifique-se que a Facebook Page está ativa e você é admin

### "Erro de permissões ao gerar token"
→ Verifique se adicionou todas as permissões na Etapa 5

### "Instagram Account ID não aparece"
→ Instagram pode não estar conectado corretamente à Page (Etapa 3)

---

## ✅ Próximos Passos

Após completar a configuração:

1. Implementar `InstagramGraphAPIService` no código
2. Atualizar `InstagramPosterAgent` para usar API oficial
3. Testar publicação de teste
4. Migrar de `instagrapi` para API oficial
5. Implementar renovação automática de tokens

---

## 📚 Links Úteis

- [Meta for Developers](https://developers.facebook.com/)
- [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
- [Instagram Graph API Docs](https://developers.facebook.com/docs/instagram-api/)
- [App Dashboard](https://developers.facebook.com/apps/)

---

**Tempo total**: ~40 minutos  
**Dificuldade**: Intermediária  
**Custo**: Gratuito
