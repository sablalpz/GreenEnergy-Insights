FROM python:3.10-slim-bullseye

WORKDIR /app/chatbot

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Instalar dependencias del sistema necesarias para pyodbc y builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    unixodbc-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Registrar repositorio de Microsoft y (opcional) instalar driver ODBC 17
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

# Copiar el contenido del contexto (./chatbot) al directorio de la app en la imagen
COPY . /app/chatbot

# Instalar dependencias Python conocidas (nota: instalar torch puede requerir ruedas específicas para tu plataforma/GPU)
COPY requirements.chatbot.txt /app/requirements.chatbot.txt
# Instalar PyTorch CPU-only explícitamente (usa el índice de PyTorch para ruedas CPU)
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch || true
RUN pip install --no-cache-dir -r /app/requirements.chatbot.txt

# Ejecutable por defecto: lanza el script interactivo
ENTRYPOINT ["python", "Streamlit.py"]
