FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias (ODBC y compiladores)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias del backend
COPY requirements.back.txt .
RUN pip install --no-cache-dir -r requirements.back.txt

# Copiar el código fuente del backend
COPY . /app

# Importar el código común como volumen (en el compose se monta)
ENV PYTHONPATH=/app

EXPOSE 5001

CMD ["python", "backend.py"]
