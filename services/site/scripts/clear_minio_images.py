#!/usr/bin/env python3
"""
Script para limpar TODAS as imagens do bucket MinIO.
⚠️  CUIDADO: Esta operação é irreversível!
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório pai ao path para importar os módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.minio_client import minio_client


def clear_all_images():
    """
    Remove TODOS os objetos do bucket de imagens do MinIO.
    """
    bucket_name = os.getenv("MINIO_BUCKET", "amazon")
    
    print("=" * 60)
    print("🗑️  LIMPEZA COMPLETA DO MINIO")
    print("=" * 60)
    print(f"\n📦 Bucket: {bucket_name}")
    
    # Verifica se o bucket existe
    if not minio_client.bucket_exists(bucket_name):
        print(f"\n⚠️  Bucket '{bucket_name}' não existe!")
        print("   Nada para limpar.")
        return
    
    print(f"\n🔍 Listando objetos no bucket...")
    
    # Lista todos os objetos
    objects = list(minio_client.list_objects(bucket_name, recursive=True))
    
    if not objects:
        print("\n✅ Bucket já está vazio!")
        return
    
    total_objects = len(objects)
    print(f"\n📊 Total de objetos encontrados: {total_objects}")
    
    # Calcula tamanho total
    total_size = sum(obj.size for obj in objects)
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"💾 Tamanho total: {total_size_mb:.2f} MB")
    
    # Lista alguns exemplos
    print(f"\n📋 Exemplos de objetos:")
    for obj in objects[:10]:
        size_kb = obj.size / 1024
        print(f"   - {obj.object_name} ({size_kb:.1f}KB)")
    
    if total_objects > 10:
        print(f"   ... e mais {total_objects - 10} objetos")
    
    print(f"\n⚠️  ATENÇÃO: Esta operação vai remover TODOS os {total_objects} objetos!")
    print("   Esta ação é IRREVERSÍVEL!")
    
    # Confirmação de segurança
    response = input("\n❓ Deseja continuar? Digite 'CONFIRMAR' para prosseguir: ")
    
    if response.strip() != "CONFIRMAR":
        print("\n❌ Operação cancelada pelo usuário.")
        return
    
    print(f"\n🗑️  Removendo {total_objects} objetos...")
    
    removed_count = 0
    error_count = 0
    
    for obj in objects:
        try:
            minio_client.remove_object(bucket_name, obj.object_name)
            removed_count += 1
            
            # Mostra progresso a cada 10 objetos
            if removed_count % 10 == 0:
                progress = (removed_count / total_objects) * 100
                print(f"   📉 Progresso: {removed_count}/{total_objects} ({progress:.1f}%)")
        
        except Exception as e:
            error_count += 1
            print(f"   ⚠️  Erro ao remover {obj.object_name}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ LIMPEZA CONCLUÍDA!")
    print("=" * 60)
    print(f"\n📊 Resumo:")
    print(f"   ✅ Removidos: {removed_count} objetos")
    if error_count > 0:
        print(f"   ⚠️  Erros: {error_count} objetos")
    print(f"   💾 Espaço liberado: {total_size_mb:.2f} MB")
    print(f"\n🎯 Bucket '{bucket_name}' está agora vazio!")


def clear_all_images_force():
    """
    Remove TODOS os objetos do bucket MinIO sem confirmação.
    Use apenas em scripts automatizados.
    """
    bucket_name = os.getenv("MINIO_BUCKET", "amazon")
    
    print(f"🗑️  Limpando bucket '{bucket_name}' (modo forçado)...")
    
    if not minio_client.bucket_exists(bucket_name):
        print(f"⚠️  Bucket '{bucket_name}' não existe!")
        return
    
    objects = list(minio_client.list_objects(bucket_name, recursive=True))
    
    if not objects:
        print("✅ Bucket já está vazio!")
        return
    
    removed_count = 0
    for obj in objects:
        try:
            minio_client.remove_object(bucket_name, obj.object_name)
            removed_count += 1
        except Exception as e:
            print(f"⚠️  Erro ao remover {obj.object_name}: {e}")
    
    total_size_mb = sum(obj.size for obj in objects) / (1024 * 1024)
    print(f"✅ {removed_count} objetos removidos ({total_size_mb:.2f} MB liberados)")


if __name__ == "__main__":
    # Se passou --force como argumento, executa sem confirmação
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        clear_all_images_force()
    else:
        clear_all_images()
