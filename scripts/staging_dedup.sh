#!/usr/bin/env bash
# =============================================================
# staging_dedup.sh
# Remove JSONs duplicados do staging, mantendo apenas o mais
# novo por produto (identificado pelo slug antes do timestamp).
#
# Padrão de nome:  {slug}_{YYYYMMDD}_{HHMMSS}.json
# Uso:             ./scripts/staging_dedup.sh [STAGING_DIR]
# Default dir:     services/site/staging
# =============================================================

set -euo pipefail

STAGING_DIR="${1:-services/site/staging}"

# Resolve em caminho absoluto relativo ao diretório de onde o script é chamado
if [[ "$STAGING_DIR" != /* ]]; then
    STAGING_DIR="$(pwd)/$STAGING_DIR"
fi

SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "$SEP"
echo "  🔍 STAGING DEDUP — verificando duplicados"
echo "$SEP"
echo "  📁 Diretório: $STAGING_DIR"
echo ""

if [[ ! -d "$STAGING_DIR" ]]; then
    echo "  ❌ Diretório não encontrado: $STAGING_DIR"
    exit 1
fi

# Coleta todos os JSONs (exceto .gitkeep que tem nome diferente)
mapfile -t ALL_FILES < <(find "$STAGING_DIR" -name "*.json" ! -name ".gitkeep" | sort)

if [[ ${#ALL_FILES[@]} -eq 0 ]]; then
    echo "  ℹ️  Nenhum JSON encontrado no staging."
    echo ""
    exit 0
fi

declare -A FILE_GROUPS  # slug_key -> lista de arquivos separada por \n
declare -A GROUP_DIRS   # controle de slugs encontrados

for filepath in "${ALL_FILES[@]}"; do
    dir=$(dirname "$filepath")
    base=$(basename "$filepath")

    # Extrai slug: remove o sufixo _YYYYMMDD_HHMMSS.json
    if [[ "$base" =~ ^(.+)_([0-9]{8})_([0-9]{6})\.json$ ]]; then
        slug="${BASH_REMATCH[1]}"
    else
        # Arquivo sem timestamp — trata o nome inteiro como slug único
        slug="${base%.json}__notimestamp"
    fi

    # Chave = slug + diretório (isola produtos iguais em categorias diferentes)
    key="${dir}|${slug}"

    if [[ -v FILE_GROUPS["$key"] ]]; then
        FILE_GROUPS["$key"]+=$'\n'"$filepath"
    else
        FILE_GROUPS["$key"]="$filepath"
    fi
done

REMOVED=0
KEPT=0
HAS_DUPS=0

for key in "${!FILE_GROUPS[@]}"; do
    # Converte string de arquivos em array ordenado (sort garante ordem cronológica)
    mapfile -t FILES < <(echo "${FILE_GROUPS[$key]}" | tr '\n' '\0' | xargs -0 -n1 | sort)

    COUNT=${#FILES[@]}
    if [[ $COUNT -le 1 ]]; then
        continue
    fi

    HAS_DUPS=1
    NEWEST="${FILES[$((COUNT - 1))]}"

    echo "  📦 Duplicados encontrados:"
    for (( i=0; i<COUNT-1; i++ )); do
        f="${FILES[$i]}"
        rm -f "$f"
        echo "    🗑️  Removido: $(basename "$f")"
        (( REMOVED++ )) || true
    done
    echo "    ✅ Mantido:  $(basename "$NEWEST")"
    (( KEPT++ )) || true
    echo ""
done

echo "$SEP"
if [[ $HAS_DUPS -eq 0 ]]; then
    echo "  ✅ Nenhum duplicado encontrado. Staging limpo!"
else
    echo "  🗑️  $REMOVED arquivo(s) removido(s)"
    echo "  ✅ $KEPT produto(s) com versão mais nova mantida"
fi
echo "$SEP"
echo ""
