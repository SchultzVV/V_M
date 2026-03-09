#!/usr/bin/env python3
"""
Script de teste para acessar a API interna da Shopee
"""
import requests
import json

shop_id = "1103946075"
item_id = "22597120770"

# Testar endpoints diferentes da Shopee
endpoints = [
    f"https://shopee.com.br/api/v4/item/get?shopid={shop_id}&itemid={item_id}",
    f"https://shopee.com.br/api/v2/item/get?shop_id={shop_id}&item_id={item_id}",
    f"https://shopee.com.br/api/v4/product/get_shop_info?shop_ids={shop_id}",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': f'https://shopee.com.br/opaanlp/{shop_id}/{item_id}',
    'Accept': 'application/json',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'X-Requested-With': 'XMLHttpRequest',
}

for i, url in enumerate(endpoints, 1):
    print(f"\n{'='*70}")
    print(f"TESTE {i}: {url}")
    print('='*70)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Resposta JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        else:
            print(f"Erro: {response.text[:200]}")
    
    except Exception as e:
        print(f"Erro: {e}")
