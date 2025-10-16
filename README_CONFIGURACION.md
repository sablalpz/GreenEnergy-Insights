# Configuración del Sistema GreenEnergy Insights

## Cambiar entre SQLite (local) y Azure SQL (producción)

### Opción 1: SQLite Local (Desarrollo) - ACTUAL

**Ventajas:**
- No requiere conexión a internet
- Rápido para desarrollo y pruebas
- Sin costos de infraestructura

**Configuración actual en `Config.py`:**
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///greenergy_insights.db'
```

### Opción 2: Azure SQL Database (Producción)

**Ventajas:**
- Base de datos en la nube
- Escalable y con alta disponibilidad
- Accesible desde cualquier ubicación
- Respaldos automáticos

**Para cambiar a Azure SQL:**

1. Edita `Config.py`:
   ```python
   # Comenta esta línea:
   # SQLALCHEMY_DATABASE_URI = 'sqlite:///greenergy_insights.db'

   # Descomenta estas líneas:
   SQLALCHEMY_DATABASE_URI = (
       "mssql+pyodbc://ugrupo2:SYfL1sTc5EQzehpOjopx"
       "@udcserver2025.database.windows.net:1433/grupo_2"
       "?driver=ODBC+Driver+17+for+SQL+Server"
       "&Encrypt=yes"
       "&TrustServerCertificate=no"
       "&Connection+Timeout=30"
   )
   ```

2. Verifica que tengas instalado el driver ODBC:
   - Windows: [Descargar ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
   - Linux: `sudo apt-get install msodbcsql17`

3. Reinicia el servidor Flask:
   ```bash
   # Detén el servidor actual (Ctrl+C)
   python api.py
   ```

4. Ejecuta las migraciones iniciales:
   ```bash
   # Las tablas se crearán automáticamente al iniciar
   # Luego carga datos:
   curl http://127.0.0.1:5000/fetch_ree_data
   python ejecutar_motor.py
   ```

## Archivos del Proyecto

### Archivos NECESARIOS (no borrar):
```
api.py                          # API REST principal
Config.py                       # Configuración
models.py                       # Modelos de base de datos
requirements.txt                # Dependencias Python
ejecutar_motor.py              # Script para ejecutar motor de analítica
generar_datos_sinteticos.py    # Generador de datos de prueba
docker-compose.yml             # Orquestación de contenedores
Dockerfile                      # Imagen Docker

templates/
  └── dashboard.html           # Dashboard principal (ÚNICO HTML necesario)

motor_analitica/
  └── motor_analitica.py       # Motor de predicciones y anomalías
```

### Archivos OBSOLETOS (ya eliminados):
```
templates/visualizacion_datos_predicciones.html  #  ELIMINADO
templates/dashboard_anomalias_old.html           #  ELIMINADO
```

### Archivos IGNORADOS por Git (.gitignore):
```
__pycache__/                   # Cache de Python
.venv/                         # Entorno virtual
instance/                      # Base de datos SQLite
*.db, *.sqlite                 # Archivos de BD local
logs/                          # Logs de ejecución
*.log
models/*.pkl                   # Modelos entrenados
graficos/*.png                 # Gráficos generados
```

## Actualización de Datos

### Automática (Dashboard):
- El dashboard se actualiza **cada 60 segundos** automáticamente
- Ver línea 469 en `templates/dashboard.html`:
  ```javascript
  setInterval(cargarDatos, 60000); // Actualizar cada minuto
  ```

### Manual (Scripts):
```bash
# 1. Cargar datos de la API de REE
curl http://127.0.0.1:5000/fetch_ree_data

# 2. Ejecutar motor de analítica (predicciones + anomalías)
python ejecutar_motor.py

# 3. Generar datos sintéticos adicionales (para pruebas)
python generar_datos_sinteticos.py
```

## Migración de SQLite a Azure SQL

Si ya tienes datos en SQLite y quieres migrarlos a Azure:

```bash
# 1. Exportar datos de SQLite
sqlite3 instance/greenergy_insights.db .dump > backup.sql

# 2. Adaptar el SQL para SQL Server (cambios necesarios):
#    - AUTOINCREMENT → IDENTITY
#    - datetime() → GETDATE()
#    - INTEGER PRIMARY KEY → INT PRIMARY KEY IDENTITY

# 3. Cambiar Config.py a Azure SQL

# 4. Ejecutar el SQL adaptado en Azure
# (usar Azure Data Studio o SQL Server Management Studio)
```

## Verificación de Conexión

```bash
# Test de salud de la API
curl http://127.0.0.1:5000/api/health

# Respuesta esperada:
# {
#   "status": "healthy",
#   "database": "connected",
#   "timestamp": "..."
# }
```

