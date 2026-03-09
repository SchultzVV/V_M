# Instagram API Oficial - Melhores Práticas

## 📋 Resumo Executivo

A **prática oficial e recomendada** pela Meta para publicar no Instagram é usar a **Instagram Graph API** (também chamada de Content Publishing API).

### ❌ O que NÃO fazer (método atual - instagrapi)
- **Login direto com usuário/senha**: Viola os termos de serviço do Instagram
- **Web scraping ou automação não oficial**: Conta pode ser banida
- **Bibliotecas não oficiais (instagrapi, instabot, etc.)**: Alto risco de bloqueio

### ✅ O que fazer (método oficial)

Usar a **Instagram Graph API** que requer:

1. **Instagram Business ou Creator Account** (não funciona com contas pessoais)
2. **Conta conectada a uma Facebook Page**
3. **App registrado no Meta for Developers**
4. **Access Token via Facebook Login/OAuth**

---

## 🔐 Requisitos Oficiais

### 1. Tipo de Conta
- ✅ Instagram Business Account
- ✅ Instagram Creator Account  
- ❌ Instagram Personal Account (não suportado)

### 2. Conectar ao Facebook
- Vincular Instagram Business/Creator a uma **Facebook Page**
- A página precisa ter permissões de publicação

### 3. App no Meta for Developers
1. Criar app em: https://developers.facebook.com/apps/
2. Adicionar produto: **Instagram Graph API**
3. Configurar permissões:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`

### 4. Obter Access Token
- Usar **Facebook Login** para autenticar
- Usuário autoriza o app
- App recebe **long-lived access token** (válido por 60 dias)
- Token pode ser renovado automaticamente

---

## 🚀 Fluxo de Publicação Oficial

### Passo 1: Criar Container
```bash
POST https://graph.facebook.com/v21.0/{IG_USER_ID}/media
Content-Type: application/json
Authorization: Bearer {ACCESS_TOKEN}

{
  "image_url": "https://exemplo.com/imagem.jpg",
  "caption": "Legenda com #hashtags",
  "access_token": "{ACCESS_TOKEN}"
}

# Resposta:
{
  "id": "{IG_CONTAINER_ID}"
}
```

### Passo 2: Publicar Container
```bash
POST https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish
Content-Type: application/json
Authorization: Bearer {ACCESS_TOKEN}

{
  "creation_id": "{IG_CONTAINER_ID}",
  "access_token": "{ACCESS_TOKEN}"
}

# Resposta:
{
  "id": "{IG_MEDIA_ID}"  # Post publicado!
}
```

---

## 📊 Limitações

### Rate Limits
- **100 posts por conta a cada 24 horas** (janela móvel)
- Carrosséis contam como 1 post
- Usar `GET /{IG_USER_ID}/content_publishing_limit` para checar

### Formatos Suportados
- ✅ **Imagens**: JPEG apenas (1080x1080 recomendado)
- ✅ **Vídeos**: MP4, máx 100MB
- ✅ **Carrosséis**: até 10 mídias
- ✅ **Reels**: vídeos curtos verticais
- ✅ **Stories**: imagens/vídeos temporários (24h)
- ❌ **Filtros do Instagram**: não suportado via API
- ❌ **Shopping tags**: não suportado
- ❌ **Branded content tags**: não suportado

### Requisitos de Mídia
- Imagens/vídeos devem estar em **servidor público** (URL acessível)
- Instagram faz cURL da URL para baixar
- Usar MinIO/S3 com URLs públicas temporárias

---

## 🔧 Implementação Recomendada

### Arquitetura Sugerida

```
┌─────────────────────────────────────────────────────────────┐
│                    Nossa Aplicação Flask                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Produto do Staging → Gerar Imagem (OpenCV)              │
│  2. Upload Imagem → MinIO com URL pública temporária        │
│  3. Create Container → Instagram Graph API                  │
│  4. Publish Container → Instagram Graph API                 │
│  5. Salvar post_id em .posted                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │  Instagram Graph API v21.0  │
                │  graph.facebook.com         │
                └─────────────────────────────────┘
```

### Bibliotecas Python Recomendadas
```python
# Biblioteca oficial do Facebook
pip install facebook-sdk

# OU usar requests direto (recomendado para maior controle)
pip install requests
```

---

## 🎯 Próximos Passos

### Fase 1: Configuração (Manual - Uma Vez)
1. ✅ Converter conta Instagram para Business/Creator
2. ✅ Criar Facebook Page e conectar Instagram
3. ✅ Criar App no Meta for Developers
4. ✅ Implementar Facebook Login na aplicação
5. ✅ Obter e armazenar Access Token

### Fase 2: Implementação (Código)
1. ✅ Criar serviço `InstagramGraphAPIService`
2. ✅ Implementar upload de imagem com URL pública (MinIO)
3. ✅ Implementar criação de container
4. ✅ Implementar publicação
5. ✅ Atualizar orquestrador para usar API oficial
6. ✅ Manter sistema .posted para controle

### Fase 3: Melhorias
1. ✅ Renovação automática de access token
2. ✅ Retry logic com exponential backoff
3. ✅ Monitoramento de rate limits
4. ✅ Suporte a carrosséis (múltiplas imagens)
5. ✅ Suporte a Reels

---

## 📚 Referências Oficiais

- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api/)
- [Content Publishing Guide](https://developers.facebook.com/docs/instagram-api/guides/content-publishing)
- [Get Started](https://developers.facebook.com/docs/instagram-api/getting-started)
- [API Reference](https://developers.facebook.com/docs/instagram-api/reference)
- [Rate Limits](https://developers.facebook.com/docs/instagram-api/overview#rate-limiting)

---

## ⚠️ Avisos Importantes

1. **Contas Pessoais**: A API oficial NÃO funciona com contas Instagram pessoais
2. **Aprovação do App**: Pode ser necessário passar por App Review da Meta para permissões avançadas
3. **Access Token**: Nunca commitar tokens no Git - usar variáveis de ambiente
4. **Testes**: Use conta de teste durante desenvolvimento

---

## 🆚 Comparação: instagrapi vs API Oficial

| Aspecto | instagrapi (atual) | Instagram Graph API (oficial) |
|---------|-------------------|-------------------------------|
| **Status** | Não oficial | Oficial Meta |
| **Termos de Serviço** | ❌ Viola TOS | ✅ Permitido |
| **Risco de Ban** | 🔴 Alto | 🟢 Nenhum |
| **Tipo de Conta** | Qualquer | Business/Creator apenas |
| **Autenticação** | User/pass | OAuth/Token |
| **Manutenção** | Quebra frequentemente | Estável |
| **Rate Limit** | Bloqueado facilmente | 100 posts/24h oficial |
| **Suporte** | Comunidade | Meta Developer Support |
| **Custo** | Grátis | Grátis |
| **Setup** | Simples | Requer configuração |

---

## 💡 Recomendação Final

**Migrar para Instagram Graph API o mais rápido possível** para:
- ✅ Evitar bloqueio/ban da conta
- ✅ Ter solução estável e confiável
- ✅ Estar em conformidade com os termos de serviço
- ✅ Ter suporte oficial em caso de problemas

A configuração inicial é mais complexa, mas vale muito a pena para uma solução em produção.
