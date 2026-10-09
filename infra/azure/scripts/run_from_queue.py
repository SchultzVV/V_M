#!/usr/bin/env python3
"""
Wrapper do job por evento (Azure Container Apps Job + KEDA azure-queue).

O KEDA só conta mensagens; ele não entrega o conteúdo ao job. Este script
tira UMA mensagem da fila `events`, executa `python3 <args>` com o payload e
apaga a mensagem se o comando terminar com sucesso.

Mensagem (JSON):  {"args": ["scripts/api_update_ml.py", "https://meli.la/xxx"]}

Env esperado (já definido pelo Terraform):
  AZURE_STORAGE_ACCOUNT  nome da conta
  EVENTS_QUEUE           nome da fila (events)
  AZURE_CLIENT_ID        client id da identidade user-assigned (DefaultAzureCredential)

Deps (Δ código na imagem): pip install azure-identity azure-storage-queue
Copiar para a imagem:      COPY infra/azure/scripts /app/infra_scripts
"""
import json
import os
import subprocess
import sys

from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient

ACCOUNT = os.environ["AZURE_STORAGE_ACCOUNT"]
QUEUE = os.environ.get("EVENTS_QUEUE", "events")
VISIBILITY = int(os.environ.get("EVENTS_VISIBILITY_TIMEOUT", "1500"))  # < replica_timeout
ALLOWED_PREFIXES = ("scripts/", "agents/")


def main() -> int:
    client = QueueClient(
        account_url=f"https://{ACCOUNT}.queue.core.windows.net",
        queue_name=QUEUE,
        credential=DefaultAzureCredential(),
    )
    msg = next(client.receive_messages(max_messages=1, visibility_timeout=VISIBILITY), None)
    if msg is None:
        print("[run_from_queue] fila vazia; nada a fazer")
        return 0

    try:
        payload = json.loads(msg.content)
        args = payload["args"]
        if not isinstance(args, list) or not args or not str(args[0]).startswith(ALLOWED_PREFIXES):
            raise ValueError(f"args inválidos: {args!r}")
    except Exception as exc:  # mensagem malformada: descarta para não envenenar a fila
        print(f"[run_from_queue] mensagem inválida ({exc}); apagando: {msg.content!r}")
        client.delete_message(msg)
        return 0

    cmd = [sys.executable, *map(str, args)]
    print(f"[run_from_queue] executando: {' '.join(cmd)}")
    rc = subprocess.call(cmd, cwd="/app")
    if rc == 0:
        client.delete_message(msg)
        print("[run_from_queue] ok; mensagem removida")
    else:
        # deixa a mensagem voltar à fila após o visibility timeout (retry natural)
        print(f"[run_from_queue] comando falhou (rc={rc}); mensagem volta à fila")
    return rc


if __name__ == "__main__":
    sys.exit(main())
