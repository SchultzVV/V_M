#!/bin/bash

# Script de teste completo do sistema de recomendações
# Uso: ./test_recommendations.sh

set -e

echo "🧪 Iniciando testes do sistema de recomendações..."
echo ""

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"

# Função para printar com cor
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Função para fazer request e checar resposta
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=${4:-200}
    
    print_info "Testing: $method $endpoint"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "$expected_status" ]; then
        print_success "Status: $http_code"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo ""
        return 0
    else
        print_error "Expected $expected_status, got $http_code"
        echo "$body"
        echo ""
        return 1
    fi
}

# 1. Health Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request GET "/health"

# 2. API Info
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  API Info"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request GET "/"

# 3. Testar Tracking (sem autenticação necessária)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Tracking - Impression"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request POST "/track" '{
    "user_id": "test-user-123",
    "event_type": "impression",
    "item_id": "prod-001",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'Z"
}'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Tracking - Click"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request POST "/track" '{
    "user_id": "test-user-123",
    "event_type": "click",
    "item_id": "prod-001",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'Z"
}'

# 4. Testar Batch Tracking
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  Batch Tracking"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request POST "/track/batch" '[
    {
        "user_id": "test-user-123",
        "event_type": "impression",
        "item_id": "prod-002",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'Z"
    },
    {
        "user_id": "test-user-123",
        "event_type": "impression",
        "item_id": "prod-003",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'Z"
    }
]'

# 5. Testar Recomendações Genéricas (fallback - sem perfil)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  Recomendações Genéricas (Fallback)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request GET "/recommendations?user_id=nonexistent-user&limit=3"

# 6. Testar Recomendações por Segmento
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  Recomendações por Segmento (electronics)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request GET "/recommendations?user_id=nonexistent-user&limit=3&segment=electronics"

# 7. Verificar se Auth Service está respondendo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  Auth Service - Status (sem usuário)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_info "Testing: GET /auth/status/test-user (expecting 404)"
curl -s "$API_URL/auth/status/test-user" | jq '.' || echo "User not found (esperado)"
echo ""

# 8. Teste de cache (duas chamadas iguais)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣  Teste de Cache"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_info "Primeira chamada (sem cache)..."
start_time=$(date +%s%3N)
response1=$(curl -s "$API_URL/recommendations?user_id=cache-test&limit=3")
end_time=$(date +%s%3N)
latency1=$((end_time - start_time))
cache_hit1=$(echo "$response1" | jq -r '.cache_hit')
print_info "Latência: ${latency1}ms | Cache hit: $cache_hit1"

sleep 1

print_info "Segunda chamada (deve usar cache)..."
start_time=$(date +%s%3N)
response2=$(curl -s "$API_URL/recommendations?user_id=cache-test&limit=3")
end_time=$(date +%s%3N)
latency2=$((end_time - start_time))
cache_hit2=$(echo "$response2" | jq -r '.cache_hit')
print_info "Latência: ${latency2}ms | Cache hit: $cache_hit2"

if [ "$cache_hit2" = "true" ]; then
    print_success "Cache funcionando! Latência reduzida de ${latency1}ms para ${latency2}ms"
else
    print_warning "Cache não funcionou como esperado"
fi
echo ""

# 9. Teste de invalidação de cache
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔟 Invalidação de Cache"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make_request POST "/recommendations/invalidate/cache-test"

# Resumo
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESUMO DOS TESTES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "Todos os testes básicos passaram!"
echo ""
print_info "Para testes completos com autenticação:"
echo "  1. Configure Instagram App no .env"
echo "  2. Obtenha authorization code"
echo "  3. Execute: make recs-test-auth INSTAGRAM_CODE=xxx"
echo ""
print_info "Para verificar dados no banco:"
echo "  make recs-psql"
echo ""
print_info "Para ver eventos no Kafka:"
echo "  make recs-kafka-consume"
echo ""
print_info "Documentação interativa:"
echo "  http://localhost:8000/docs"
echo ""
