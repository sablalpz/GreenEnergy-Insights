"""
=================================================================================
MÓDULO DE PERSISTENCIA PARA PREDICCIONES, ANOMALÍAS Y MÉTRICAS
=================================================================================

Este módulo proporciona funciones para guardar predicciones, anomalías y
métricas del modelo en tablas separadas de Azure SQL Database.

Tablas:
- predictions: Predicciones generadas por el modelo
- anomalies: Anomalías detectadas en los datos
- model_metrics: Métricas de rendimiento del modelo
"""

import sys
import os
from flask import Flask
from datetime import datetime, timedelta
import json

# Agregar el directorio padre al path para importar Config y models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Config import Config
from models import db, Prediction, Anomaly, ModelMetric

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# =============================================================================
# FUNCIONES DE GUARDADO
# =============================================================================

def guardar_predicciones(predicciones_df, modelo_usado="prophet"):
    """
    Guarda predicciones en la tabla predictions.

    Args:
        predicciones_df: DataFrame con columnas 'timestamp', 'prediccion',
                         'limite_inferior' (opcional), 'limite_superior' (opcional)
        modelo_usado: Nombre del modelo usado (por defecto: 'prophet')

    Returns:
        int: Número de predicciones guardadas
    """
    with app.app_context():
        nuevas = 0

        for _, row in predicciones_df.iterrows():
            # Verificar si ya existe
            existe = Prediction.query.filter_by(
                timestamp=row['timestamp'],
                modelo_usado=modelo_usado
            ).first()

            if not existe:
                pred = Prediction(
                    timestamp=row['timestamp'],
                    prediccion=row['prediccion'],
                    limite_inferior=row.get('limite_inferior'),
                    limite_superior=row.get('limite_superior'),
                    modelo_usado=modelo_usado
                )
                db.session.add(pred)
                nuevas += 1

        db.session.commit()
        print(f"   ✓ Guardadas {nuevas} predicciones nuevas")
        return nuevas


def guardar_anomalias(anomalias_df, metodo_deteccion="motor_analitica"):
    """
    Guarda anomalías en la tabla anomalies.

    Args:
        anomalias_df: DataFrame con columnas 'timestamp', 'value', 'tipo_anomalia',
                      'severidad', 'anomaly_score' (opcional)
        metodo_deteccion: Método usado para detectar (por defecto: 'motor_analitica')

    Returns:
        int: Número de anomalías guardadas
    """
    with app.app_context():
        nuevas = 0

        for _, row in anomalias_df.iterrows():
            # Verificar si ya existe
            existe = Anomaly.query.filter_by(
                timestamp=row['timestamp'],
                metodo_deteccion=metodo_deteccion
            ).first()

            if not existe:
                anomalia = Anomaly(
                    timestamp=row['timestamp'],
                    value=row['value'],
                    tipo_anomalia=row['tipo_anomalia'],
                    severidad=row['severidad'],
                    metodo_deteccion=metodo_deteccion,
                    score_anomalia=row.get('anomaly_score')
                )
                db.session.add(anomalia)
                nuevas += 1

        db.session.commit()
        print(f"   ✓ Guardadas {nuevas} anomalías nuevas")
        return nuevas


def guardar_metricas(nombre_modelo, metricas_dict, n_samples=None, metadata=None):
    """
    Guarda métricas del modelo en la tabla model_metrics.

    Args:
        nombre_modelo: Nombre del modelo (ej: 'prophet', 'random_forest')
        metricas_dict: Dict con métricas {'MAPE': 0.05, 'RMSE': 10.2, ...}
        n_samples: Número de muestras usadas para calcular métricas
        metadata: Dict con información adicional (se guarda como JSON)

    Returns:
        int: ID del registro guardado
    """
    with app.app_context():
        metrica = ModelMetric(
            nombre_modelo=nombre_modelo,
            mape=metricas_dict.get('MAPE'),
            smape=metricas_dict.get('SMAPE'),
            rmse=metricas_dict.get('RMSE'),
            mae=metricas_dict.get('MAE'),
            r2=metricas_dict.get('R2'),
            n_samples=n_samples if n_samples else 0,
            model_metadata=json.dumps(metadata) if metadata else None
        )

        db.session.add(metrica)
        db.session.commit()

        print(f"   ✓ Guardadas métricas del modelo '{nombre_modelo}' (ID: {metrica.id})")
        return metrica.id


# =============================================================================
# FUNCIONES DE LECTURA
# =============================================================================

