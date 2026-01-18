#!/usr/bin/env python3
"""
Exemplos práticos de uso do Sistema Instagram
Execute: python3 examples_instagram.py
"""

import requests
import json
import time
from datetime import datetime, timedelta


BASE_URL = "http://localhost:5000"


def example_1_simple_post():
    """Exemplo 1: Post automático simples"""
    print("\n" + "="*60)
    print("EXEMPLO 1: Post Automático Simples")
    print("="*60)
    
    # Posta automaticamente (modo teste)
    response = requests.post(
        f"{BASE_URL}/instagram/post/auto",
        params={"simulate": True}
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
    if result['success']:
        print(f"Produto: {result.get('product_title', 'N/A')}")
        print(f"Post URL: {result.get('post_url', 'N/A')}")


def example_2_filtered_post():
    """Exemplo 2: Post com filtros específicos"""
    print("\n" + "="*60)
    print("EXEMPLO 2: Post com Filtros")
    print("="*60)
    
    # Posta apenas produtos na faixa de R$ 50-300
    payload = {
        "filters": {
            "tag": "geral",
            "min_price": 50,
            "max_price": 300
        },
        "simulate": True,
        "post_type": "photo"
    }
    
    response = requests.post(
        f"{BASE_URL}/instagram/post",
        json=payload
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
    if result['success']:
        print(f"Produto: {result['product']['title']}")
        print(f"Preço: R$ {result['product']['price']:.2f}")
        print(f"Legenda: {result['caption'][:80]}...")


def example_3_custom_caption():
    """Exemplo 3: Post com legenda personalizada"""
    print("\n" + "="*60)
    print("EXEMPLO 3: Post com Legenda Personalizada")
    print("="*60)
    
    payload = {
        "filters": {},
        "simulate": True,
        "custom_caption": "🔥 SUPER OFERTA DO DIA! 🔥\n\nNão perca esta oportunidade incrível!"
    }
    
    response = requests.post(
        f"{BASE_URL}/instagram/post",
        json=payload
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
    if result['success']:
        print(f"Legenda usada: {result['caption'][:100]}...")


def example_4_carousel_post():
    """Exemplo 4: Post em carrossel (múltiplas imagens)"""
    print("\n" + "="*60)
    print("EXEMPLO 4: Post em Carrossel")
    print("="*60)
    
    payload = {
        "filters": {},
        "simulate": True,
        "post_type": "carousel"  # Gera múltiplas imagens
    }
    
    response = requests.post(
        f"{BASE_URL}/instagram/post",
        json=payload
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
    if result['success']:
        print(f"Produto: {result['product']['title']}")
        print(f"Tipo: Carrossel")


def example_5_check_status():
    """Exemplo 5: Verificar status do sistema"""
    print("\n" + "="*60)
    print("EXEMPLO 5: Status do Sistema")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/instagram/status")
    status = response.json()
    
    print(f"\nStatus Geral: {status['status']}")
    print(f"\nComponentes:")
    for component, state in status['components'].items():
        emoji = "✅" if state in ['ok', 'configured', 'loaded'] else "⚠️"
        print(f"  {emoji} {component}: {state}")
    
    print(f"\nStaging:")
    print(f"  📦 Produtos disponíveis: {status['staging']['products_available']}")


def example_6_view_history():
    """Exemplo 6: Ver histórico de posts"""
    print("\n" + "="*60)
    print("EXEMPLO 6: Histórico de Posts")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/instagram/history",
        params={"limit": 5}
    )
    
    history = response.json()
    
    print(f"\nTotal de posts: {history['count']}")
    print("\nÚltimos posts:")
    for post in history['posts'][:5]:
        print(f"  • {post.get('product_id', 'N/A')} - {post.get('post_url', 'N/A')}")


def example_7_test_image_generation():
    """Exemplo 7: Testar geração de imagem sem postar"""
    print("\n" + "="*60)
    print("EXEMPLO 7: Teste de Geração de Imagem")
    print("="*60)
    
    # Você precisa ter um produto no staging para testar
    # Substitua pelo ID real de um produto seu
    payload = {
        "product_id": "MLB19571567"  # Exemplo
    }
    
    response = requests.post(
        f"{BASE_URL}/instagram/test/image",
        json=payload
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
    if result['success']:
        print(f"Imagens geradas:")
        for img_path in result.get('image_paths', []):
            print(f"  • {img_path}")
        print(f"\nLegenda: {result.get('caption', 'N/A')[:80]}...")


def example_8_schedule_post():
    """Exemplo 8: Agendar post para o futuro"""
    print("\n" + "="*60)
    print("EXEMPLO 8: Agendar Post")
    print("="*60)
    
    # Agenda para daqui a 2 horas
    scheduled_time = int((datetime.now() + timedelta(hours=2)).timestamp())
    
    payload = {
        "scheduled_time": scheduled_time,
        "filters": {"tag": "geral"}
    }
    
    response = requests.post(
        f"{BASE_URL}/instagram/schedule",
        json=payload
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Agendado' if result['success'] else '❌ Erro'}")
    if result['success']:
        scheduled_dt = datetime.fromtimestamp(result['scheduled_time'])
        print(f"Agendado para: {scheduled_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Key no Redis: {result['schedule_key']}")


def example_9_workflow_info():
    """Exemplo 9: Ver informações do workflow"""
    print("\n" + "="*60)
    print("EXEMPLO 9: Informações do Workflow")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/instagram/workflow")
    workflow = response.json()
    
    if workflow['success']:
        print("\nWorkflow dos Agentes:")
        print(workflow['workflow_diagram'])
        
        print("\nAgentes:")
        for agent in workflow['agents']:
            print(f"  {agent['order']}. {agent['name']}")
            print(f"     {agent['description']}")


def example_10_production_post():
    """Exemplo 10: Post real em produção (use com cuidado!)"""
    print("\n" + "="*60)
    print("EXEMPLO 10: Post em PRODUÇÃO")
    print("="*60)
    print("\n⚠️  ATENÇÃO: Este exemplo vai POSTAR DE VERDADE no Instagram!")
    
    confirm = input("Digite 'SIM' para continuar ou qualquer tecla para cancelar: ")
    
    if confirm != 'SIM':
        print("❌ Operação cancelada")
        return
    
    payload = {
        "filters": {},
        "simulate": False,  # ⚠️  POSTA DE VERDADE!
        "post_type": "photo"
    }
    
    response = requests.post(
        f"{BASE_URL}/instagram/post",
        json=payload
    )
    
    result = response.json()
    
    print(f"\nStatus: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
    if result['success']:
        print(f"\n🎉 Post criado com sucesso!")
        print(f"📸 URL: {result['post_url']}")
        print(f"📦 Produto: {result['product']['title']}")
        print(f"💰 Preço: R$ {result['product']['price']:.2f}")
    else:
        print(f"\n❌ Erro ao criar post:")
        for error in result.get('errors', []):
            print(f"   - {error}")


def main():
    """Menu interativo de exemplos"""
    print("\n" + "="*80)
    print(" "*20 + "📸 EXEMPLOS PRÁTICOS - SISTEMA INSTAGRAM")
    print("="*80)
    
    examples = [
        ("Post Automático Simples", example_1_simple_post),
        ("Post com Filtros", example_2_filtered_post),
        ("Post com Legenda Personalizada", example_3_custom_caption),
        ("Post em Carrossel", example_4_carousel_post),
        ("Verificar Status do Sistema", example_5_check_status),
        ("Ver Histórico de Posts", example_6_view_history),
        ("Testar Geração de Imagem", example_7_test_image_generation),
        ("Agendar Post Futuro", example_8_schedule_post),
        ("Informações do Workflow", example_9_workflow_info),
        ("Post em PRODUÇÃO (cuidado!)", example_10_production_post)
    ]
    
    while True:
        print("\n" + "-"*80)
        print("Escolha um exemplo para executar:")
        print("-"*80)
        
        for i, (name, _) in enumerate(examples, 1):
            print(f"  {i}. {name}")
        
        print("  0. Sair")
        print("-"*80)
        
        try:
            choice = int(input("\nDigite o número do exemplo: "))
            
            if choice == 0:
                print("\n👋 Até logo!")
                break
            
            if 1 <= choice <= len(examples):
                examples[choice - 1][1]()
                input("\nPressione ENTER para continuar...")
            else:
                print("❌ Opção inválida!")
        
        except ValueError:
            print("❌ Digite um número válido!")
        except KeyboardInterrupt:
            print("\n\n👋 Até logo!")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            input("\nPressione ENTER para continuar...")


if __name__ == "__main__":
    # Verifica se o servidor está rodando
    try:
        response = requests.get(f"{BASE_URL}/instagram/status", timeout=2)
        if response.ok:
            main()
        else:
            print("❌ Servidor não está respondendo corretamente")
            print("Execute: make up")
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao servidor")
        print("Execute: make up")
    except Exception as e:
        print(f"❌ Erro: {e}")
