FROM python:3.10-slim

# Instala dependências do sistema para o Chromium
RUN apt-get update && apt-get install -y \
    wget curl unzip fonts-liberation libnss3 libatk-bridge2.0-0 libxss1 \
    libasound2 libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils libgbm1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install playwright && playwright install --with-deps

EXPOSE 5000

CMD ["python", "main.py"]
