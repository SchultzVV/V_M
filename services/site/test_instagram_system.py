#!/usr/bin/env python3
"""
Script de teste rápido do sistema Instagram
Executa testes básicos de cada componente
"""
import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

import redis
from agents.product_decision_agent import ProductDecisionAgent
from agents.product_enricher_agent import ProductEnricherAgent
from agents.instagram_poster_agent import InstagramPosterAgent
from agents.instagram_orchestrator import InstagramPostOrchestrator


def test_redis_connection():
    """Testa conexão com Redis"""
    print("\n🔍 Testando conexão Redis...")
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        client = redis.from_url(redis_url, decode_responses=False)
        client.ping()
        print("✅ Redis conectado com sucesso")
        return client
    except Exception as e:
        print(f"❌ Erro ao conectar Redis: {e}")
        return None


def test_decision_agent(redis_client):
    """Testa agente decisor"""
    print("\n🎯 Testando Agente Decisor...")
    try:
        agent = ProductDecisionAgent(redis_client)
        result = agent.execute({})
        
        if result.get('success'):
            product = result['selected_product']
            print(f"✅ Produto selecionado: {product.get('title', 'N/A')[:50]}...")
            print(f"   Preço: R$ {product.get('price', 0):.2f}")
            print(f"   Razão: {result.get('reason', 'N/A')}")
            return product
        else:
            print(f"❌ Erro: {result.get('error')}")
            return None
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return None


def test_enricher_agent(redis_client, product):
    """Testa agente enriquecedor"""
    print("\n🎨 Testando Agente Enriquecedor...")
    try:
        agent = ProductEnricherAgent(redis_client)
        result = agent.execute({'selected_product': product})
        
        if result.get('success'):
            enriched = result['enriched_product']
            print(f"✅ Produto enriquecido")
            print(f"   Legenda: {enriched.get('caption', 'N/A')[:80]}...")
            print(f"   Hashtags: {', '.join(enriched.get('hashtags', [])[:5])}")
            print(f"   CTA: {enriched.get('call_to_action', 'N/A')}")
            return enriched
        else:
            print(f"❌ Erro: {result.get('error')}")
            return None
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return None


def test_image_generation(enriched_product):
    """Testa geração de imagem"""
    print("\n🖼️  Testando Geração de Imagem...")
    try:
        from services.instagram_image_service import InstagramImageGenerator
        
        generator = InstagramImageGenerator()
        image_path = generator.generate_product_image(
            enriched_product,
            layout='square',
            style='modern'
        )
        
        print(f"✅ Imagem gerada: {image_path}")
        return image_path
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return None


def test_full_orchestrator():
    """Testa orquestrador completo"""
    print("\n🚀 Testando Orquestrador Completo...")
    try:
        orchestrator = InstagramPostOrchestrator()
        
        result = orchestrator.run(
            filters={},
            simulate=True,  # Não posta de verdade
            post_type='photo'
        )
        
        if result.get('success'):
            print("✅ Orquestrador executado com sucesso")
            print(f"   Produto: {result['selected_product'].get('title', 'N/A')[:50]}")
            print(f"   Post URL: {result['post_result'].get('post_url', 'N/A')}")
            return True
        else:
            print("❌ Erro no orquestrador")
            for error in result.get('errors', []):
                print(f"   - {error}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("📸 TESTE DO SISTEMA INSTAGRAM AUTO POST")
    print("=" * 60)
    
    # Teste 1: Redis
    redis_client = test_redis_connection()
    if not redis_client:
        print("\n❌ Redis não disponível. Abortando testes.")
        return
    
    # Teste 2: Agente Decisor
    product = test_decision_agent(redis_client)
    if not product:
        print("\n❌ Agente Decisor falhou. Abortando testes.")
        return
    
    # Teste 3: Agente Enriquecedor
    enriched = test_enricher_agent(redis_client, product)
    if not enriched:
        print("\n❌ Agente Enriquecedor falhou. Abortando testes.")
        return
    
    # Teste 4: Geração de Imagem
    image_path = test_image_generation(enriched)
    if not image_path:
        print("\n⚠️  Geração de imagem falhou (pode ser problema de fontes)")
    
    # Teste 5: Orquestrador Completo
    test_full_orchestrator()
    
    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS")
    print("=" * 60)
    print("\n💡 Próximos passos:")
    print("   1. Verifique os logs acima")
    print("   2. Se tudo OK, use: make instagram-post")
    print("   3. Para ver imagem gerada: ls uploads/instagram/")
    print("")


if __name__ == "__main__":
    main()
