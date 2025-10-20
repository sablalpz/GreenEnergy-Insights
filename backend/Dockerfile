FROM python:3.10-slim-bullseye

WORKDIR /app

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Instalar dependencias del sistema necesarias (sin paquetes recomendados)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    apt-transport-https \
    gcc \
    g++ \
    unixodbc-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Registrar repositorio de Microsoft y instalar el driver ODBC 17
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

# Copiar dependencias de Python e instalarlas
COPY requirements.back.txt /app/requirements.back.txt
RUN pip install --no-cache-dir -r /app/requirements.back.txt

# Copiar el código fuente
COPY . /app

EXPOSE 5000

# Ejecutar el backend principal (ahora backend/backend.py es la entrada)
CMD ["python", "backend.py"]
