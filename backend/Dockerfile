FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    gcc \
    g++ \
    unixodbc-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Registrar repositorio de Microsoft y instalar el driver ODBC 17
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    install -o root -g root -m 644 microsoft.gpg /usr/share/keyrings/microsoft.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/* microsoft.gpg

# Copiar dependencias de Python
COPY requirements.back.txt .
RUN pip install --no-cache-dir -r requirements.back.txt

# Copiar el código fuente
COPY . /app

# Añadir el código común al PYTHONPATH
ENV PYTHONPATH=/app

EXPOSE 5001

CMD ["python", "backend.py"]
