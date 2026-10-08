#!/usr/bin/env python3
"""
Preparação MANUAL de produtos da Shopee.
Como a Shopee bloqueia scraping automatizado, este script auxilia
na entrada manual dos dados.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from slugify import slugify

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python3 shopee_prepare_manual.py <URL_SHOPEE>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("="*70)
    print("🛍️  PREPARAÇÃO MANUAL DE PRODUTO DA SHOPEE")
    print("="*70)
    print(f"\n🔗 URL: {url}\n")
    print("💡 Abra a URL no navegador e copie as informações manualmente.\n")
    
    # Coletar dados do usuário
    product_data = {}
    
    product_data['title'] = input("📝 Título do produto: ").strip()
    
    price_str = input("💰 Preço atual (R$): ").strip().replace("R$", "").replace(",", ".")
    product_data['price'] = float(price_str)
    
    old_price_str = input("💸 Preço antigo [Enter para pular]: ").strip().replace("R$", "").replace(",", ".")
    product_data['original_price'] = float(old_price_str) if old_price_str else 0
    
    product_data['stock'] = int(input("📦 Estoque disponível: ").strip())
    
    sold_str = input("🛒 Quantidade vendida [Enter para 0]: ").strip()
    product_data['sold'] = int(sold_str) if sold_str else 0
    
    rating_str = input("⭐ Avaliação (0-5) [Enter para 0]: ").strip()
    product_data['rating'] = float(rating_str) if rating_str else 0
    
    # Imagens
    print("\n🖼️  URLs das imagens (uma por linha, Enter vazio para finalizar):")
    images = []
    i = 1
    while True:
        img_url = input(f"   Imagem {i}: ").strip()
        if not img_url:
            break
        images.append(img_url)
        i += 1
    
    product_data['images'] = images
    product_data['description'] = ''
    product_data['condition'] = 'new'
    
    # Mostrar dados coletados
    print("\n" + "="*70)
    print("📦 DADOS COLETADOS:")
    print("="*70)
    print(f"📝 Título: {product_data['title'][:60]}...")
    print(f"💰 Preço: R$ {product_data['price']:.2f}")
    if product_data['original_price']:
        print(f"💸 Preço antigo: R$ {product_data['original_price']:.2f}")
    print(f"📦 Estoque: {product_data['stock']}")
    print(f"🛒 Vendidos: {product_data['sold']}")
    if product_data['rating']:
        print(f"⭐ Avaliação: {product_data['rating']}")
    print(f"🖼️  Imagens: {len(product_data['images'])} encontradas")
    
    # Confirmar
    confirm = input("\n✅ Confirmar dados? (s/N): ").strip().lower()
    if confirm != 's':
        print("❌ Cancelado pelo usuário")
        sys.exit(1)
    
    # Perguntar categoria
    print("\n" + "="*70)
    print("📂 CATEGORIA DO PRODUTO")
    print("="*70)
    print("E  - Eletrônicos")
    print("CD - Casa e Decoração")  
    print("ME - Moda e Estilo")
    print("PET - Pet Shop")
    print("ES - Esportes")
    
    category = input("\nEscolha a categoria (E/CD/ME/PET/ES): ").strip().upper()
    if category not in ['E', 'CD', 'ME', 'PET', 'ES']:
        print("❌ Categoria inválida")
        sys.exit(1)
    
    # Subcategoria baseada na categoria
    subcategories = {
        'E': ['smartphone', 'notebook', 'tablet', 'acessorios', 'outros'],
        'CD': ['cozinha', 'quarto', 'banheiro', 'decoracao', 'outros'],
        'ME': ['roupas', 'calcados', 'acessorios', 'bolsas', 'outros'],
        'PET': ['caes', 'gatos', 'passaros', 'acessorios', 'outros'],
        'ES': ['futebol', 'corrida', 'academia', 'natacao', 'ciclismo', 'tenis', 'esportes-radicais', 'acessorios', 'outros']
    }
    
    print(f"\nSubcategorias disponíveis: {', '.join(subcategories[category])}")
    subcategory = input("Digite a subcategoria: ").strip().lower()
    
    # Criar slug
    slug = slugify(product_data['title'])
    
    # Preparar JSON final
    staging_data = {
        'title': product_data['title'],
        'slug': slug,
        'price': product_data['price'],
        'original_price': product_data['original_price'],
        'stock': product_data['stock'],
        'sold': product_data['sold'],
        'rating': product_data['rating'],
        'images': product_data['images'],
        'description': product_data['description'],
        'category': category,
        'subcategory': subcategory,
        'platform': 'shopee',
        'source_url': url,
        'collected_at': datetime.now().isoformat(),
        'method': 'manual'
    }
    
    # Salvar JSON
    staging_dir = Path("services/site/list_to_prepare_and_stage")
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    json_filename = f"{slug}-shopee.json"
    json_path = staging_dir / json_filename
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(staging_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("✅ PRODUTO PREPARADO COM SUCESSO!")
    print("="*70)
    print(f"📁 Arquivo salvo: {json_path}")
    print(f"\n💡 Próximo passo: Revisar o arquivo JSON e mover para staging/")
    
if __name__ == "__main__":
    main()
