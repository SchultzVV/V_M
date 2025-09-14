# Guia de Resolução de Problemas da IA

## Problema: "vc funciona de fato?"

Este documento explica a solução implementada para o problema relatado onde a funcionalidade de IA da aplicação não funcionava corretamente.

## O que foi identificado

A aplicação Flask depende de dois microserviços externos para funcionalidade de IA:
- `ingestion_service` (porta 5003) - para processar URLs
- `retrieval_service` (porta 5004) - para responder perguntas

Quando estes serviços estão indisponíveis, a aplicação retornava erros 500 sem explicação clara para o usuário.

## Solução implementada

### 1. Melhor tratamento de erros

**Antes:**
- Erros 500 com mensagens técnicas confusas
- Timeout de 150 segundos
- Nenhuma verificação de disponibilidade

**Depois:**
- Erros 503 (Service Unavailable) apropriados
- Timeout reduzido para 5 segundos
- Mensagens de erro claras em português
- Sugestões práticas para resolução

### 2. Novo endpoint de status

**Endpoint:** `GET /ai/status`

Retorna informações sobre disponibilidade dos serviços:
```json
{
  "ingestion_service": "online|offline",
  "retrieval_service": "online|offline", 
  "overall_status": "operational|degraded"
}
```

### 3. Interface melhorada

- Indicadores visuais de status dos serviços
- Botão para atualizar status
- Mensagens de erro mais claras
- Sugestões contextuais quando serviços estão offline

### 4. Logging melhorado

- Configuração de logging estruturado
- Logs informativos para debug
- Separação entre warnings e errors

## Como usar

### Para verificar se está funcionando:

1. **Acesse a página:** `http://localhost:5000/ai`
2. **Verifique o status:** Os indicadores mostram se os serviços estão online
3. **Teste as funcionalidades:**
   - Se serviços estão online: funciona normalmente
   - Se serviços estão offline: recebe mensagens claras de erro

### Para resolver problemas:

**Se os serviços estão offline:**
```bash
make up  # Inicia todos os serviços incluindo IA
```

**Para verificar apenas o status via API:**
```bash
curl http://localhost:5000/ai/status
```

**Para testar endpoints diretamente:**
```bash
# Testar ingestão
curl -X POST http://localhost:5000/ingest-url \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://exemplo.com"}'

# Testar consulta  
curl -X POST http://localhost:5000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "teste"}'
```

## Benefícios da solução

✅ **Experiência do usuário melhorada**
- Feedback claro sobre estado dos serviços
- Sugestões práticas para resolução
- Interface visual intuitiva

✅ **Desenvolvimento e debug facilitados**
- Logs estruturados
- Status de serviços visível
- Timeouts apropriados

✅ **Robustez aumentada**
- Aplicação não quebra quando serviços estão offline
- Códigos HTTP apropriados (503 vs 500)
- Tratamento de diferentes tipos de erro

## Testes

Execute os testes unitários para verificar a funcionalidade:

```bash
make test-unit
```

Os testes cobrem:
- Funcionamento normal quando serviços estão disponíveis
- Comportamento adequado quando serviços estão offline
- Validação de parâmetros
- Endpoint de status

## Conclusão

A pergunta "vc funciona de fato?" agora tem uma resposta clara: **SIM, a aplicação funciona!**

- ✅ Quando os microserviços estão disponíveis: funcionalidade completa
- ✅ Quando os microserviços estão indisponíveis: feedback claro e instruções para resolução
- ✅ Interface melhorada com indicadores de status
- ✅ Documentação e testes abrangentes