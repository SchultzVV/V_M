# V&M Site

Este repositório contém o site Flask e scripts auxiliares. Agora há integração com dois microserviços de IA para ingestão de URLs e perguntas via chat.

## Como subir o ambiente

Para desenvolvimento utilize:

```bash
make up
```

Para executar usando a imagem publicada no GitHub Container Registry:

```bash
make prd-up-ghcr
```

### Acessando a página de IA

Com o ambiente no ar abra `http://localhost:5000/ai`.
Nela você encontra:

- **Formulário de Ingestão**: informe uma URL e clique em **Ingerir URL** para que o serviço `ingestion_service` processe o conteúdo.
- **Chat de Perguntas**: envie perguntas que serão encaminhadas ao `retrieval_service` e veja as respostas em uma caixa de histórico.

### Testando via curl

```bash
curl -X POST http://localhost:5000/ingest-url -H 'Content-Type: application/json' -d '{"url": "https://exemplo.com"}'

curl -X POST http://localhost:5000/query -H 'Content-Type: application/json' -d '{"question": "qual a data de matrícula?"}'
```

### Executando testes

```bash
make test-unit
```

## Product staging pipeline

```mermaid
%% see docs/pipeline.mmd for an editable version
flowchart LR
    A[generate_staging_json.py] --> B[Staging JSON]
    B --> C[stage_products.py]
    C --> D[Upload images to MinIO]
    D --> E[POST /add_product]
    E --> F[add_product route]
    F --> G[save_product()]
    G --> H[(PostgreSQL)]
    H --> I[/api/products]
    I --> J[Frontend]
```

### Escalabilidade futura

- Substituir `requests` por **gRPC** para comunicação entre serviços.
- Adicionar **WebSocket** para chat em tempo real.
- Processar ingestão de forma assíncrona com **Celery** ou **FastAPI BackgroundTasks**.
- Migrar o frontend para **React** ou **HTMX** com suporte a polling.
- Disponibilizar facilmente via **ngrok** com `make serve-ngrok`.
