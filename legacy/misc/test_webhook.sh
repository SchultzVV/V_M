#!/bin/bash

echo "🧪 Testando Webhook do Mercado Livre"
echo "======================================"
echo ""

# 1. Testa health check
echo "1️⃣ Testando health check..."
curl -s http://localhost:5000/webhook/health | jq .
echo ""
echo ""

# 2. Testa webhook com produto fictício
echo "2️⃣ Testando webhook com produto fictício do Mercado Livre..."
curl -X POST http://localhost:5000/webhook/mercadolivre \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "items",
    "resource": "https://api.mercadolibre.com/items/MLB1234567890",
    "user_id": "123456",
    "application_id": "3186869212482819"
  }' | jq .

echo ""
echo ""

# 3. Testa endpoint de teste
echo "3️⃣ Testando endpoint de teste..."
curl -X POST http://localhost:5000/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "marketplace": "mercadolivre",
    "test": true,
    "message": "Teste de integração do webhook"
  }' | jq .

echo ""
echo ""
echo "✅ Testes concluídos!"
echo ""
echo "💡 Para testar com um produto real:"
echo "   1. Cadastre um produto com external_id usando make prepare-products"
echo "   2. Use o MLB ID real do Mercado Livre"
echo "   3. Configure o webhook no painel: https://developers.mercadolivre.com.br"
