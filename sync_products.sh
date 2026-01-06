#!/bin/bash

echo "🔄 Sincronização Manual de Produtos - Mercado Livre"
echo "===================================================="
echo ""

# Verifica se o site está rodando
if ! docker ps | grep -q site-dev; then
    echo "❌ Site não está rodando!"
    echo "Execute: docker-compose up -d site"
    exit 1
fi

echo "1️⃣ Verificando status..."
curl -s http://localhost:5000/sync/mercadolivre/status | jq .

echo ""
echo "Escolha uma opção:"
echo "1) Sincronizar UM produto específico"
echo "2) Sincronizar TODOS os produtos"
echo "3) Sair"
echo ""

read -p "Opção: " opcao

case $opcao in
    1)
        echo ""
        read -p "Digite o MLB ID (ex: MLB1234567890): " mlb_id
        echo ""
        echo "🔄 Sincronizando produto $mlb_id..."
        curl -X POST http://localhost:5000/sync/mercadolivre/product/$mlb_id \
            -H "Content-Type: application/json" | jq .
        ;;
    2)
        echo ""
        read -p "Tem certeza? Isso vai sincronizar TODOS os produtos. (s/n): " confirma
        if [ "$confirma" = "s" ]; then
            echo ""
            echo "🔄 Sincronizando todos os produtos..."
            curl -X POST http://localhost:5000/sync/mercadolivre/all \
                -H "Content-Type: application/json" | jq .
        else
            echo "Cancelado."
        fi
        ;;
    3)
        echo "Saindo..."
        exit 0
        ;;
    *)
        echo "Opção inválida!"
        exit 1
        ;;
esac

echo ""
