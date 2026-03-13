#!/usr/bin/env python3
"""
Script sincroniza todos os links de produtos já preparados em staging
para o arquivo central de short_links (staging/short_link/links.json).

Uso:
    python scripts/sync_short_links.py
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

try:
    from prepare_ml_best import append_short_link_entry
    from auto_prepare_ml import extract_ml_product_id
except ImportError as e:
    print(f"❌ Erro ao importar funções: {e}")
    sys.exit(1)


def resolve_short_link(url: str) -> tuple[str, str]:
    """
    Segue um link curto para descobrir a URL final.
    Retorna (url_inicial, url_final) ou (url, url) se não for um short link.
    """
    url = (url or "").strip()
    if not url:
        return ("", "")

    # Se não é um link short (meli.la, t.co, etc), retorna como-é
    if not any(domain in url for domain in ["meli.la", "bit.ly", "t.co", "short.", "tinyurl"]):
        return (url, url)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        return (url, response.url)
    except Exception as e:
        print(f"   ⚠️  Erro ao resolver {url}: {e}")
        return (url, url)


def sync_staging_links_to_short_link():
    """
    Sincroniza todos os links de staging JSONs para short_link/links.json
    """
    staging_root = Path("/app/staging")
    short_link_file = Path("/app/staging/short_link/links.json")

    if not staging_root.exists():
        print(f"❌ Diretório {staging_root} não existe")
        return 0

    print("=" * 70)
    print("🔗 SINCRONIZANDO SHORT LINKS DE STAGING")
    print("=" * 70)
    print(f"\n📂 Procurando JSONs em: {staging_root}\n")

    # Encontrar todos os JSONs de produtos
    json_files = list(staging_root.glob("*/*/*.json")) + list(staging_root.glob("*/*.json"))
    json_files = sorted(set(json_files))

    if not json_files:
        print("   ℹ️  Nenhum JSON de produto encontrado em staging")
        return 0

    print(f"   Found {len(json_files)} JSONs para processar\n")

    added_count = 0
    skipped_count = 0
    error_count = 0

    for json_path in json_files:
        # Pular o próprio links.json
        if "short_link" in str(json_path):
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            link = data.get("link", "").strip()
            if not link:
                print(f"   ⏩ {json_path.name} — sem campo 'link'")
                skipped_count += 1
                continue

            # Extrair URL inicial e final
            initial_url, final_url = resolve_short_link(link)

            # Extrair product_url se disponível
            external_id = data.get("external_id", "")
            product_url = ""
            if external_id:
                product_url = f"https://www.mercadolivre.com.br/p/{external_id.replace('-', '')}"
            elif "mercadolivre" in final_url or "mercadolibre" in final_url:
                product_url = final_url

            # Adicionar ao short_link file
            added = append_short_link_entry(initial_url, final_url, product_url)

            if added:
                status = "✅ Adicionado"
                added_count += 1
            else:
                status = "ℹ️  Já existe"
                skipped_count += 1

            title = data.get("title", "?")[:50]
            print(f"   {status}: {title}")

        except json.JSONDecodeError:
            print(f"   ❌ Erro JSON: {json_path.name}")
            error_count += 1
        except Exception as e:
            print(f"   ❌ Erro: {json_path.name} — {e}")
            error_count += 1

    print(f"\n" + "=" * 70)
    print(f"📊 RESUMO")
    print("=" * 70)
    print(f"   ✅ Adicionados: {added_count}")
    print(f"   ℹ️  Já existentes: {skipped_count}")
    print(f"   ❌ Erros: {error_count}")
    print(f"   📄 Total processado: {len(json_files)}")

    # Mostrar arquivo final
    if short_link_file.exists():
        data = json.loads(short_link_file.read_text(encoding="utf-8"))
        total = len(data.get("links", []))
        print(f"\n   📁 links.json agora tem {total} entradas")

    print("=" * 70 + "\n")

    return added_count


if __name__ == "__main__":
    sync_staging_links_to_short_link()
