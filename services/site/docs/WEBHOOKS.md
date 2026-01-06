# Sistema de Webhooks - Marketplaces

Sistema de integração automática com marketplaces via webhooks.

## 🎯 Conceito

**O webhook NÃO cria produtos novos!** Ele apenas **atualiza** produtos já cadastrados manualmente.

### Fluxo de trabalho:

1. **Você cadastra o produto manualmente** usando `generate_staging_json.py` e `stage_products.py`
2. **Você adiciona o `external_id`** (ID do produto no marketplace)
3. **O webhook atualiza automaticamente**:
   - ✅ Preço atual
   - ✅ Preço original (desconto)
   - ✅ Disponibilidade
   - ✅ Imagens
   - ✅ Link
   - ✅ Arquivo JSON de staging

## 📦 Endpoints Disponíveis

### Health Check
```bash
GET /webhook/health
```
Verifica se o serviço está ativo.

### Mercado Livre
```bash
POST /webhook/mercadolivre
```
Recebe notificações do Mercado Livre sobre:
- Novos itens publicados (`topic: items`)
- Atualizações de preço
- Mudanças de estoque
- Pedidos (`topic: orders`)
- Pagamentos (`topic: payments`)

**Exemplo de payload:**
```json
{
  "topic": "items",
  "resource": "https://api.mercadolibre.com/items/MLB123456789",
  "user_id": "123456",
  "application_id": "789012"
}
```

### Shopee
```bash
POST /webhook/shopee
```
Recebe notificações da Shopee sobre produtos e pedidos.

### Amazon
```bash
POST /webhook/amazon
```
Recebe notificações da Amazon SP-API.

### Testes
```bash
POST /webhook/test
```
Endpoint para simular webhooks durante desenvolvimento.

**Exemplo:**
```bash
curl -X POST http://localhost:5000/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "marketplace": "mercadolivre",
    "test": true,
    "data": {"message": "teste"}
  }'
```

## 📦 Configuração do Mercado Livre

### 1. Criar Aplicação no Mercado Livre
1. Acesse: https://developers.mercadolivre.com.br/devcenter
2. Crie uma nova aplicação
3. Anote o `APP_ID` e `SECRET_KEY`

### 2. Configurar Webhook no Painel
1. No painel da aplicação, vá em "Notificações"
2. Configure a URL do webhook:
   ```
   https://lojinhavem.ngrok.io/webhook/mercadolivre
   ```
3. Selecione os topics:
   - `items` (recomendado)
   - `orders` (opcional)
   - `payments` (opcional)

### 3. Variáveis de Ambiente
Adicione ao `.env` ou `docker-compose`:
```bash
ML_APP_ID=seu_app_id
ML_SECRET_KEY=sua_secret_key
ML_ACCESS_TOKEN=seu_access_token
```

### 4. Obter Access Token
```bash
# URL de autorização (substitua APP_ID)
https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=APP_ID&redirect_uri=https://lojinhavem.ngrok.io/callback

# Depois de autorizar, troque o code por token
curl -X POST https://api.mercadolibre.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=APP_ID" \
  -d "client_secret=SECRET_KEY" \
  -d "code=CODE_RECEBIDO" \
  -d "redirect_uri=https://lojinhavem.ngrok.io/callback"
```

## 🧪 Testar Webhook Localmente

### 1. Subir o servidor
```bash
make serve-ngrok
# ou
docker-compose up
```

### 2. Simular notificação do Mercado Livre
```bash
curl -X POST http://localhost:5000/webhook/mercadolivre \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "items",
    "resource": "https://api.mercadolibre.com/items/MLB1234567890",
    "user_id": "123456",
    "application_id": "789012"
  }'
```

### 3. Verificar logs
```bash
docker-compose logs -f site
```

## 🔄 Fluxo de Sincronização

```
[Cadastro Manual] → Banco de Dados + Staging JSON
                           ↓
              (produto tem external_id)
                           ↓
Mercado Livre → Webhook → Atualiza Banco + Staging JSON
                           ↓
                  Preço, Disponibilidade,
                  Imagens atualizados!
```

### Exemplo Completo

**1. Cadastro Manual:**
```bash
make prepare-products
```

Preencha os dados:
```
Plataforma: mercadolivre
ID do produto no marketplace: MLB1234567890  ← IMPORTANTE!
Título: AirFryer Philips 1900W
Preço atual: 299.90
Preço antigo: 499.90
Link: https://...
Produto disponível?: s
```

