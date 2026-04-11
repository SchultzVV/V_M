# 📖 DefineMe - services/site/agents/

## 🎯 Propósito da Pasta

Esta pasta contém **agentes LLM (Large Language Models)** baseados em LangChain e LangGraph que automatizam a postagem de produtos no Instagram. São agentes inteligentes que trabalham em conjunto para selecionar, enriquecer e postar produtos de forma autônoma.

## 🤖 Arquitetura de Agentes

### Sistema Multi-Agente

```
┌──────────────────────────────────────────────────────────┐
│         InstagramPostOrchestrator (LangGraph)            │
│                    (instagram_orchestrator.py)           │
└────┬──────────────────┬──────────────────┬──────────────┘
     │                  │                  │
     ▼                  ▼                  ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Agente 1  │  │   Agente 2  │  │   Agente 3  │
│   DECISOR   │  │ ENRIQUECEDOR│  │   POSTADOR  │
│             │  │             │  │             │
│ Escolhe o   │→ │ Melhora     │→ │ Publica no  │
│ produto     │  │ descrição   │  │ Instagram   │
│ ideal       │  │ e legenda   │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```

## 📂 Arquivos e Responsabilidades

### 🔵 `instagram_orchestrator.py`
**Orquestrador Principal** - Coordena todo o fluxo usando LangGraph.

**Responsabilidades:**
- Gerencia o estado do workflow
- Coordena a execução sequencial dos agentes
- Trata erros e fallbacks
- Mantém histórico de execução

**Estado do Grafo:**
```python
{
    # Inputs
    "filters": {"tag": "CD", "disponivel": True},
    "simulate": False,
    "custom_caption": "",
    "post_type": "carousel",
    
    # Outputs
    "selected_product": {...},
    "enriched_product": {...},
    "post_result": {...},
    
    # Controle
    "errors": [],
    "step": "product_selected"
}
```

**Fluxo do Workflow:**
```
┌─────────────────┐
│  Entry Point    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ decide_product  │  (Nó 1)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ enrich_product  │  (Nó 2)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ post_instagram  │  (Nó 3)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      END        │
└─────────────────┘
```

---

### 🟢 `product_decision_agent.py`
**Agente 1: Decisor de Produto**

**Função:** Escolhe qual produto será postado no Instagram.

**Critérios de Decisão:**
- ✅ Produtos disponíveis (`disponivel = true`)
- ✅ Não postados recentemente (evita duplicatas)
- ✅ Melhor desconto (maior % OFF)
- ✅ Mais imagens (melhor para carrossel)
- ✅ Filtros específicos (categoria, tag, etc)

**Fonte de dados:** JSONs de `staging/` (arquivos locais, não PostgreSQL)
**Histórico de postados:** arquivo `insta_staging/.posted` (não Redis)

**Lógica de Seleção:**
```python
# 1. Lê JSONs de staging/ via glob
# 2. Filtra produtos disponíveis
# 3. Remove já postados (checa insta_staging/.posted)
# 4. Ordena por desconto (maior primeiro)
# 5. Retorna o melhor candidato
```

**Output:**
```json
{
  "success": true,
  "selected_product": {
    "id": 42,
    "title": "Robô Aspirador 3 em 1",
    "price": "R$ 359,99",
    "oldPrice": "R$ 999,99",
    "discount_percentage": 64,
    "images": ["url1", "url2", ...],
    "tag": "CD",
    "subcategory": "sala"
  },
  "reason": "Melhor desconto (64%) e 8 imagens disponíveis"
}
```

---

### 🟡 `product_enricher_agent.py`
**Agente 2: Enriquecedor de Produto**

**Função:** Melhora a descrição e gera legenda otimizada para Instagram.

**Capacidades LLM:**
- 📝 Gera descrições persuasivas
- 🏷️ Adiciona hashtags relevantes
- ✨ Destaca benefícios do produto
- 💰 Enfatiza descontos e economia
- 🎯 Adapta linguagem para Instagram

