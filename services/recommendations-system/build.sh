#!/bin/bash

# Script para build e push da imagem do sistema de recomendações

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
IMAGE_NAME="recommendations-system"
VERSION=${VERSION:-latest}
REGISTRY=${DOCKER_REGISTRY:-"docker.io"}
REGISTRY_USER=${DOCKER_USER:-""}

echo -e "${GREEN}🚀 Building Recommendations System Docker Image${NC}"
echo "=================================================="
echo "Image: ${IMAGE_NAME}"
echo "Version: ${VERSION}"
echo "Registry: ${REGISTRY}"
echo "=================================================="

# Navegar para o diretório correto
cd "$(dirname "$0")"

# Build da imagem
echo -e "\n${YELLOW}📦 Building image...${NC}"
docker build -t ${IMAGE_NAME}:${VERSION} .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Build successful!${NC}"
else
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

# Tag para registry
if [ ! -z "$REGISTRY_USER" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${REGISTRY_USER}/${IMAGE_NAME}:${VERSION}"
    
    echo -e "\n${YELLOW}🏷️  Tagging image...${NC}"
    docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE_NAME}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Tagged as ${FULL_IMAGE_NAME}${NC}"
    else
        echo -e "${RED}❌ Tagging failed!${NC}"
        exit 1
    fi
    
    # Push para registry (se solicitado)
    if [ "$1" == "--push" ] || [ "$1" == "-p" ]; then
        echo -e "\n${YELLOW}📤 Pushing to registry...${NC}"
        docker push ${FULL_IMAGE_NAME}
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Push successful!${NC}"
            echo -e "\nImage available at: ${FULL_IMAGE_NAME}"
        else
            echo -e "${RED}❌ Push failed!${NC}"
            exit 1
        fi
    else
        echo -e "\n${YELLOW}ℹ️  Image ready for push:${NC}"
        echo "docker push ${FULL_IMAGE_NAME}"
        echo -e "\nOr run: ./build.sh --push"
    fi
else
    echo -e "\n${YELLOW}ℹ️  Local image created: ${IMAGE_NAME}:${VERSION}${NC}"
    echo "To push to a registry, set DOCKER_REGISTRY and DOCKER_USER env vars"
fi

# Mostrar informações da imagem
echo -e "\n${GREEN}📊 Image Info:${NC}"
docker images ${IMAGE_NAME}:${VERSION}

# Mostrar comandos úteis
echo -e "\n${GREEN}🎯 Useful Commands:${NC}"
echo "Run locally:"
echo "  docker run -p 8000:8000 -p 8001:8001 -p 8002:8002 -p 8003:8003 -p 8005:8005 \\"
echo "    -e INSTAGRAM_APP_ID=your_id \\"
echo "    -e INSTAGRAM_APP_SECRET=your_secret \\"
echo "    -e OPENAI_API_KEY=your_key \\"
echo "    ${IMAGE_NAME}:${VERSION}"
echo ""
echo "Test health:"
echo "  curl http://localhost:8000/health"
echo ""
echo "View logs:"
echo "  docker logs -f <container_id>"

echo -e "\n${GREEN}✅ Done!${NC}"
