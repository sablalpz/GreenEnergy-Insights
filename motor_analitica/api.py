"""
=================================================================================
API REST - GreenEnergy Insights
=================================================================================

API Flask para el sistema de predicción y análisis de demanda eléctrica.
Proporciona endpoints para:
- Ingesta de datos desde API REE
- Consulta de datos históricos
- Gestión de anomalías
- Predicciones del modelo
- Métricas del modelo
"""

from flask import Flask, jsonify, request, render_template, Blueprint
from werkzeug.exceptions import HTTPException
import requests
import logging
import os
from common import Config, db, User, EnergyData, Anomaly, Prediction, ModelMetric
from datetime import datetime, timedelta
import json
from common import db_access

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

# Crear carpeta logs si no existe
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# INICIALIZACIÓN DE FLASK Y BASE DE DATOS
# =============================================================================

# Crear app usando la fábrica de common para garantizar inicialización común
from common.database import create_app

# Las plantillas y estáticos del dashboard están en la carpeta `templates` y `static`
# Exportable blueprint para que el backend principal pueda registrar estas rutas
# No especificamos `template_folder` aquí para que use las plantillas del app principal
motor_bp = Blueprint('motor_analitica', __name__, static_folder='static')

# Si el módulo se ejecuta directamente, create_app() registrará el blueprint y arrancará
app = None

# =============================================================================
# MANEJADORES DE ERRORES
# =============================================================================

@motor_bp.app_errorhandler(Exception)
def handle_exception(e):
    """Manejador global de errores"""
    if isinstance(e, HTTPException):
        return e

    logger.error(f"Error no manejado: {str(e)}", exc_info=True)
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e)
    }), 500

@motor_bp.app_errorhandler(404)
def not_found(e):
    """Manejador de error 404"""
    return jsonify({
        "error": "Not Found",
        "message": "El recurso solicitado no existe"
    }), 404

@motor_bp.app_errorhandler(400)
def bad_request(e):
    """Manejador de error 400"""
    return jsonify({
        "error": "Bad Request",
        "message": str(e)
    }), 400

# Ingesta de datos está gestionada por el servicio ETL independiente.
# La ruta /fetch_ree_data se ha eliminado para evitar duplicidad de responsabilidades.

# =============================================================================
# ENDPOINTS DE DATOS HISTÓRICOS
# =============================================================================

@motor_bp.route("/energy_data")
def get_energy_data():
    """
    Obtiene todos los datos históricos de energía usando db_access
    """
    try:
        registros = db_access.obtener_todos(EnergyData, db.session, order_by='timestamp')
        return jsonify(registros)
    except Exception as e:
        logger.error(f"Error al obtener datos de energía: {e}")
        return jsonify({"error": "Error al obtener datos"}), 500

@motor_bp.route("/api/energy_data/recent")
def get_recent_energy_data():
    """
    Obtiene datos históricos recientes (últimos N días)
    """
    days = request.args.get('days', 7, type=int)

    if days < 1 or days > 365:
        return jsonify({"error": "El parámetro 'days' debe estar entre 1 y 365"}), 400

    fecha_limite = datetime.utcnow() - timedelta(days=days)

    try:
        registros = db_access.obtener_registros_rango(EnergyData, db.session, 'timestamp', start=fecha_limite.isoformat(), order_by='timestamp', limit=10000, columns=['timestamp','demanda','precio'])
        return jsonify(registros)
    except Exception as e:
        logger.error(f"Error al obtener datos recientes: {e}")
        return jsonify({"error": "Error al obtener datos"}), 500

@motor_bp.route("/api/energy_data/stats")
def get_energy_stats():
    """
    Obtiene estadísticas generales de los datos históricos
    """
    try:
        stats = db_access.obtener_estadisticas_tabla(db.session, EnergyData, date_field='timestamp')
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =============================================================================
# ENDPOINTS DE ANOMALÍAS
# =============================================================================

@motor_bp.route("/api/anomalies")
def get_anomalies():
    """
    Obtiene anomalías con filtros opcionales
    """
    # Obtener parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    severidad = request.args.get('severidad')
    tipo = request.args.get('tipo')
    limit = request.args.get('limit', 100, type=int)

    # Validar limit
    if limit < 1 or limit > 1000:
        return jsonify({"error": "El parámetro 'limit' debe estar entre 1 y 1000"}), 400

    # Construir query base
    query = Anomaly.query

    # Aplicar filtros
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
            query = query.filter(Anomaly.timestamp >= fecha_inicio_dt)
        except ValueError:
            return jsonify({"error": "Formato de fecha_inicio inválido"}), 400

    if fecha_fin:
        try:
            fecha_fin_dt = datetime.fromisoformat(fecha_fin)
            query = query.filter(Anomaly.timestamp <= fecha_fin_dt)
        except ValueError:
            return jsonify({"error": "Formato de fecha_fin inválido"}), 400

    if severidad:
        query = query.filter(Anomaly.severidad == severidad)

    if tipo:
        query = query.filter(Anomaly.tipo_anomalia == tipo)

    try:
        # Ordenar y limitar
        registros = db_access.obtener_registros(Anomaly, db.session, filters=None, order_by='timestamp.desc()', limit=limit)
        return jsonify(registros)
    except Exception as e:
        logger.error(f"Error al obtener anomalías: {e}")
        return jsonify({"error": "Error al obtener anomalías"}), 500

