#!/usr/bin/env python3
"""
Script para migrar o banco de dados e adicionar a coluna 'tags' na tabela products
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Configurações do banco
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/produtos_db")

def run_migration():
    try:
        # Conectar ao banco
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar se a coluna já existe
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='products' AND column_name='tags';
        """)
        
        if cursor.fetchone():
            print("✅ Coluna 'tags' já existe na tabela products")
            return
        
        # Adicionar coluna tags
        print("🔧 Adicionando coluna 'tags' na tabela products...")
        cursor.execute("""
            ALTER TABLE products 
            ADD COLUMN tags TEXT DEFAULT '["geral"]';
        """)
        
        # Atualizar produtos existentes com tags baseadas no título
        print("🏷️  Atualizando tags dos produtos existentes...")
        cursor.execute("SELECT id, title FROM products;")
        products = cursor.fetchall()
        
        for product in products:
            title = product['title'].lower()
            tags = ["geral"]
            
            # Casa & Decoração
            casa_keywords = ['copo', 'casa', 'cozinha', 'quarto', 'sala', 'decoração', 'móvel', 'organizador', 
                             'pote', 'utensílio', 'panela', 'frigideira', 'aspirador', 'robô', 'limpeza',
                             'hermético', 'mantimentos', 'dispensa', 'armário', 'plástico']
            
            # Moda & Estilo  
            moda_keywords = ['vestido', 'blusa', 'calça', 'sapato', 'tênis', 'bolsa', 'acessório', 
                             'roupa', 'moda', 'multiformas', 'madrinhas', 'casamento', 'festas']
            
            # Eletrônicos
            eletronicos_keywords = ['celular', 'smartphone', 'tablet', 'notebook', 'fone', 'carregador', 
                                   'cabo', 'eletrônico', 'tv', 'monitor', 'mouse', 'teclado', 'camera', 
                                   'smartwatch', 'airfryer', 'fritadeira', 'philips']

            # Esportes
            esportes_keywords = ['futebol', 'chuteira', 'bola', 'corrida', 'academia', 'musculação',
                                 'musculacao', 'halter', 'kettlebell', 'natação', 'natacao', 'ciclismo',
                                 'bike', 'bicicleta', 'tenis de corrida', 'raquete', 'crossfit', 'yoga']
            
            if any(keyword in title for keyword in casa_keywords):
                tags.append("CD")
                
            if any(keyword in title for keyword in moda_keywords):
                tags.append("ME")
                
            if any(keyword in title for keyword in eletronicos_keywords):
                tags.append("E")

            if any(keyword in title for keyword in esportes_keywords):
                tags.append("ES")
            
            # Atualizar produto com as tags
            cursor.execute(
                "UPDATE products SET tags = %s WHERE id = %s;",
                (str(tags).replace("'", '"'), product['id'])
            )
        
        # Commit das mudanças
        conn.commit()
        print(f"✅ Migração concluída! {len(products)} produtos atualizados.")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando migração do banco de dados...")
    run_migration()
