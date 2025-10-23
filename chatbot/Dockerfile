FROM python:3.10-slim-bullseye

WORKDIR /app/chatbot

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Instalar dependencias del sistema necesarias para pyodbc y compilaciones
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    unixodbc-dev \
    g++ \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Registrar el repositorio de Microsoft e instalar el driver ODBC 18
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    rm -rf /var/lib/apt/lists/*

# Copiar el contenido del contexto (./chatbot) al directorio de la app
COPY . /app/chatbot

# Instalar dependencias Python conocidas (nota: instalar torch puede requerir ruedas específicas para tu plataforma/GPU)
COPY requirements.chatbot.txt /app/requirements.chatbot.txt

# Instalar PyTorch CPU-only explícitamente (usa el índice de PyTorch para ruedas CPU)
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch || true

# Instalar dependencias Python del chatbot
RUN pip install --no-cache-dir -r /app/requirements.chatbot.txt

# Ejecutable por defecto: lanza el script interactivo
ENTRYPOINT ["streamlit", "run", "Streamlit.py", "--server.port=5003", "--server.address=0.0.0.0", "--browser.serverAddress=0.0.0.0"]