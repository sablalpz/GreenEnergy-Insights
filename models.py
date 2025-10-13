"""
=================================================================================
MODELOS DE BASE DE DATOS - GreenEnergy Insights
=================================================================================

Modelos SQLAlchemy unificados para todas las tablas del sistema.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class EnergyData(db.Model):
    """
    Tabla principal: Datos históricos de energía desde API REE
    """
    __tablename__ = "energy_data"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, unique=True, nullable=False, index=True)
    precio = db.Column(db.Float, nullable=False)
    geo_id = db.Column(db.Integer, nullable=True)
    dia_semana = db.Column(db.Integer, nullable=True)
    hora_dia = db.Column(db.Integer, nullable=True)
    fin_de_semana = db.Column(db.Boolean, nullable=True)
    estacion = db.Column(db.String(10), nullable=True)
    demanda = db.Column(db.Float, nullable=True)

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "precio": self.precio,
            "demanda": self.demanda,
            "geo_id": self.geo_id,
            "dia_semana": self.dia_semana,
            "hora_dia": self.hora_dia,
            "fin_de_semana": self.fin_de_semana,
            "estacion": self.estacion
        }


class Prediction(db.Model):
    """
    Tabla: Predicciones generadas por el motor de analítica
    """
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    prediccion = db.Column(db.Float, nullable=False)
    limite_inferior = db.Column(db.Float, nullable=True)
    limite_superior = db.Column(db.Float, nullable=True)
    modelo_usado = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "prediccion": self.prediccion,
            "limite_inferior": self.limite_inferior,
            "limite_superior": self.limite_superior,
            "modelo_usado": self.modelo_usado,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Anomaly(db.Model):
    """
    Tabla: Anomalías detectadas en los datos
    """
    __tablename__ = "anomalies"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    tipo_anomalia = db.Column(db.String(50), nullable=False, index=True)
    severidad = db.Column(db.String(20), nullable=False, index=True)
    metodo_deteccion = db.Column(db.String(50), nullable=False)
    score_anomalia = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "value": self.value,
            "tipo_anomalia": self.tipo_anomalia,
            "severidad": self.severidad,
            "metodo_deteccion": self.metodo_deteccion,
            "score_anomalia": self.score_anomalia,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ModelMetric(db.Model):
    """
    Tabla: Métricas de rendimiento de los modelos
    """
    __tablename__ = "model_metrics"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_modelo = db.Column(db.String(50), nullable=False, index=True)
    mape = db.Column(db.Float, nullable=True)
    smape = db.Column(db.Float, nullable=True)
    rmse = db.Column(db.Float, nullable=True)
    mae = db.Column(db.Float, nullable=True)
    r2 = db.Column(db.Float, nullable=True)
    n_samples = db.Column(db.Integer, nullable=False)
    model_metadata = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "nombre_modelo": self.nombre_modelo,
            "mape": self.mape,
            "smape": self.smape,
            "rmse": self.rmse,
            "mae": self.mae,
            "r2": self.r2,
            "n_samples": self.n_samples,
            "model_metadata": self.model_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
