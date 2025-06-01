import os
import json
import requests

STAGING_DIR = "staging"
PROCESSED_FILE = os.path.join(STAGING_DIR, ".processed")
API_ENDPOINT = "http://localhost:5000/add_product"

# Carrega os arquivos já processados
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed_files = set(f.read().splitlines())
else:
    processed_files = set()

newly_processed = []

# Processa novos arquivos
for filename in os.listdir(STAGING_DIR):
    if not filename.endswith(".json") or filename in processed_files or filename == ".processed":
        continue

    path = os.path.join(STAGING_DIR, filename)
    try:
        with open(path, "r") as f:
            data = json.load(f)

        response = requests.post(API_ENDPOINT, json=data)

        if response.status_code == 201:
            print(f"[OK] Produto adicionado: {filename}")
            newly_processed.append(filename)
        else:
            print(f"[ERRO] {filename} - {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[FALHA] {filename} - {str(e)}")

# Atualiza .processed
if newly_processed:
    with open(PROCESSED_FILE, "a") as f:
        for fname in newly_processed:
            f.write(fname + "\n")
