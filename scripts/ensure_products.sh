#!/usr/bin/env bash
# ensure_products.sh — Verifica se o banco tem produtos; se vazio, popula do staging.
# Uso: bash scripts/ensure_products.sh [container_name]

set -uo pipefail

CONTAINER="${1:-site}"
MAX_WAIT=60
elapsed=0

echo ""
echo "Step 🗄️  Verificando produtos no banco de dados..."

# ── Aguarda container estar rodando ─────────────────────────────────────────
until docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; do
    printf "   ⏳ Aguardando container %s... (%ds)\r" "$CONTAINER" "$elapsed"
    sleep 3; elapsed=$((elapsed + 3))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "   ⚠️  Container ${CONTAINER} não está rodando — pulando auto-stage"
        exit 0
    fi
done

# ── Aguarda Flask + PostgreSQL responderem ───────────────────────────────────
printf "   ⏳ Aguardando Flask + PostgreSQL"
elapsed=0
until docker exec --workdir /app "$CONTAINER" python3 -c "
from database import engine
from sqlalchemy import text
with engine.connect() as c: c.execute(text('SELECT 1'))
print('ready')
" 2>/dev/null | grep -q 'ready'; do
    printf "."
    sleep 3; elapsed=$((elapsed + 3))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo ""
        echo "   ⚠️  Timeout (${MAX_WAIT}s) aguardando Flask — pulando auto-stage"
        exit 0
    fi
done
echo " ✅"

# ── Conta produtos no banco ──────────────────────────────────────────────────
COUNT=$(docker exec --workdir /app "$CONTAINER" python3 -c "
from database import engine
from sqlalchemy import text
try:
    with engine.connect() as c:
        result = c.execute(text('SELECT COUNT(*) FROM products'))
        print(result.scalar())
except Exception:
    print(0)
" 2>/dev/null | tail -1 | tr -d '[:space:]') || true

# Valida que COUNT é número
if ! echo "$COUNT" | grep -qE '^[0-9]+$'; then
    echo "   ⚠️  Não foi possível verificar contagem — pulando auto-stage"
    exit 0
fi

echo "   📦 Produtos no banco: ${COUNT}"

# ── Auto-stage se vazio ──────────────────────────────────────────────────────
if [ "$COUNT" -eq 0 ]; then
    echo "   ⚠️  Banco vazio — populando com dados do staging automaticamente..."
    echo ""
    docker exec --workdir /app "$CONTAINER" python3 scripts/stage_products.py --force
    echo ""
    NEW_COUNT=$(docker exec --workdir /app "$CONTAINER" python3 -c "
from database import engine
from sqlalchemy import text
try:
    with engine.connect() as c:
        result = c.execute(text('SELECT COUNT(*) FROM products'))
        print(result.scalar())
except Exception:
    print(0)
" 2>/dev/null | tail -1 | tr -d '[:space:]') || true
    echo "   ✅ Stage concluído: ${NEW_COUNT} produto(s) carregado(s) no banco"
else
    echo "   ✅ DB já tem ${COUNT} produto(s) — nenhuma ação necessária"
fi

echo ""
