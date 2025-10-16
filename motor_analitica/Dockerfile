FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg \
    gcc \
    g++ \
    unixodbc-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

#Establecer conexión con Azure
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    install -o root -g root -m 644 microsoft.gpg /usr/share/keyrings/microsoft.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/* microsoft.gpg


# Copiar dependencias del ETL
COPY requirements.motor.txt .
RUN pip install --no-cache-dir -r requirements.motor.txt

# Copiar el código fuente del ETL
COPY . /app

# Importar el código común como volumen
ENV PYTHONPATH=/app


CMD ["python", "motor_analitica.py"]