**2. Upload inicial:**
```bash
docker-compose exec site python scripts/stage_products.py
```

Produto agora está no banco com `external_id = "MLB1234567890"`

**3. Webhook automático:**

Mercado Livre envia notificação quando o preço muda:
```json
{
  "topic": "items",
  "resource": "https://api.mercadolibre.com/items/MLB1234567890"
}
```

**4. Sistema busca dados atualizados:**
```json
{
  "id": "MLB1234567890",
  "price": 249.90,        ← Novo preço!
  "original_price": 499.90,
  "status": "active",
  "available_quantity": 5
}
```

**5. Atualiza banco de dados:**
```python
Product.query.filter_by(
    platform="mercadolivre",
    external_id="MLB1234567890"
).update({
    "preco": "249.90",
    "desconto": 50.0,
    "disponivel": True
})
```

**6. Atualiza staging JSON:**
```json
{
  "platform": "mercadolivre",
  "external_id": "MLB1234567890",
  "title": "AirFryer Philips 1900W",
  "price": "R$ 249.90",  ← Atualizado!
  "oldPrice": "R$ 499.90",
  "disponivel": true,
  "ultima_atualizacao": "2026-01-02T10:30:00",
  "atualizado_via_webhook": true
}
```

## ⚠️ Importante

1. **Cadastro Manual Obrigatório:** Produtos DEVEM ser cadastrados manualmente primeiro
2. **External ID Obrigatório:** Sem `external_id`, o webhook não consegue identificar o produto
3. **Webhook = Atualização:** Webhook apenas atualiza, NÃO cria produtos novos
4. **Staging JSON:** É atualizado automaticamente junto com o banco
5. **Imagens:** Se o marketplace enviar novas imagens, elas substituem as antigas

## 🔧 Migração do Banco

Execute para adicionar novos campos:
```bash
docker-compose exec site python scripts/migrate_add_webhook_fields.py
```

Campos adicionados:
- `platform` - Origem (mercadolivre, shopee, amazon)
- `external_id` - ID do produto no marketplace
- `nome`, `preco`, `preco_original` - Aliases para compatibilidade
- `desconto` - Percentual calculado automaticamente
- `descricao` - Descrição completa
- `imagens` - Lista de URLs
- `created_at`, `updated_at` - Timestamps

## 📚 Documentação das APIs

- **Mercado Livre:** https://developers.mercadolivre.com.br/pt_br/notificacoes
- **Shopee:** https://open.shopee.com/documents/v2/v2.push.get_push_config
- **Amazon:** https://developer-docs.amazon.com/sp-api/docs/notifications-api-v1-reference

## ⚠️ Importante

1. **URL Pública:** Ngrok deve estar rodando com subdomain `lojinhavem`
2. **Headers:** Mercado Livre valida o endpoint antes de ativar
3. **Duplicatas:** Sistema usa `platform` + `external_id` como chave única
4. **Timeout:** Webhook deve responder em < 5 segundos
5. **Retry:** Mercado Livre reenvie notificações em caso de falha

## 🚀 Próximos Passos

1. ✅ Webhook Mercado Livre implementado (apenas atualização)
2. ✅ Sistema atualiza banco + staging JSON automaticamente
3. ⬜ Implementar autenticação OAuth do ML
4. ⬜ Adicionar logs de webhook em banco
5. ⬜ Webhook Shopee completo
6. ⬜ Webhook Amazon SP-API
7. ⬜ Dashboard de sincronização com status de atualização
8. ⬜ Notificações quando produto ficar indisponível

## 💡 Dicas

### Como verificar se um produto está sendo rastreado?

```bash
# No banco de dados
docker-compose exec postgres psql -U postgres -d postgres -c \
  "SELECT id, title, platform, external_id, preco, disponivel, updated_at FROM products WHERE external_id IS NOT NULL;"
```

### Como forçar atualização manual via API do ML?

```bash
curl -X POST http://localhost:5000/webhook/mercadolivre \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "items",
    "resource": "https://api.mercadolibre.com/items/MLB1234567890",
    "user_id": "123456",
    "application_id": "789012"
  }'
```

### Como adicionar external_id em produtos já cadastrados?

1. Edite o JSON de staging manualmente
2. Adicione o campo `"external_id": "MLB123456789"`
3. Execute `stage_products.py` novamente
4. O sistema atualizará o banco com o external_id
