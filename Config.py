class Config:
    # Conexión a base de datos - Usar SQLite local si Azure no está disponible
    # Para usar Azure SQL, descomenta las siguientes líneas y comenta SQLALCHEMY_DATABASE_URI con SQLite

    # Azure SQL Database (comentado por defecto)
    # SQLALCHEMY_DATABASE_URI = (
    #     "mssql+pyodbc://ugrupo2:SYfL1sTc5EQzehpOjopx"
    #     "@udcserver2025.database.windows.net:1433/grupo_2"
    #     "?driver=ODBC+Driver+17+for+SQL+Server"
    #     "&Encrypt=yes"
    #     "&TrustServerCertificate=no"
    #     "&Connection+Timeout=30"
    # )

    # SQLite local (por defecto para desarrollo)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///greenergy_insights.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Token API REE
    REE_API_TOKEN = "ddcbd54fa41b494243f3a6094062af3f41a4675956a8f50a2b92b80bd0fbc71a"