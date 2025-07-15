FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r services/site/requirements-prd.txt

EXPOSE 5000

CMD ["python", "main.py"]
