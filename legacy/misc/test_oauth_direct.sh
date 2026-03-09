#!/bin/bash
# Script para testar OAuth diretamente

source .env

echo "🔑 Teste OAuth Direto - Mercado Livre"
echo "======================================"
echo ""
echo "📋 Configuração:"
echo "   APP_ID: $ML_APP_ID"
echo "   REDIRECT_URI: $ML_REDIRECT_URI"
echo ""

# Construir URL de autorização
AUTH_URL="https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=${ML_APP_ID}&redirect_uri=${ML_REDIRECT_URI}"

echo "🌐 URL de Autorização Gerada:"
echo "$AUTH_URL"
echo ""
echo "📱 OPÇÕES:"
echo ""
echo "1️⃣  Copie a URL acima e cole em um navegador"
echo "2️⃣  Use o comando abaixo para abrir automaticamente:"
echo "    xdg-open '$AUTH_URL'"
echo ""
echo "✅ Após autorizar, você será redirecionado para:"
echo "   $ML_REDIRECT_URI?code=TG-..."
echo ""
echo "🔍 Para verificar os logs do callback:"
echo "   docker-compose logs -f site | grep callback"
