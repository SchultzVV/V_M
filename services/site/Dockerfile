# 📦 Imagem base otimizada
FROM python:3.10-slim

# 🧱 Dependências do sistema para PostgreSQL + Playwright (Debian/trixie)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # suas deps atuais
    libpq-dev gcc curl unzip wget xdg-utils \
    fonts-liberation libnss3 libatk-bridge2.0-0 libxss1 \
    libasound2 libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 \
    # complementos necessários p/ Chromium/Firefox no Debian
    ca-certificates gnupg libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 \
    libxfixes3 libxtst6 libxext6 libxcb1 libx11-6 \
    libpangocairo-1.0-0 libpango-1.0-0 libharfbuzz0b \
    libfreetype6 libfontconfig1 libgdk-pixbuf-2.0-0 \
    libjpeg62-turbo libpng16-16 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 🧪 Instala Playwright e os browsers (sem --with-deps no Debian)
RUN pip install --no-cache-dir playwright==1.54.0 \
 && playwright install  # ou: playwright install chromium

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
