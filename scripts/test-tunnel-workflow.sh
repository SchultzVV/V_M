#!/bin/bash
# ============================================================
# Test Script: Validar Cloudflare Tunnel Workflow
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🧪 TESTE: Cloudflare Tunnel Shared Workflow${NC}"
echo ""

# Test 1: Verificar tunnel-manager.sh existe
echo -e "${YELLOW}Test 1️⃣  Verificar script tunnel-manager.sh...${NC}"
if [ -f "scripts/tunnel-manager.sh" ]; then
    echo -e "${GREEN}✅ script/tunnel-manager.sh existe${NC}"
else
    echo -e "${RED}❌ script/tunnel-manager.sh NÃO encontrado${NC}"
    exit 1
fi
echo ""

# Test 2: Verificar docker-compose.dev.yaml tem Nginx
echo -e "${YELLOW}Test 2️⃣  Verificar Nginx em docker-compose.dev.yaml...${NC}"
if grep -q "nginx:" docker-compose.dev.yaml; then
    echo -e "${GREEN}✅ Nginx configurado em docker-compose.dev.yaml${NC}"
else
    echo -e "${RED}❌ Nginx NÃO encontrado em docker-compose.dev.yaml${NC}"
    exit 1
fi
echo ""

# Test 3: Verificar nginx-react.conf exists
echo -e "${YELLOW}Test 3️⃣  Verificar nginx/nginx-react.conf...${NC}"
if [ -f "nginx/nginx-react.conf" ]; then
    if grep -q "upstream flask_backend" nginx/nginx-react.conf; then
        echo -e "${GREEN}✅ Nginx config com upstream flask_backend${NC}"
    else
        echo -e "${RED}⚠️  nginx-react.conf sem upstream explícito${NC}"
    fi
else
    echo -e "${RED}❌ nginx/nginx-react.conf NÃO encontrado${NC}"
    exit 1
fi
echo ""

# Test 4: Verificar tunnel-manager.sh é executável
echo -e "${YELLOW}Test 4️⃣  Verificar permissões tunnel-manager.sh...${NC}"
if [ -x "scripts/tunnel-manager.sh" ]; then
    echo -e "${GREEN}✅ script é executável${NC}"
else
    echo -e "${YELLOW}⚠️  script não é executável, corrigindo...${NC}"
    chmod +x scripts/tunnel-manager.sh
    echo -e "${GREEN}✅ Permissões corrigidas${NC}"
fi
echo ""

# Test 5: Verificar Makefile tem stop-all
echo -e "${YELLOW}Test 5️⃣  Verificar novo comando stop-all...${NC}"
if grep -q "stop-all:" Makefile; then
    echo -e "${GREEN}✅ Comando 'make stop-all' disponível${NC}"
else
    echo -e "${RED}❌ Comando 'make stop-all' não encontrado${NC}"
    exit 1
fi
echo ""

# Test 6: Verificar Makefile não faz pkill em stop-frontend-public
echo -e "${YELLOW}Test 6️⃣  Verificar stop-frontend-public NÃO mata tunnel...${NC}"
if grep -A 5 "^stop-frontend-public:" Makefile | grep -q "pkill cloudflared"; then
    echo -e "${RED}❌ stop-frontend-public ainda faz pkill cloudflared!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ stop-frontend-public preserva tunnel ✓${NC}"
fi
echo ""

# Test 7: Verificar CLOUDFLARE_TUNNEL_WORKFLOW.md existe
echo -e "${YELLOW}Test 7️⃣  Verificar documentação workflow...${NC}"
if [ -f "docs/CLOUDFLARE_TUNNEL_WORKFLOW.md" ]; then
    echo -e "${GREEN}✅ Documentação criada${NC}"
else
    echo -e "${RED}❌ Documentação não encontrada${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ TODOS OS TESTES PASSARAM!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📖 Próximo passo: Ler documentação${NC}"
echo "   $ cat docs/CLOUDFLARE_TUNNEL_WORKFLOW.md"
echo ""
echo -e "${YELLOW}🚀 Para testar o workflow:${NC}"
echo "   Terminal 1: $ make serve-cloudflare"
echo "   Terminal 2: $ make serve-frontend-public"
echo "   (Deve reutilizar mesma URL!)"
echo ""
