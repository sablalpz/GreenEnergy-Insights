class Config:
    # Conexión a Azure SQL Database
    SQLALCHEMY_DATABASE_URI = (
        "mssql+pyodbc://ugrupo2:SYfL1sTc5EQzehpOjopx"
        "@udcserver2025.database.windows.net:1433/grupo_2"
        "?driver=ODBC+Driver+17+for+SQL+Server"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Token API REE
    REE_API_TOKEN = "ddcbd54fa41b494243f3a6094062af3f41a4675956a8f50a2b92b80bd0fbc71a"