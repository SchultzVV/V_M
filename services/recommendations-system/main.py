"""
Recommendations System - Unified Entry Point
Inicia múltiplos serviços em processos separados
"""
import sys
import os
import subprocess
import time
from multiprocessing import Process

# Adiciona o diretório ao path
sys.path.insert(0, os.path.dirname(__file__))


def start_service(module_path, port, name):
    """Inicia um serviço específico"""
    print(f"🚀 Starting {name} on port {port}...")
    try:
        subprocess.run([
            "uvicorn",
            f"{module_path}:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload" if os.getenv("ENV", "production") == "development" else ""
        ])
    except Exception as e:
        print(f"❌ Error starting {name}: {e}")


def start_profile_builder_consumer():
    """Inicia o profile builder em modo consumer"""
    print("🚀 Starting Profile Builder (Consumer mode)...")
    try:
        subprocess.run(["python", "profile_builder/main.py"])
    except Exception as e:
        print(f"❌ Error starting Profile Builder: {e}")


def main():
    """
    Inicia todos os serviços
    
    Pode ser configurado via variável SERVICE para iniciar apenas um:
    SERVICE=api python main.py
    SERVICE=auth python main.py
    etc.
    """
    service = os.getenv("SERVICE", "all").lower()
    
    services = {
        "api": ("api.main", 8000, "API Gateway"),
        "auth": ("auth.main", 8001, "Auth Service"),
        "ingest": ("ingest.main", 8002, "Ingest Service"),
        "tracking": ("tracking.main", 8003, "Tracking Service"),
        "recommendations": ("recommendations.main", 8005, "Recommendations Service"),
    }
    
    if service == "all":
        print("🚀 Starting ALL services...")
        
        # Iniciar profile builder em processo separado
        profile_process = Process(target=start_profile_builder_consumer)
        profile_process.start()
        
        # Iniciar serviços HTTP
        processes = []
        for svc_name, (module, port, display_name) in services.items():
            p = Process(target=start_service, args=(module, port, display_name))
            p.start()
            processes.append(p)
            time.sleep(1)  # Delay para evitar race conditions
        
        # Aguardar todos os processos
        profile_process.join()
        for p in processes:
            p.join()
    
    elif service == "profile_builder":
        start_profile_builder_consumer()
    
    elif service in services:
        module, port, display_name = services[service]
        start_service(module, port, display_name)
    
    else:
        print(f"❌ Unknown service: {service}")
        print(f"Available services: {', '.join(['all', 'profile_builder'] + list(services.keys()))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
