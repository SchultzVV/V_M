#!/bin/bash

# ============================================
# 🎨 Setup Instagram - Sistema de Postagem
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📸 Setup do Sistema de Postagem Instagram"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verifica se .env existe
if [ ! -f .env ]; then
    echo "⚠️  Arquivo .env não encontrado"
    echo "📝 Criando .env a partir do template..."
    cp .env.instagram.example .env
    echo "✅ Arquivo .env criado"
    echo ""
fi

# Pede credenciais do OpenAI
echo "🤖 Configuração OpenAI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "Digite sua OpenAI API Key: " OPENAI_KEY

if [ -z "$OPENAI_KEY" ]; then
    echo "⚠️  OpenAI API Key não fornecida"
else
    # Adiciona ao .env se não existir
    if ! grep -q "OPENAI_API_KEY=" .env; then
        echo "OPENAI_API_KEY=$OPENAI_KEY" >> .env
    else
        # Substitui a existente
        sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_KEY|g" .env
    fi
    echo "✅ OpenAI API Key configurada"
fi

echo ""
echo "📸 Configuração Instagram"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "Digite seu usuário do Instagram: " IG_USER
read -sp "Digite sua senha do Instagram: " IG_PASS
echo ""

if [ -z "$IG_USER" ] || [ -z "$IG_PASS" ]; then
    echo "⚠️  Credenciais Instagram não fornecidas"
else
    # Adiciona ao .env
    if ! grep -q "INSTAGRAM_USERNAME=" .env; then
        echo "INSTAGRAM_USERNAME=$IG_USER" >> .env
    else
        sed -i "s|INSTAGRAM_USERNAME=.*|INSTAGRAM_USERNAME=$IG_USER|g" .env
    fi
    
    if ! grep -q "INSTAGRAM_PASSWORD=" .env; then
        echo "INSTAGRAM_PASSWORD=$IG_PASS" >> .env
    else
        sed -i "s|INSTAGRAM_PASSWORD=.*|INSTAGRAM_PASSWORD=$IG_PASS|g" .env
    fi
    
    echo "✅ Credenciais Instagram configuradas"
fi

# Adiciona Redis URL se não existir
if ! grep -q "REDIS_URL=" .env; then
    echo "REDIS_URL=redis://redis:6379" >> .env
    echo "✅ Redis URL configurada"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Configuração concluída!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Próximos passos:"
echo ""
echo "   1. Suba o ambiente:"
echo "      make up"
echo ""
echo "   2. Teste o sistema:"
echo "      make instagram-test"
echo ""
echo "   3. Verifique o status:"
echo "      make instagram-status"
echo ""
echo "   4. Poste automaticamente:"
echo "      make instagram-post"
echo ""
echo "📚 Comandos disponíveis:"
echo "   make instagram-post      - Posta automaticamente"
echo "   make instagram-test      - Testa sem postar"
echo "   make instagram-status    - Verifica status"
echo "   make instagram-history   - Mostra histórico"
echo "   make instagram-workflow  - Mostra fluxo dos agentes"
echo "   make stage-and-post      - Publica ML + Instagram"
echo ""