@motor_bp.route("/api/anomalies/stats")
def get_anomaly_stats():
    """
    Obtiene estadísticas de anomalías
    """
    try:
        stats = db_access.obtener_agg_anomalias(db.session, Anomaly)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de anomalías: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =============================================================================
# ENDPOINTS DE PREDICCIONES
# =============================================================================

@motor_bp.route("/api/predictions/recent")
def get_recent_predictions():
    """
    Obtiene predicciones recientes
    """
    limit = request.args.get('limit', 50, type=int)

    if limit < 1 or limit > 1000:
        return jsonify({"error": "El parámetro 'limit' debe estar entre 1 y 1000"}), 400

    try:
        registros = db_access.obtener_registros(Prediction, db.session, order_by='timestamp.desc()', limit=limit)
        return jsonify(registros)
    except Exception as e:
        logger.error(f"Error al obtener predicciones: {e}")
        return jsonify({"error": "Error al obtener predicciones"}), 500

@motor_bp.route("/api/predictions/stats")
def get_predictions_stats():
    """
    Obtiene estadísticas de predicciones
    """
    try:
        total = db.session.query(db.func.count(Prediction.id)).scalar()
        if total == 0:
            return jsonify({
                "total_predictions": 0,
                "message": "No hay predicciones disponibles"
            })

        por_modelo = db.session.query(Prediction.modelo_usado, db.func.count(Prediction.id)).group_by(Prediction.modelo_usado).all()
        # usar fecha_generacion como fecha de creación
        ultima = db.session.query(Prediction).order_by(Prediction.fecha_generacion.desc()).first()

        return jsonify({
            "total_predictions": total,
            "by_model": dict(por_modelo),
            "last_prediction": getattr(ultima, 'fecha_generacion', None).isoformat() if ultima else None,
            "last_model_used": getattr(ultima, 'modelo_usado', None) if ultima else None
        })
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de predicciones: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =============================================================================
# ENDPOINTS DE MÉTRICAS DEL MODELO
# =============================================================================

@motor_bp.route("/api/metrics/latest")
def get_latest_metrics():
    """
    Obtiene las métricas más recientes del modelo
    """
    modelo = request.args.get('modelo')

    try:
        registros = db_access.obtener_registros(ModelMetric, db.session, order_by='timestamp.desc()', limit=1)
        if not registros:
            return jsonify({"message": "No hay métricas disponibles"}), 404
        return jsonify(registros[0])
    except Exception as e:
        logger.error(f"Error al obtener métricas: {e}")
        return jsonify({"error": "Error al obtener métricas"}), 500

@motor_bp.route("/api/metrics/history")
def get_metrics_history():
    """
    Obtiene el historial de métricas
    """
    modelo = request.args.get('modelo')
    limit = request.args.get('limit', 10, type=int)

    if limit < 1 or limit > 100:
        return jsonify({"error": "El parámetro 'limit' debe estar entre 1 y 100"}), 400

    try:
        query = ModelMetric.query.order_by(ModelMetric.timestamp.desc())

        if modelo:
            query = query.filter(ModelMetric.nombre_modelo == modelo)

        metrics = query.limit(limit).all()

        return jsonify([m.to_dict() for m in metrics])

    except Exception as e:
        logger.error(f"Error al obtener historial de métricas: {e}")
        return jsonify({"error": "Error al obtener historial"}), 500

# =============================================================================
# ENDPOINTS DE DASHBOARD
# =============================================================================

@motor_bp.route("/")
@motor_bp.route("/dashboard")
def dashboard():
    """
    Renderiza el dashboard principal unificado
    """
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error al renderizar dashboard: {e}")
        return jsonify({"error": "Error al cargar el dashboard"}), 500

# =============================================================================
# ENDPOINTS DE INFORMACIÓN Y SALUD
# =============================================================================

@motor_bp.route("/api/health")
def health_check():
    """
    Endpoint de health check para verificar el estado de la API
    """
    try:
        # Verificar conexión a BD
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        })
    except Exception as e:
        logger.error(f"Health check falló: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "disconnected",
            "error": str(e)
        }), 503

@motor_bp.route("/api/info")
def api_info():
    """
    Información general de la API
    """
    return jsonify({
        "name": "GreenEnergy Insights API",
        "version": "1.0.0",
        "description": "API REST para el sistema de predicción y análisis de demanda eléctrica",
        "endpoints": {
            "data": [
                "/energy_data",
                "/api/energy_data/recent",
                "/api/energy_data/stats"
            ],
            "anomalies": [
                "/api/anomalies",
                "/api/anomalies/stats"
            ],
            "predictions": [
                "/api/predictions/recent",
                "/api/predictions/stats"
            ],
            "metrics": [
                "/api/metrics/latest",
                "/api/metrics/history"
            ],
            "dashboard": [
                "/",
                "/dashboard"
            ],
            "health": [
                "/api/health",
                "/api/info"
            ]
        }
    })

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    # Crear la app usando la fábrica compartida y registrar el blueprint
    app = create_app(template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                     static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.register_blueprint(motor_bp)

    with app.app_context():
        db.create_all()
    logger.info("Tablas de base de datos creadas/verificadas")

    logger.info("Iniciando servidor Flask en puerto 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
