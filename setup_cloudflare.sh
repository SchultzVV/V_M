#!/bin/bash
# =======================
# 🌐 Setup Cloudflare Tunnel
# =======================
# Este script configura o Cloudflare Tunnel pela primeira vez
# para expor o serviço site com HTTPS gratuito (substitui ngrok)

set -e

echo "🚀 Setup do Cloudflare Tunnel"
echo "=============================="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar se cloudflared está instalado
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}📦 Cloudflared não encontrado. Instalando...${NC}"
    
    # Download do cloudflared
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -O /tmp/cloudflared.deb
    
    # Instalar
    sudo dpkg -i /tmp/cloudflared.deb
    
    # Limpar
    rm /tmp/cloudflared.deb
    
    echo -e "${GREEN}✅ Cloudflared instalado com sucesso!${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Cloudflared já está instalado${NC}"
    echo ""
fi

# Login no Cloudflare
echo -e "${YELLOW}🔑 Passo 1: Login no Cloudflare${NC}"
echo "Abrindo navegador para autenticação..."
echo "Faça login com sua conta Cloudflare (ou crie uma - é GRÁTIS)"
echo ""
cloudflared tunnel login

echo ""
echo -e "${GREEN}✅ Login realizado com sucesso!${NC}"
echo ""

# Criar túnel
TUNNEL_NAME="vm-site"
echo -e "${YELLOW}🔧 Passo 2: Criando túnel '${TUNNEL_NAME}'${NC}"
echo ""

# Verificar se túnel já existe
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo -e "${YELLOW}⚠️  Túnel '${TUNNEL_NAME}' já existe${NC}"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    echo "Usando túnel existente: $TUNNEL_ID"
else
    cloudflared tunnel create $TUNNEL_NAME
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    echo -e "${GREEN}✅ Túnel criado: ${TUNNEL_ID}${NC}"
fi

echo ""
echo -e "${YELLOW}📝 Passo 3: Configurando túnel${NC}"

# Criar diretório de configuração
mkdir -p ~/.cloudflared

# Encontrar o arquivo de credenciais
CRED_FILE=$(ls ~/.cloudflared/*.json 2>/dev/null | grep "$TUNNEL_ID" | head -1)

if [ -z "$CRED_FILE" ]; then
    echo -e "${RED}❌ Erro: Arquivo de credenciais não encontrado${NC}"
    exit 1
fi

# Criar arquivo de configuração
cat > ~/.cloudflared/config.yml << EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${CRED_FILE}

ingress:
  # Rota principal - seu site Docker na porta 5000
  - hostname: vm-site.trycloudflare.com
    service: https://localhost:5000
    originRequest:
      noTLSVerify: true
  
  # Fallback para requisições não encontradas
  - service: http_status:404
EOF

echo -e "${GREEN}✅ Configuração criada em ~/.cloudflared/config.yml${NC}"
echo ""

# Configurar DNS (domínio trycloudflare.com é gratuito)
echo -e "${YELLOW}🌐 Passo 4: Configurando DNS${NC}"
echo ""

# Tentar configurar rota DNS
if cloudflared tunnel route dns $TUNNEL_NAME vm-site.trycloudflare.com 2>/dev/null; then
    echo -e "${GREEN}✅ Rota DNS configurada${NC}"
else
    echo -e "${YELLOW}⚠️  Usando domínio temporário do Cloudflare${NC}"
    echo "Você terá uma URL automática ao iniciar o túnel"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup concluído com sucesso!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1️⃣  Inicie o túnel com:"
echo "   ${GREEN}make serve-cloudflare${NC}"
echo ""
echo "2️⃣  Copie a URL HTTPS que aparecer"
echo ""
echo "3️⃣  Configure no painel do Mercado Livre:"
echo "   https://developers.mercadolivre.com.br/devcenter"
echo "   Redirect URI: <URL_DO_TUNNEL>/auth/mercadolivre/callback"
echo ""
echo "4️⃣  Atualize o arquivo .env com:"
echo "   ML_REDIRECT_URI=<URL_DO_TUNNEL>/auth/mercadolivre/callback"
echo ""
echo "💡 Para parar o túnel: Ctrl+C ou 'make stop-cloudflare'"
echo ""