def obtener_predicciones(modelo=None, desde=None, hasta=None, limit=100):
    """
    Obtiene predicciones de la tabla predictions.
    
    Args:
        modelo: Filtrar por modelo (opcional)
        desde: Fecha inicio (opcional)
        hasta: Fecha fin (opcional)
        limit: Límite de registros (por defecto: 100)
    
    Returns:
        list: Lista de diccionarios con las predicciones
    """
    with app.app_context():
        query = Prediction.query
        
        if modelo:
            query = query.filter(Prediction.modelo_usado == modelo)
        if desde:
            query = query.filter(Prediction.timestamp >= desde)
        if hasta:
            query = query.filter(Prediction.timestamp <= hasta)
        
        query = query.order_by(Prediction.timestamp.desc()).limit(limit)
        predicciones = query.all()
        
        return [
            {
                'id': p.id,
                'timestamp': p.timestamp,
                'prediccion': p.prediccion,
                'limite_inferior': p.limite_inferior,
                'limite_superior': p.limite_superior,
                'modelo_usado': p.modelo_usado,
                'fecha_generacion': p.fecha_generacion
            }
            for p in predicciones
        ]


def obtener_anomalias(desde=None, hasta=None, severidad=None, limit=100):
    """
    Obtiene anomalías de la tabla anomalies.
    
    Args:
        desde: Fecha inicio (opcional)
        hasta: Fecha fin (opcional)
        severidad: Filtrar por severidad (opcional)
        limit: Límite de registros (por defecto: 100)
    
    Returns:
        list: Lista de diccionarios con las anomalías
    """
    with app.app_context():
        query = Anomaly.query
        
        if desde:
            query = query.filter(Anomaly.timestamp >= desde)
        if hasta:
            query = query.filter(Anomaly.timestamp <= hasta)
        if severidad:
            query = query.filter(Anomaly.severidad == severidad)
        
        query = query.order_by(Anomaly.timestamp.desc()).limit(limit)
        anomalias = query.all()
        
        return [
            {
                'id': a.id,
                'timestamp': a.timestamp,
                'value': a.value,
                'tipo_anomalia': a.tipo_anomalia,
                'severidad': a.severidad,
                'metodo_deteccion': a.metodo_deteccion,
                'descripcion': a.descripcion,
                'fecha_deteccion': a.fecha_deteccion
            }
            for a in anomalias
        ]


def obtener_ultimas_metricas(modelo=None, limit=10):
    """
    Obtiene las últimas métricas guardadas.
    
    Args:
        modelo: Filtrar por modelo (opcional)
        limit: Límite de registros (por defecto: 10)
    
    Returns:
        list: Lista de diccionarios con las métricas
    """
    with app.app_context():
        query = ModelMetric.query
        
        if modelo:
            query = query.filter(ModelMetric.nombre_modelo == modelo)
        
        query = query.order_by(ModelMetric.timestamp.desc()).limit(limit)
        metricas = query.all()
        
        return [
            {
                'id': m.id,
                'nombre_modelo': m.nombre_modelo,
                'timestamp': m.timestamp,
                'mape': m.mape,
                'smape': m.smape,
                'rmse': m.rmse,
                'mae': m.mae,
                'r2': m.r2,
                'n_samples': m.n_samples,
                'metadata': json.loads(m.metadata_json) if m.metadata_json else None
            }
            for m in metricas
        ]


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def limpiar_predicciones_antiguas(dias=30):
    """
    Elimina predicciones más antiguas de X días.
    
    Args:
        dias: Número de días a mantener (por defecto: 30)
    
    Returns:
        int: Número de registros eliminados
    """
    with app.app_context():
        fecha_limite = datetime.now() - timedelta(days=dias)
        eliminadas = Prediction.query.filter(
            Prediction.fecha_generacion < fecha_limite
        ).delete()
        
        db.session.commit()
        print(f"   ✓ Eliminadas {eliminadas} predicciones antiguas")
        return eliminadas


def obtener_estadisticas():
    """
    Obtiene estadísticas generales de las tablas.
    
    Returns:
        dict: Diccionario con estadísticas
    """
    with app.app_context():
        total_predicciones = Prediction.query.count()
        total_anomalias = Anomaly.query.count()
        total_metricas = ModelMetric.query.count()
        
        return {
            'total_predicciones': total_predicciones,
            'total_anomalias': total_anomalias,
            'total_metricas': total_metricas,
            'modelos_unicos': db.session.query(Prediction.modelo_usado).distinct().count(),
            'ultima_prediccion': Prediction.query.order_by(
                Prediction.fecha_generacion.desc()
            ).first().fecha_generacion if total_predicciones > 0 else None
        }


if __name__ == "__main__":
    # Test de conexión
    print("\n" + "="*80)
    print("TEST DE MÓDULO DE PERSISTENCIA")
    print("="*80 + "\n")
    
    stats = obtener_estadisticas()
    print("Estadísticas de las tablas:")
    print(f"  - Predicciones: {stats['total_predicciones']}")
    print(f"  - Anomalías: {stats['total_anomalias']}")
    print(f"  - Métricas: {stats['total_metricas']}")
    print(f"  - Modelos únicos: {stats['modelos_unicos']}")
    print(f"  - Última predicción: {stats['ultima_prediccion']}")
    print("\n✓ Módulo funcionando correctamente\n")
