from flask_sqlalchemy import SQLAlchemy

# Crear una única instancia global de SQLAlchemy
db = SQLAlchemy()

# Importaciones relativas para que estén disponibles al importar "common"
from .Config import Config  # Configuración general de la app
from .database import User, EnergyData, Prediction, Anomaly, ModelMetric, create_app # Modelos de base de datos
from .db_access import row_to_dict, guardar_registro, guardar_registros_desde_df, guardar_metricas, \
    obtener_registros, limpiar_registros_antiguos, obtener_estadisticas  # Funciones de acceso a datos