from flask_sqlalchemy import SQLAlchemy

# Crear una única instancia global de SQLAlchemy
db = SQLAlchemy()

# Importaciones relativas para que estén disponibles al importar "common"
from .Config import Config  # Configuración general de la app
from .database import User, EnergyData, create_app # Modelos de base de datos
