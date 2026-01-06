# 🔄 Sincronização Manual de Produtos

Sistema de sincronização **SEM webhooks** - você controla quando atualizar!

## 🎯 Conceito

Ao invés de depender de webhooks (que precisam de servidor público), você:

1. **Cadastra produtos manualmente** (com external_id)
2. **Chama o endpoint de sincronização** quando quiser atualizar
3. **Sistema busca dados atualizados** na API do Mercado Livre
4. **Atualiza banco + JSON de staging** automaticamente

## 📡 Endpoints Disponíveis

### 1. Status da Sincronização
```bash
GET /sync/mercadolivre/status
```

Retorna:
```json
{
  "platform": "mercadolivre",
  "total_products": 5,
  "authenticated": true,
  "ready_to_sync": true
}
```

### 2. Sincronizar UM Produto
```bash
POST /sync/mercadolivre/product/<MLB_ID>

# Exemplo:
curl -X POST http://localhost:5000/sync/mercadolivre/product/MLB1234567890
```

Atualiza:
- ✅ Preço atual
- ✅ Preço original (desconto)
- ✅ Disponibilidade
- ✅ Imagens
- ✅ Link
- ✅ JSON de staging

### 3. Sincronizar TODOS os Produtos
```bash
POST /sync/mercadolivre/all

# Exemplo:
curl -X POST http://localhost:5000/sync/mercadolivre/all
```

Sincroniza todos os produtos com `external_id` do Mercado Livre.

## 🚀 Como Usar

### Opção 1: Script Interativo (Recomendado)

```bash
./sync_products.sh
```

Menu interativo:
```
1) Sincronizar UM produto específico
2) Sincronizar TODOS os produtos
3) Sair
```

### Opção 2: Comandos Diretos

```bash
# Status
curl http://localhost:5000/sync/mercadolivre/status | jq .

# Um produto
curl -X POST http://localhost:5000/sync/mercadolivre/product/MLB3704497069 | jq .

# Todos
curl -X POST http://localhost:5000/sync/mercadolivre/all | jq .
```

### Opção 3: Cron Job (Automático)

```bash
# Edite o crontab
crontab -e

# Adicione (atualiza todo dia às 3h da manhã):
0 3 * * * curl -X POST http://localhost:5000/sync/mercadolivre/all
```

## 📋 Fluxo Completo

### 1. Cadastrar Produto com External ID

```bash
# Gere o JSON
make prepare-products
```

Preencha:
```
Plataforma: mercadolivre
External ID: MLB3704497069  ← IMPORTANTE!
Título: AirFryer Philips 1900W
Preço: 299.90
...
```

### 2. Upload Inicial

```bash
docker-compose exec site python scripts/stage_products.py
```

Produto agora está no banco com `external_id = "MLB3704497069"`

### 3. Fazer Login no ML (uma vez)

```bash
# Abra no navegador
open http://localhost:5000/auth/mercadolivre/login

# Autorize e pronto!
```

### 4. Sincronizar Quando Quiser

```bash
# Hoje
./sync_products.sh

# Amanhã
./sync_products.sh

# Toda semana
# (ou configure cron job)
```

## ⏰ Quando Sincronizar?

**Manualmente:**
- Antes de publicar novos produtos
- Quando souber que o preço mudou
- Uma vez por dia/semana

**Automaticamente (Cron):**
```bash
# A cada 6 horas
0 */6 * * * curl -X POST http://localhost:5000/sync/mercadolivre/all

# Todo dia às 8h
0 8 * * * curl -X POST http://localhost:5000/sync/mercadolivre/all

# Toda segunda-feira às 9h
0 9 * * 1 curl -X POST http://localhost:5000/sync/mercadolivre/all
```

## 🆚 Comparação: Webhook vs Manual

| Aspecto | Webhook | Manual/Sync |
|---------|---------|-------------|
| **Servidor público** | ✅ Obrigatório | ❌ Não precisa |
| **URL fixa** | ✅ Obrigatório | ❌ Não precisa |
| **Atualização** | ⚡ Instantânea | ⏰ Quando você quiser |
| **Complexidade** | 🔴 Alta | 🟢 Baixa |
| **Custo** | 💰 Servidor | 💚 Grátis (localhost) |
| **Controle** | 🤖 Automático | 👤 Manual |
| **Ideal para** | Produção | Desenvolvimento/Pequeno porte |

## ✅ Vantagens do Sistema Manual

1. **Sem servidor público** - Roda em localhost
2. **Sem ngrok/domínio** - Não precisa URL fixa
3. **Você controla** - Atualiza quando quiser
4. **Mais simples** - Menos infraestrutura
5. **Grátis** - Sem custos de servidor

## 🎯 Exemplo Real

```bash
# 1. Fazer login (uma vez)
open http://localhost:5000/auth/mercadolivre/login

# 2. Cadastrar produto com MLB ID
# external_id: MLB3704497069

# 3. Sincronizar
curl -X POST http://localhost:5000/sync/mercadolivre/product/MLB3704497069

# Resposta:
{
  "status": "success",
  "message": "Produto atualizado com sucesso",
  "result": {
    "product_id": "abc-123",
    "external_id": "MLB3704497069",
    "title": "AirFryer Philips",
    "preco": 249.90,      ← Atualizado!
    "desconto": 50.0,     ← Calculado!
    "disponivel": true    ← Verificado!
  }
}
```

## 🚀 Resumo

✅ **Não precisa de webhook!**  
✅ **Funciona 100% em localhost**  
✅ **Sincronização manual ou via cron**  
✅ **Mesma funcionalidade, mais simples**  

**Webhooks são opcionais** - use apenas se precisar de atualização instantânea em produção!
