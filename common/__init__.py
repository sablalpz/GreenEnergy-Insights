from flask_sqlalchemy import SQLAlchemy

# Crear una única instancia global de SQLAlchemy
db = SQLAlchemy()

# Importaciones relativas para que estén disponibles al importar "common"
from .Config import Config  # Configuración general de la app
from .database import User, EnergyData, Prediction, Anomaly, ModelMetric, create_app # Modelos de base de datos
from .db_access import guardar_energydata, guardar_anomalias, guardar_predicciones, guardar_metricas, obtener_anomalias, obtener_predicciones, obtener_ultimas_metricas, limpiar_predicciones_antiguas, obtener_estadisticas