**Prompt do LLM:**
```
Você é um especialista em marketing digital para Instagram.
Crie uma legenda envolvente para o seguinte produto:

Título: {title}
Preço: {price} (antes {oldPrice})
Desconto: {discount}%
Categoria: {categoria}

A legenda deve:
- Ser atraente e persuasiva
- Incluir 5-8 hashtags relevantes
- Destacar o desconto
- Ter call-to-action
- Máximo 2200 caracteres
```

**Output:**
```json
{
  "success": true,
  "enriched_product": {
    ...produto_original,
    "caption": "🏠 Transforme sua casa com tecnologia!\n\n🤖 Este Robô Aspirador é o sonho de toda casa moderna...\n\n💰 DE R$ 999,99 POR APENAS R$ 359,99\n🎉 Economia de 64%!\n\n🔗 Link na bio\n\n#CasaInteligente #RoboAspiradorDepo #TecnologiaEmCasa #Desconto #Promocao #LimpezaAutomatica #SmartHome #VidaPratica",
    "hashtags": ["#CasaInteligente", "#RoboAspiradorDepo", ...],
    "enhanced_description": "Robô aspirador 3 em 1 com 1200pa de sucção..."
  }
}
```

---

### 🔴 `instagram_poster_agent.py`
**Agente 3: Postador no Instagram**

**Função:** Realiza a publicação efetiva no Instagram via API oficial.

**Cliente Instagram:** `instagrapi` (lib não-oficial, autenticação via `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` — não usa OAuth)
**Image Generator:** `InstagramImageGenerator` de `services.instagram_image_service_cv2` (OpenCV)

**Processo:**
1. **Gera imagens:**
   - Carrossel: `image_generator.generate_carousel_images(product)`
   - Foto única: `image_generator.generate_product_image(product)`
   - Redimensiona para 1080x1080 via OpenCV
2. **Posta no Instagram:**
   - Usa `instagrapi.Client()` (lazy loading)
   - Se `instagrapi` não instalado → modo simulação automático
   - Publica photo ou carousel
3. **Registra histórico:**
   - Salva no Redis (lista `instagram_history`, 1000 entradas)
   - TTL configurável via `redis.setex`

**Modos de Operação:**

#### Modo Simulação (`simulate=True`)
```python
# Não posta de verdade, apenas simula
result = poster_agent.execute(product, simulate=True)

# Output:
{
  "success": True,
  "simulated": True,
  "post_id": "simulated_12345",
  "message": "Post simulado com sucesso"
}
```

#### Modo Produção (`simulate=False`)
```python
# Posta no Instagram de verdade
result = poster_agent.execute(product, simulate=False)

# Output:
{
  "success": True,
  "simulated": False,
  "post_id": "18123456789_123456789",
  "permalink": "https://instagram.com/p/ABC123/",
  "message": "Post publicado com sucesso"
}
```

---

## 🔄 Fluxo Completo de Execução

### Comando: `make instagram-post`

```
┌─────────────────────────────────────────────────┐
│  1. API Recebe Request                          │
│     POST /instagram/post/auto?simulate=false    │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  2. Orquestrador Inicializa                     │
│     InstagramPostOrchestrator()                 │
│     - Conecta Redis                             │
│     - Inicializa 3 agentes                      │
│     - Compila workflow LangGraph                │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  3. AGENTE DECISOR                              │
│     product_decision_agent.execute()            │
│                                                  │
│     • Lê JSONs de staging/ (arquivos locais)     │
│     • Filtra produtos disponíveis               │
│     • Checa insta_staging/.posted               │
│     • Seleciona melhor candidato                │
│                                                  │
│  Output: selected_product                       │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  4. AGENTE ENRIQUECEDOR                         │
│     product_enricher_agent.execute()            │
│                                                  │
│     • Recebe selected_product                   │
│     • Chama LLM (GPT-4 / Claude)                │
│     • Gera legenda otimizada                    │
│     • Adiciona hashtags                         │
│                                                  │
│  Output: enriched_product (com caption)         │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  5. AGENTE POSTADOR                             │
│     instagram_poster_agent.execute()            │
│                                                  │
│     • Baixa imagens do MinIO                    │
│     • Prepara imagens (1080x1080)               │
│     • Upload para Instagram API                 │
│     • Publica post/carousel                     │
│     • Salva histórico no Redis                  │
│                                                  │
│  Output: post_result (com post_id)              │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  6. Resposta Final                              │
│     {                                            │
│       "success": true,                          │
│       "product": {...},                         │
│       "post_id": "18123456...",                 │
│       "permalink": "https://instagram.com/p/...",│
│       "caption": "🏠 Transforme sua casa...",   │
│       "workflow_steps": ["decide", "enrich", "post"]│
│     }                                            │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Comandos Relacionados

### Publicar no Instagram

```bash
# Publicação automática (posta de verdade)
make instagram-post

