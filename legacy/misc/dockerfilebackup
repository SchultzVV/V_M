# 📦 Imagem base otimizada
FROM python:3.10-slim

# 🧱 Dependências do sistema para PostgreSQL + Playwright
RUN apt-get update && apt-get install -y \
    libpq-dev gcc curl unzip \
    wget fonts-liberation libnss3 libatk-bridge2.0-0 libxss1 \
    libasound2 libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 xdg-utils libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# 🧪 Instala Playwright e os browsers
RUN pip install playwright && playwright install --with-deps

# 📁 Define o diretório da aplicação
WORKDIR /app

# 🗂️ Copia os arquivos para dentro do container
COPY . .

# 📦 Argumento para alternar entre requirements-dev.txt e requirements.txt
ARG REQUIREMENTS=requirements-dev.txt

# 📦 Instala dependências da aplicação
RUN pip install --no-cache-dir -r $REQUIREMENTS

# 🔌 Porta exposta pela aplicação Flask
EXPOSE 5000

# 🚀 Comando padrão de inicialização
CMD ["python", "main.py"]
