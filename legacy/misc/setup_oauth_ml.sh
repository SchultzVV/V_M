#!/bin/bash

echo "🔐 Configuração OAuth - Mercado Livre"
echo "======================================"
echo ""

# Verifica se o site está rodando
if ! docker ps | grep -q site-dev; then
    echo "🚀 Iniciando o site..."
    docker-compose up -d site
    sleep 5
else
    echo "✅ Site já está rodando"
fi

echo ""
echo "📋 PASSO 1: Configure no painel do Mercado Livre"
echo "   URL: https://developers.mercadolivre.com.br/devcenter"
echo ""
echo "   Adicione esta URL em 'Redirect URIs':"
echo "   👉 http://localhost:5000/auth/mercadolivre/callback"
echo ""
echo "   (Pressione ENTER quando estiver configurado)"
read -p ""

echo ""
echo "🌐 PASSO 2: Fazendo login..."
echo ""
echo "   Abrindo navegador em: http://localhost:5000/auth/mercadolivre/login"
echo ""

# Tenta abrir o navegador
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5000/auth/mercadolivre/login"
elif command -v open &> /dev/null; then
    open "http://localhost:5000/auth/mercadolivre/login"
else
    echo "   Copie e cole esta URL no navegador:"
    echo "   http://localhost:5000/auth/mercadolivre/login"
fi

echo ""
echo "   Aguardando autorização..."
echo "   (Pressione ENTER após autorizar no Mercado Livre)"
read -p ""

echo ""
echo "🔍 PASSO 3: Verificando autenticação..."
echo ""

STATUS=$(curl -s http://localhost:5000/auth/mercadolivre/status | jq -r '.status')

if [ "$STATUS" = "authenticated" ]; then
    echo "✅ SUCESSO! Você está autenticado!"
    echo ""
    curl -s http://localhost:5000/auth/mercadolivre/status | jq .
    echo ""
    echo "🎉 Pronto! Agora o webhook pode acessar a API do Mercado Livre."
    echo ""
    echo "📝 Tokens salvos em: services/site/config/ml_tokens.json"
else
    echo "⚠️  Ainda não autenticado. Status: $STATUS"
    echo ""
    echo "Verifique se:"
    echo "1. Adicionou a URL de callback no painel do ML"
    echo "2. Clicou em 'Autorizar' na tela do Mercado Livre"
    echo "3. Foi redirecionado de volta para localhost:5000"
fi

echo ""
