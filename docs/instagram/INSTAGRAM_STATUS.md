# Status Atual: Instagram Auto-Posting

## 📊 Situação Atual

### ✅ O que foi implementado

1. **Arquitetura completa**:
   - ✅ 3 Agentes LangChain (Decisor, Enriquecedor, Postador)
   - ✅ LangGraph Orchestrator
   - ✅ Redis para cache/memória
   - ✅ OpenCV para geração de imagens com preços
   - ✅ 10 rotas Flask REST
   - ✅ Sistema de controle `.posted` (similar ao `.processed`)

2. **Infraestrutura**:
   - ✅ Docker Compose com Redis
   - ✅ Makefile com 7 comandos
   - ✅ Documentação completa (8 arquivos MD)

3. **Testes**:
   - ✅ Modo simulação funciona perfeitamente (`make insta-test`)
   - ✅ Imagens geradas com preço overlay (OpenCV)
   - ✅ Produtos selecionados do staging corretamente

### ❌ O que NÃO funciona

1. **Problema principal**: Autenticação Instagram via `instagrapi`
   - Erro: `{"message":"login_required","status":"fail"}`
   - Instagram bloqueia login automatizado (viola TOS)
   - `make insta-publish` falha

2. **Método usado atualmente**:
   - ❌ `instagrapi` (biblioteca não oficial)
   - ❌ Login direto com user/senha
   - ❌ Contra os Termos de Serviço do Instagram
   - ❌ Alto risco de ban/bloqueio da conta

---

## 🎯 Solução: Migrar para API Oficial

### Por que migrar?

| Aspecto | instagrapi (atual) | Instagram Graph API (oficial) |
|---------|-------------------|-------------------------------|
| Status | ❌ Não oficial | ✅ Oficial Meta |
| Risco de ban | 🔴 Alto | 🟢 Zero |
| Estabilidade | 🟡 Quebra com atualizações | 🟢 Estável |
| Suporte | Comunidade | Meta Developer Support |
| Conformidade TOS | ❌ Viola | ✅ Permitido |

### Requisitos para API Oficial

1. **Instagram Business Account** (não funciona com conta pessoal)
2. **Conectar a uma Facebook Page**
3. **App registrado no Meta for Developers**
4. **Access Token via OAuth**

---

## 📋 Plano de Ação

### Fase 1: Configuração Manual (30-40 min) - VOCÊ FAZ

Siga o guia: `services/site/docs/SETUP_INSTAGRAM_BUSINESS.md`

**Tarefas**:
- [ ] Converter Instagram para Business Account
- [ ] Criar Facebook Page
- [ ] Conectar Instagram à Facebook Page
- [ ] Criar App no Meta for Developers
- [ ] Obter Access Token (long-lived)
- [ ] Obter Instagram Business Account ID
- [ ] Adicionar credenciais ao `.env`

**Resultado esperado**: 
```bash
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400000000000
INSTAGRAM_ACCESS_TOKEN=EAABwzLix...
FACEBOOK_PAGE_ID=123456789012345
META_APP_ID=123456789012345
META_APP_SECRET=abc123...
```

### Fase 2: Implementação (EU FAÇO)

Após você completar a Fase 1, eu vou implementar:

**Tarefas**:
- [ ] Criar `InstagramGraphAPIService` (API oficial)
- [ ] Atualizar `InstagramPosterAgent` para usar nova API
- [ ] Implementar upload de imagens com URL pública (MinIO)
- [ ] Criar container → Publicar container
- [ ] Manter sistema `.posted` para controle
- [ ] Remover dependência de `instagrapi`
- [ ] Atualizar testes

**Código novo**:
```
services/site/services/
  └── instagram_graph_api_service.py  # Novo serviço oficial

services/site/agents/
  └── instagram_poster_agent.py       # Atualizar para usar API oficial
```

### Fase 3: Testes e Validação

- [ ] Testar criação de container
- [ ] Testar publicação real
- [ ] Validar rate limits (100 posts/24h)
- [ ] Verificar integração com `make insta-publish`
- [ ] Confirmar `.posted` funcionando

