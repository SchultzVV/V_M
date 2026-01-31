FROM python:3.11-slim

LABEL maintainer="V_M Team"
LABEL description="Sistema de Recomendações Personalizadas com Instagram"
LABEL version="1.0.0"

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código do sistema
COPY . .

# Criar diretório para logs
RUN mkdir -p /app/logs

# Expor portas de todos os serviços
EXPOSE 8000 8001 8002 8003 8005

# Health check no API Gateway
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Variável de ambiente para controlar qual serviço iniciar
ENV SERVICE=all
ENV PYTHONUNBUFFERED=1

# Comando padrão: iniciar todos os serviços
CMD ["python", "main.py"]