# Teste (simulação, não posta)
make instagram-test

# Via API direta
curl -X POST "http://localhost:5000/instagram/post/auto?simulate=false"
```

### Verificar Status

```bash
# Status do sistema
make instagram-status

# Histórico de posts
make instagram-history

# Diagrama do workflow
make instagram-workflow
```

### Teste Completo

```bash
# Testa todos os componentes
make instagram-test-system
```

---

## 📊 Exemplo de Execução Real

### Console Output

```
🔗 Conectando ao Redis: redis://redis:6379
✅ Orquestrador Instagram inicializado

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Executando Agente Decisor de Produto...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Produtos disponíveis no banco: 15
🔍 Filtros aplicados: {'disponivel': True}
✅ Produtos após filtros: 12
⏭️  Produtos já postados (últimas 24h): 3
🎯 Candidatos finais: 9

✅ Produto selecionado: Robô Varredora Aspirador De Pó...
💰 Desconto: 64% OFF
🖼️  Imagens disponíveis: 8
📝 Motivo: Melhor desconto disponível (64%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Executando Agente Enriquecedor...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Gerando legenda com LLM (GPT-4)...
📝 Legenda gerada: 305 caracteres
🏷️  Hashtags: 8
✅ Enriquecimento completo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 Executando Agente Postador Instagram...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 Baixando 8 imagens do MinIO...
✅ Imagens baixadas: 8/8
🖼️  Preparando imagens para Instagram...
✅ Imagens preparadas: 8/8 (1080x1080)

📤 Modo: PRODUÇÃO (postagem real)
🎯 Tipo de post: carousel
📸 Uploading imagens para Instagram API...
   ✅ Imagem 1/8 uploaded
   ✅ Imagem 2/8 uploaded
   ...
   ✅ Imagem 8/8 uploaded

✅ POST PUBLICADO COM SUCESSO!
🆔 Post ID: 18123456789_987654321
🔗 Permalink: https://instagram.com/p/ABC123def/
💾 Histórico salvo no Redis

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WORKFLOW COMPLETO!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Produto: Robô Varredora Aspirador...
💰 Preço: R$ 359,99 (64% OFF)
📸 Post ID: 18123456789_987654321
🔗 https://instagram.com/p/ABC123def/

Total de etapas: 3
Duração: 8.3s
```

---

## 🛠️ Configuração

### Variáveis de Ambiente

```bash
# .env
REDIS_URL=redis://redis:6379
OPENAI_API_KEY=sk-...
INSTAGRAM_ACCESS_TOKEN=EAABsbC...
INSTAGRAM_ACCOUNT_ID=17841...
```

### Dependências

```python
# requirements-prd.txt
langchain>=0.1.0
langgraph>=0.0.20
openai>=1.0.0
redis>=4.5.0
pillow>=10.0.0
requests>=2.31.0
```

---

## 🔗 Links Relacionados

- [DefineMe Raiz](../../DefineMe.md) - Comandos make instagram-*
- [DefineMe Scripts](../scripts/DefineMe.md) - Scripts de preparação
- [MAPA_PASTAS.md](../../MAPA_PASTAS.md) - Estrutura completa
- [docs/INSTAGRAM_AUTO_POST.md](../docs/INSTAGRAM_AUTO_POST.md) - Documentação detalhada
