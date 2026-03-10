#!/usr/bin/env python3
"""
Migração: adiciona coluna subcategory à tabela products.
Também corrige produtos existentes que ainda não têm subcategory definida.

Uso: docker exec site python3 scripts/migrate_add_subcategory.py
"""
import sys
sys.path.insert(0, "/app")

from database import SessionLocal
from sqlalchemy import text

def run():
    db = SessionLocal()
    try:
        # 1. Adiciona coluna se não existir
        db.execute(text("""
            ALTER TABLE products
            ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100) DEFAULT '';
        """))
        db.commit()
        print("✅ Coluna 'subcategory' adicionada (ou já existia)")

        # 2. Informa quantos produtos existentes ainda não têm subcategory
        result = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE subcategory IS NULL OR subcategory = ''"
        )).scalar()
        print(f"ℹ️  {result} produtos sem subcategoria definida (precisarão ser re-staged ou editados no admin)")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro na migração: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run()
