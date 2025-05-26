FROM python:3.10-slim

# Diretório de trabalho
WORKDIR /app

# Copia tudo para dentro do container
COPY . .

# Instala as dependências
RUN pip install -r requirements.txt

# Expõe a porta 5000
EXPOSE 5000

# Roda a aplicação Flask
CMD ["python", "main.py"]
