"""
Sistema de Postagem Automática Instagram - Diagrama Visual
"""

SYSTEM_ARCHITECTURE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SISTEMA DE POSTAGEM AUTOMÁTICA INSTAGRAM                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRADA (TRIGGER)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              [make stage]                    [API: /instagram/post]
                    │                                   │
                    │           ┌───────────────────────┘
                    │           │
                    ▼           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGING DIRECTORY                                    │
│  creatina-monohidratada_20260113.json                                       │
│  guarda-roupa-casal_20260113.json                                           │
│  robo-aspirador_20250717.json                                               │
│  ... (mais produtos)                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
╔═════════════════════════════════════════════════════════════════════════════╗
║                      LANGGRAPH ORCHESTRATOR                                  ║
║                   (instagram_orchestrator.py)                                ║
╚═════════════════════════════════════════════════════════════════════════════╝
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   │
       ╔════════════════════════════╗                  │
       ║   AGENTE 1: DECISOR       ║                  │
       ║ (product_decision_agent)  ║                  │
       ╚════════════════════════════╝                  │
                    │                                   │
       ┌────────────┴─────────────┐                    │
       │                          │                    │
       │  • Analisa produtos      │                    │
       │  • Filtra por tags       │                    │
       │  • Verifica histórico    │◄───────────────────┤
       │  • Usa LLM para decidir  │                    │
       │                          │                 [Redis]
       └────────────┬─────────────┘              Cache & Memory
                    │                                   │
                    ▼                                   │
          [Produto Selecionado]                         │
                    │                                   │
                    ▼                                   │
       ╔════════════════════════════╗                  │
       ║   AGENTE 2: ENRIQUECEDOR  ║                  │
       ║ (product_enricher_agent)  ║                  │
       ╚════════════════════════════╝                  │
                    │                                   │
       ┌────────────┴─────────────┐                    │
       │                          │                    │
       │  • Gera legenda (LLM)    │                    │
       │  • Cria hashtags         │◄───────────────────┤
       │  • Define CTA            │                    │
       │  • Sugestões visuais     │                    │
       │                          │                    │
       └────────────┬─────────────┘                    │
                    │                                   │
                    ▼                                   │
         [Produto Enriquecido]                          │
                    │                                   │
                    ▼                                   │
       ╔════════════════════════════╗                  │
       ║   AGENTE 3: POSTADOR      ║                  │
       ║ (instagram_poster_agent)  ║                  │
       ╚════════════════════════════╝                  │
                    │                                   │
       ┌────────────┴─────────────┐                    │
       │                          │                    │
       │  • Gera imagem (Pillow)  │                    │
       │  • Adiciona overlays     │                    │
       │  • Posta (instagrapi)    │◄───────────────────┘
       │  • Registra histórico    │
       │                          │
       └────────────┬─────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │  Instagram API   │
          │  (instagrapi)    │
          └──────────┬───────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SAÍDA (OUTPUT)                                  │
│                                                                              │
│  ✅ Post criado no Instagram                                                │
│  📸 URL: https://instagram.com/p/ABC123                                     │
│  💾 Salvo no histórico (Redis)                                              │
│  📊 Métricas disponíveis via API                                            │
└─────────────────────────────────────────────────────────────────────────────┘

"""

COMPONENTS_DETAIL = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           COMPONENTES DO SISTEMA                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────┐
│    BaseAgent (SOLID)     │  ← Classe abstrata base
│  • execute()             │
│  • _save_to_memory()     │
│  • _check_cache()        │
│  • _save_to_cache()      │
└────────────┬─────────────┘
             │
      ┌──────┴──────┬──────────────┐
      │             │              │
      ▼             ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Decisor  │  │Enriquec. │  │ Postador │
└──────────┘  └──────────┘  └──────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         TECNOLOGIAS UTILIZADAS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  🤖 LangChain          → Framework de agentes IA                            │
│  🔀 LangGraph          → Orquestração de workflows                          │
│  🧠 OpenAI GPT         → Modelos de linguagem                               │
│  🗄️  Redis              → Cache semântico e memória                         │
│  🖼️  Pillow             → Geração de imagens                                │
│  📸 instagrapi         → Instagram API                                      │
│  🐍 Flask              → Web framework                                       │
│  🐳 Docker             → Containerização                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLUXO DE DADOS (JSON)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Staging JSON                                                                │
│  {                                                                           │
│    "title": "Produto X",                                                     │
│    "price": 199.90,                                                          │
│    "images_local": "uploads/produto-x"                                       │
│  }                                                                           │
│         ↓                                                                    │
│  Enriquecido                                                                 │
│  {                                                                           │
│    ...staging_data,                                                          │
│    "caption": "🔥 Produto X por apenas R$ 199,90!",                         │
│    "hashtags": ["#oferta", "#deal"],                                         │
│    "call_to_action": "🛒 Link na bio"                                       │
│  }                                                                           │
│         ↓                                                                    │
│  Post Result                                                                 │
│  {                                                                           │
│    "success": true,                                                          │
│    "post_url": "https://instagram.com/p/ABC123",                             │
│    "media_id": "123456789"                                                   │
│  }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
"""

REDIS_KEYS = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        ESTRUTURA DE DADOS - REDIS                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│  KEY: agent:product_decision:memory                                          │
│  TYPE: List (LPUSH/LRANGE)                                                   │
│  DESC: Memória do agente decisor (últimas 100 interações)                   │
│  EXAMPLE:                                                                    │
│    [                                                                         │
│      {"timestamp": "2026-01-18T10:30:00", "product_id": "MLB123"},          │
│      {"timestamp": "2026-01-18T09:15:00", "product_id": "MLB456"}           │
│    ]                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  KEY: cache:product_enricher:{md5_hash}                                      │
│  TYPE: String (GET/SETEX)                                                    │
│  TTL: 86400 (24 horas)                                                       │
│  DESC: Cache de enriquecimento de produto                                    │
│  EXAMPLE:                                                                    │
│    {                                                                         │
│      "caption": "🔥 Produto...",                                            │
│      "hashtags": ["#oferta"],                                                │
│      "enriched_at": "2026-01-18T10:30:00"                                    │
│    }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  KEY: instagram:posted_products                                              │
│  TYPE: List (LPUSH/LRANGE)                                                   │
│  DESC: IDs dos produtos já postados (evita duplicação)                       │
│  SIZE: Últimos 500 produtos                                                  │
│  EXAMPLE:                                                                    │
│    ["MLB19571567", "MLB19571566", "MLB19571565", ...]                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  KEY: instagram:post_history                                                 │
│  TYPE: List (LPUSH/LRANGE)                                                   │
│  DESC: Histórico completo de posts                                           │
│  SIZE: Últimos 1000 posts                                                    │
│  EXAMPLE:                                                                    │
│    [                                                                         │
│      {                                                                       │
│        "product_id": "MLB123",                                               │
│        "post_url": "https://instagram.com/p/ABC",                            │
│        "posted_at": "2026-01-18T10:30:00"                                    │
│      }                                                                       │
│    ]                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
"""

if __name__ == "__main__":
    print(SYSTEM_ARCHITECTURE)
    print("\n" + "="*80 + "\n")
    print(COMPONENTS_DETAIL)
    print("\n" + "="*80 + "\n")
    print(REDIS_KEYS)
