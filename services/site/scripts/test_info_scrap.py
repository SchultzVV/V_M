#!/usr/bin/env python3
"""
Script de teste para o serviço de extração de informações de imagens.
Envia uma imagem para o endpoint /extract e exibe os resultados.
"""

import sys
import requests
from pathlib import Path


def test_info_scrap(image_path: str):
    """
    Testa o serviço de extração enviando uma imagem.
    
    Args:
        image_path: Caminho para a imagem a ser testada
    """
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 TESTE DO SERVIÇO DE EXTRAÇÃO DE INFORMAÇÕES")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    
    # Verifica se a imagem existe
    img_file = Path(image_path)
    if not img_file.exists():
        print(f"❌ Erro: Imagem não encontrada: {image_path}")
        return False
    
    print(f"📁 Imagem: {img_file.name}")
    print(f"📏 Tamanho: {img_file.stat().st_size / 1024:.2f} KB")
    print()
    
    # Endpoint do serviço
    url = "http://info-scrap:8000/extract"
    
    try:
        print(f"🌐 Conectando ao serviço: {url}")
        print()
        
        # Prepara o arquivo para envio
        with open(img_file, 'rb') as f:
            files = {'file': (img_file.name, f, 'image/png')}
            
            print("📤 Enviando imagem para extração...")
            response = requests.post(url, files=files, timeout=60)
        
        print(f"📡 Status HTTP: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Extração realizada com sucesso!")
            print()
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("📄 RESULTADO DA EXTRAÇÃO:")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print()
            
            # Exibe o resultado formatado
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()
            
            return True
        else:
            print(f"❌ Erro na extração: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao serviço info-scrap")
        print()
        print("💡 Verifique se o container está rodando:")
        print("   docker ps | grep info-scrap")
        print()
        print("💡 Para subir o serviço:")
        print("   make up")
        return False
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 test_info_scrap.py <caminho_imagem>")
        print()
        print("Exemplo:")
        print("  python3 test_info_scrap.py /app/image_example.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    success = test_info_scrap(image_path)
    
    sys.exit(0 if success else 1)
