#!/bin/bash
# =======================
# 🌐 Setup LocalTunnel (Alternativa Simples)
# =======================
# LocalTunnel é uma alternativa ao ngrok que não precisa de cadastro
# e é completamente gratuito

set -e

echo "🚀 Setup do LocalTunnel"
echo "======================"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js não está instalado!${NC}"
    echo ""
    echo "Instale o Node.js primeiro:"
    echo "  sudo apt install nodejs npm"
    exit 1
fi

echo -e "${GREEN}✅ Node.js encontrado: $(node --version)${NC}"
echo ""

# Instalar LocalTunnel
echo -e "${YELLOW}📦 Instalando LocalTunnel...${NC}"
sudo npm install -g localtunnel

echo ""
echo -e "${GREEN}✅ LocalTunnel instalado com sucesso!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Setup concluído!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Para iniciar o túnel, use:"
echo "  ${GREEN}make serve-localtunnel${NC}"
echo ""
