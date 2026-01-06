"""
Script para adicionar campos de webhook ao modelo Product
Adiciona: platform, external_id, nome, preco, preco_original, desconto, descricao, imagens, created_at, updated_at
"""

import sys
import os

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine
import time

def migrate_add_webhook_fields():
    """Adiciona novos campos ao modelo Product para suportar webhooks"""
    
    print("🔄 Iniciando migração para adicionar campos de webhook...")
    
    # Aguarda conexão com o banco
    print("⏳ Aguardando conexão com o banco...")
    time.sleep(2)
    
    try:
        with engine.connect() as conn:
            # Verifica se a tabela existe
            check_table = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'products'
                );
            """)
            result = conn.execute(check_table)
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("❌ Tabela 'products' não existe. Execute a aplicação primeiro.")
                return
            
            print("✅ Tabela 'products' encontrada.")
            
            # Lista de colunas para adicionar
            columns_to_add = [
                ("platform", "VARCHAR(50)"),
                ("external_id", "VARCHAR(255)"),
                ("nome", "VARCHAR(255)"),
                ("preco", "VARCHAR(50)"),
                ("preco_original", "VARCHAR(50)"),
                ("desconto", "FLOAT DEFAULT 0"),
                ("descricao", "TEXT"),
                ("imagens", "TEXT"),
                ("disponivel", "BOOLEAN DEFAULT TRUE"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]
            
            # Adiciona cada coluna se não existir
            for column_name, column_type in columns_to_add:
                check_column = text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'products' 
                        AND column_name = '{column_name}'
                    );
                """)
                result = conn.execute(check_column)
                column_exists = result.fetchone()[0]
                
                if not column_exists:
                    print(f"➕ Adicionando coluna '{column_name}'...")
                    alter_query = text(f"""
                        ALTER TABLE products 
                        ADD COLUMN {column_name} {column_type};
                    """)
                    conn.execute(alter_query)
                    conn.commit()
                    print(f"✅ Coluna '{column_name}' adicionada com sucesso!")
                else:
                    print(f"⏭️  Coluna '{column_name}' já existe, pulando...")
            
            # Adiciona constraint único para platform + external_id
            print("➕ Adicionando constraint único para platform + external_id...")
            try:
                constraint_query = text("""
                    ALTER TABLE products 
                    ADD CONSTRAINT unique_platform_external_id 
                    UNIQUE (platform, external_id);
                """)
                conn.execute(constraint_query)
                conn.commit()
                print("✅ Constraint único adicionado com sucesso!")
            except Exception as e:
                if "already exists" in str(e):
                    print("⏭️  Constraint já existe, pulando...")
                else:
                    print(f"⚠️  Aviso ao adicionar constraint: {str(e)}")
            
            # Sincroniza campos antigos com novos (compatibilidade)
            print("🔄 Sincronizando campos...")
            sync_query = text("""
                UPDATE products 
                SET 
                    nome = COALESCE(nome, title),
                    preco = COALESCE(preco, price),
                    preco_original = COALESCE(preco_original, old_price),
                    imagens = COALESCE(imagens, image)
                WHERE nome IS NULL OR preco IS NULL OR preco_original IS NULL OR imagens IS NULL;
            """)
            conn.execute(sync_query)
            conn.commit()
            print("✅ Campos sincronizados!")
            
            print("\n✅ Migração concluída com sucesso!")
            print("📊 Estatísticas:")
            
            # Mostra estatísticas
            count_query = text("SELECT COUNT(*) FROM products;")
            result = conn.execute(count_query)
            total = result.fetchone()[0]
            print(f"   Total de produtos: {total}")
            
    except Exception as e:
        print(f"❌ Erro durante a migração: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_add_webhook_fields()