---

## 🔄 Comparação: Fluxo Atual vs Novo Fluxo

### Fluxo Atual (instagrapi - NÃO FUNCIONA)

```
┌─────────────────────────────────────────────┐
│ 1. Produto do staging                       │
│ 2. Gerar imagem com OpenCV                  │
│ 3. Login Instagram (user/senha)             │ ❌ BLOQUEADO
│ 4. instagrapi.photo_upload()                │
└─────────────────────────────────────────────┘
```

### Novo Fluxo (Instagram Graph API - OFICIAL)

```
┌─────────────────────────────────────────────┐
│ 1. Produto do staging                       │
│ 2. Gerar imagem com OpenCV                  │
│ 3. Upload imagem → MinIO (URL pública)      │
│ 4. POST /{IG_ID}/media (criar container)    │ ✅ OFICIAL
│ 5. POST /{IG_ID}/media_publish (publicar)   │ ✅ OFICIAL
│ 6. Salvar em .posted                        │
└─────────────────────────────────────────────┘
```

**Diferença chave**: Não precisa de login! Usa Access Token OAuth.

---

## 📁 Arquivos Criados para Você

### Documentação

1. **INSTAGRAM_API_OFICIAL.md**
   - Explica a API oficial
   - Comparação instagrapi vs API oficial
   - Requisitos e limitações
   - Fluxo de publicação

2. **SETUP_INSTAGRAM_BUSINESS.md**
   - Guia passo a passo (30-40 min)
   - Print-like instructions
   - Troubleshooting
   - Como obter todas as credenciais

### Estrutura Nova

```
services/site/
├── insta_staging/           # ✅ CRIADO - Similar ao staging/
│   └── .posted             # ✅ CRIADO - Lista de produtos postados
└── agents/
    └── product_decision_agent.py  # ✅ ATUALIZADO - Usa .posted
```

### Comandos Makefile (já existem)

```bash
make insta-test      # Simula post (funciona)
make insta-publish   # Post real (aguardando API oficial)
make insta-status    # Status de posts
make insta-history   # Histórico
```

---

## 🎬 Próxima Ação Imediata

### Para VOCÊ (Usuário):

1. Leia: `services/site/docs/SETUP_INSTAGRAM_BUSINESS.md`
2. Execute as 9 etapas do guia (30-40 min)
3. Me envie as credenciais que obtiver:
   ```
   INSTAGRAM_BUSINESS_ACCOUNT_ID=?
   INSTAGRAM_ACCESS_TOKEN=?
   FACEBOOK_PAGE_ID=?
   META_APP_ID=?
   META_APP_SECRET=?
   ```

### Para MIM (Agente):

Assim que você me passar as credenciais, eu implemento:
- InstagramGraphAPIService
- Integração com MinIO para URLs públicas
- Atualização do InstagramPosterAgent
- Testes completos

---

## ⏱️ Estimativa de Tempo

- **Sua parte (manual)**: 30-40 minutos
- **Minha parte (código)**: ~2-3 horas
- **Testes**: 30 minutos
- **Total**: ~4 horas para sistema 100% funcional

---

## 📌 Status Summary

```
✅ Sistema completo implementado (agentes, rotas, infra)
✅ Modo simulação funcionando
✅ Sistema .posted criado
✅ Documentação completa
❌ Autenticação Instagram bloqueada (instagrapi)
🔄 Aguardando configuração API oficial
🚀 Pronto para migrar assim que credenciais estiverem disponíveis
```

---

## 📚 Arquivos para Ler (nesta ordem)

1. `INSTAGRAM_STATUS.md` (este arquivo) - Visão geral
2. `services/site/docs/INSTAGRAM_API_OFICIAL.md` - Entender a solução
3. `services/site/docs/SETUP_INSTAGRAM_BUSINESS.md` - Fazer configuração
4. Depois me avise que está pronto! 🚀
