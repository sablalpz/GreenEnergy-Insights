"""
Script de persistencia para predicciones, anomalías y métricas del modelo usando funciones genéricas de db_access.
"""
from common.db_access import (
    guardar_registro,
    guardar_registros_desde_df,
    guardar_metricas,
    obtener_registros,
    limpiar_registros_antiguos,
    obtener_estadisticas
)
from common import db
from datetime import datetime

# Importa tus modelos aquí
from common import Prediction, Anomaly, ModelMetric

# Ejemplo de uso para guardar una predicción
def guardar_prediccion(session, **kwargs):
    return guardar_registro(Prediction, session, **kwargs)

# Ejemplo de uso para guardar varias predicciones desde un DataFrame
def guardar_predicciones_df(session, df, modelo_usado):
    fecha_generacion = datetime.now()
    return guardar_registros_desde_df(
        df,
        Prediction,
        session,
        unique_fields=["timestamp", "modelo_usado"],
        extra_fields={"modelo_usado": modelo_usado, "fecha_generacion": fecha_generacion}
    )

# Guardar anomalías desde DataFrame
def guardar_anomalias_df(session, df, metodo_deteccion):
    fecha_deteccion = datetime.now()
    return guardar_registros_desde_df(
        df,
        Anomaly,
        session,
        unique_fields=["timestamp", "metodo_deteccion"],
        extra_fields={"metodo_deteccion": metodo_deteccion, "fecha_deteccion": fecha_deteccion}
    )

# Guardar métricas del modelo
def guardar_metricas_modelo(session, nombre_modelo, metricas_dict, n_samples=None, metadata=None):
    return guardar_metricas(ModelMetric, session, nombre_modelo, metricas_dict, n_samples, metadata)

# Consultar predicciones
def consultar_predicciones(session, modelo=None, limit=100):
    filtros = {"modelo_usado": modelo} if modelo else None
    return obtener_registros(Prediction, session, filters=filtros, order_by="timestamp.desc()", limit=limit)

# Consultar anomalías
def consultar_anomalias(session, severidad=None, limit=100):
    filtros = {"severidad": severidad} if severidad else None
    return obtener_registros(Anomaly, session, filters=filtros, order_by="timestamp.desc()", limit=limit)

# Consultar métricas
def consultar_metricas(session, modelo=None, limit=10):
    filtros = {"nombre_modelo": modelo} if modelo else None
    return obtener_registros(ModelMetric, session, filters=filtros, order_by="timestamp.desc()", limit=limit)

# Limpiar predicciones antiguas
def limpiar_predicciones_antiguas(session, dias=30):
    return limpiar_registros_antiguos(Prediction, session, "fecha_generacion", dias)

# Evaluar si se deben mantener los datos en la base de datos
def evaluar_mantenimiento(session, tabla, dias=30):
    """
    Elimina registros antiguos de la tabla indicada si es necesario.
    Args:
        session: sesión de SQLAlchemy
        tabla: clase del modelo (Prediction, Anomaly, ModelMetric)
        dias: número de días a mantener
    Returns:
        int: número de registros eliminados
    """
    fecha_field = "fecha_generacion" if tabla == Prediction else "fecha_deteccion" if tabla == Anomaly else "timestamp"
    return limpiar_registros_antiguos(tabla, session, fecha_field, dias)

# Obtener estadísticas generales
def obtener_stats(session):
    return obtener_estadisticas(session, {
        "predicciones": Prediction,
        "anomalias": Anomaly,
        "metricas": ModelMetric
    })
