#!/usr/bin/env python3
"""
Script interativo para reorganizar os 6 produtos que ainda estão em 'geral/'
Mostra o título de cada um e pergunta qual categoria atribuir.
"""

import os
import json
import sys
from pathlib import Path

# Adicionar o diretório de scripts ao path
sys.path.insert(0, '/app/scripts')
sys.path.insert(0, '/app/services/site/scripts')

from organize_tags import move_product, detect_category_with_confidence

def show_menu():
    """Exibe o menu de categorias"""
    print("\n" + "="*70)
    print("🏷️  ESCOLHA A CATEGORIA DO PRODUTO")
    print("="*70)
    print("📋 Categorias disponíveis:")
    print("   1. PET - PetShop")
    print("   2. E - Eletrônicos")
    print("   3. CD - Casa & Decoração")
    print("   4. ME - Moda & Estilo")
    print("   5. ES - Esportes")
    print("   6. geral - Categoria Geral")
    print("="*70)

def get_category_from_user(suggested_tag=None):
    """Pede ao usuário para escolher uma categoria"""
    mapping = {
        "1": "PET",
        "2": "E",
        "3": "CD",
        "4": "ME",
        "5": "ES",
        "6": "geral",
        "PET": "PET",
        "E": "E",
        "CD": "CD",
        "ME": "ME",
        "ES": "ES",
        "geral": "geral",
    }
    
    show_menu()
    if suggested_tag:
        print(f"💡 Sugestão baseada no título: {suggested_tag}")
    
    while True:
        try:
            choice = input("\n➤ Digite o número ou tag (Enter para usar sugestão): ").strip().upper()
            
            if not choice:
                if suggested_tag:
                    return suggested_tag
                else:
                    print("❌ Por favor, escolha uma opção")
                    continue
            
            if choice in mapping:
                return mapping[choice]
            else:
                print("❌ Opção inválida. Digite 1-6 ou o nome da tag (PET, E, CD, ME, ES, geral)")
        except KeyboardInterrupt:
            print("\n\n⚠️  Operação cancelada pelo usuário")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Erro: {e}")

def process_remaining_products():
    """Processa os 6 produtos que ainda estão em geral/"""
    geral_path = Path("/app/staging/geral")
    
    if not geral_path.exists():
        print("❌ Pasta /app/staging/geral não encontrada")
        return
    
    # Encontrar todos os JSONs em geral/ (não recursivo, apenas root)
    json_files = list(geral_path.glob("*.json"))
    
    if not json_files:
        print("✅ Nenhum produto em geral/ para reorganizar!")
        return
    
    print(f"\n🏷️  ORGANIZADOR INTERATIVO — {len(json_files)} produtos em geral/")
    print("="*70 + "\n")
    
    moved_count = 0
    skipped_count = 0
    
    for idx, json_file in enumerate(json_files, 1):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                product = json.load(f)
            
            title = product.get('title', 'SEM TÍTULO')
            current_tag = product.get('tag', 'N/A')
            
            # Detectar categoria sugerida
            suggested_tag, confidence = detect_category_with_confidence(title)
            
            print(f"\n[{idx}/{len(json_files)}] 📦 PRODUTO")
            print("-" * 70)
            print(f"Título: {title}")
            print(f"Tag atual: {current_tag}")
            print(f"Detecção: {suggested_tag} ({confidence*100:.0f}%)")
            print("-" * 70)
            
            # Perguntar ao usuário
            new_category = get_category_from_user(suggested_tag if confidence >= 0.55 else None)
            
            if new_category == current_tag:
                print(f"⏭️  Produto já está em {current_tag}")
                skipped_count += 1
                continue
            
            # Mover o produto
            success = move_product(json_file, new_category, None)
            if success:
                print(f"✅ Movido para {new_category}/")
            else:
                print(f"❌ Erro ao mover")
            moved_count += 1
            
        except json.JSONDecodeError:
            print(f"❌ Erro ao ler {json_file.name}: arquivo JSON inválido")
        except Exception as e:
            print(f"❌ Erro ao processar {json_file.name}: {e}")
    
    print("\n" + "="*70)
    print("📊 RESUMO")
    print("="*70)
    print(f"✅ Movidos: {moved_count}")
    print(f"⏭️  Sem mudança: {skipped_count}")
    print("="*70)

if __name__ == "__main__":
    process_remaining_products()
