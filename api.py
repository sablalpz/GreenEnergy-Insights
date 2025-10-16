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

from flask import Flask, jsonify, request, render_template
from werkzeug.exceptions import HTTPException
import requests
import logging
import os
from Config import Config
from models import db, EnergyData, Anomaly, Prediction, ModelMetric
from datetime import datetime, timedelta
import json

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

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# Inicializar db con la app
db.init_app(app)

# =============================================================================
# MANEJADORES DE ERRORES
# =============================================================================

@app.errorhandler(Exception)
def handle_exception(e):
    """Manejador global de errores"""
    if isinstance(e, HTTPException):
        return e

    logger.error(f"Error no manejado: {str(e)}", exc_info=True)
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e)
    }), 500

@app.errorhandler(404)
def not_found(e):
    """Manejador de error 404"""
    return jsonify({
        "error": "Not Found",
        "message": "El recurso solicitado no existe"
    }), 404

@app.errorhandler(400)
def bad_request(e):
    """Manejador de error 400"""
    return jsonify({
        "error": "Bad Request",
        "message": str(e)
    }), 400

# =============================================================================
# ENDPOINTS DE INGESTA DE DATOS
# =============================================================================

@app.route("/fetch_ree_data")
def fetch_ree_data():
    """
    Obtiene datos de la API de REE y los almacena en la base de datos
    """
    logger.info("Iniciando fetch de datos desde API REE")

    url = "https://api.esios.ree.es/indicators/1001"
    headers = {"Authorization": f"Token {Config.REE_API_TOKEN}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con API REE: {e}")
        return jsonify({"error": "No se pudo conectar con la API de REE"}), 500

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        logger.error(f"Error al decodificar respuesta JSON: {e}")
        return jsonify({"error": "La API de REE devolvió una respuesta no válida."}), 500

    new_records = 0
    errors = 0

    if 'indicator' in data and 'values' in data['indicator']:
        for item in data['indicator']['values']:
            try:
                timestamp_dt = datetime.fromisoformat(item['datetime'].replace('Z', '+00:00'))
                precio = float(item['value'])

                exists = EnergyData.query.filter_by(timestamp=timestamp_dt).first()
                if not exists:
                    record = EnergyData(timestamp=timestamp_dt, precio=precio)
                    db.session.add(record)
                    new_records += 1
            except (KeyError, ValueError, AttributeError) as e:
                logger.warning(f"Error al procesar registro: {e} en item: {item}")
                errors += 1
                continue
    else:
        logger.error("Estructura de datos de REE no reconocida")
        return jsonify({"error": "Estructura de datos de REE no reconocida."}), 500

    try:
        db.session.commit()
        logger.info(f"ETL completado: {new_records} nuevos registros, {errors} errores")
        return jsonify({
            "message": f"Proceso ETL completado.",
            "new_records": new_records,
            "errors": errors
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al guardar en base de datos: {e}")
        return jsonify({"error": "Error al guardar datos en base de datos"}), 500

# =============================================================================
# ENDPOINTS DE DATOS HISTÓRICOS
# =============================================================================

@app.route("/energy_data")
def get_energy_data():
    """
    Obtiene todos los datos históricos de energía
    """
    try:
        records = EnergyData.query.order_by(EnergyData.timestamp).all()
        return jsonify([r.to_dict() for r in records])
    except Exception as e:
        logger.error(f"Error al obtener datos de energía: {e}")
        return jsonify({"error": "Error al obtener datos"}), 500

@app.route("/api/energy_data/recent")
def get_recent_energy_data():
    """
    Obtiene datos históricos recientes (últimos N días)
    """
    days = request.args.get('days', 7, type=int)

    if days < 1 or days > 365:
        return jsonify({"error": "El parámetro 'days' debe estar entre 1 y 365"}), 400

    fecha_limite = datetime.utcnow() - timedelta(days=days)

    try:
        records = EnergyData.query.filter(
            EnergyData.timestamp >= fecha_limite,
            EnergyData.demanda != None
        ).order_by(EnergyData.timestamp).all()

        return jsonify([{
            "timestamp": r.timestamp.isoformat(),
            "demanda": r.demanda,
            "precio": r.precio
        } for r in records])
    except Exception as e:
        logger.error(f"Error al obtener datos recientes: {e}")
        return jsonify({"error": "Error al obtener datos"}), 500

@app.route("/api/energy_data/stats")
def get_energy_stats():
    """
    Obtiene estadísticas generales de los datos históricos
    """
    try:
        total = EnergyData.query.count()

        if total == 0:
            return jsonify({
                "total_records": 0,
                "message": "No hay datos disponibles"
            })

        primer_registro = EnergyData.query.order_by(EnergyData.timestamp.asc()).first()
        ultimo_registro = EnergyData.query.order_by(EnergyData.timestamp.desc()).first()

        return jsonify({
            "total_records": total,
            "first_record": primer_registro.timestamp.isoformat(),
            "last_record": ultimo_registro.timestamp.isoformat(),
            "days_covered": (ultimo_registro.timestamp - primer_registro.timestamp).days
        })
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =============================================================================
# ENDPOINTS DE ANOMALÍAS
# =============================================================================

@app.route("/api/anomalies")
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
        anomalies = query.order_by(Anomaly.timestamp.desc()).limit(limit).all()
        return jsonify([a.to_dict() for a in anomalies])
    except Exception as e:
        logger.error(f"Error al obtener anomalías: {e}")
        return jsonify({"error": "Error al obtener anomalías"}), 500

@app.route("/api/anomalies/stats")
def get_anomaly_stats():
    """
    Obtiene estadísticas de anomalías
    """
    try:
        # Estadísticas generales
        total_anomalies = Anomaly.query.count()

        # Por severidad
        severidades = db.session.query(
            Anomaly.severidad,
            db.func.count(Anomaly.id)
        ).group_by(Anomaly.severidad).all()

        # Por tipo
        tipos = db.session.query(
            Anomaly.tipo_anomalia,
            db.func.count(Anomaly.id)
        ).group_by(Anomaly.tipo_anomalia).all()

        # Por día (últimos 7 días)
        fecha_limite = datetime.utcnow() - timedelta(days=7)
        por_dia = db.session.query(
            db.func.date(Anomaly.timestamp).label('fecha'),
            db.func.count(Anomaly.id).label('count')
        ).filter(Anomaly.timestamp >= fecha_limite).group_by(
            db.func.date(Anomaly.timestamp)
        ).order_by('fecha').all()

        # Anomalías críticas recientes (últimas 24 horas)
        fecha_24h = datetime.utcnow() - timedelta(hours=24)
        criticas_recientes = Anomaly.query.filter(
            Anomaly.severidad == 'critica',
            Anomaly.timestamp >= fecha_24h
        ).count()

        return jsonify({
            "total_anomalies": total_anomalies,
            "by_severity": dict(severidades),
            "by_type": dict(tipos),
            "by_day": [{"fecha": str(fecha), "count": count} for fecha, count in por_dia],
            "critical_last_24h": criticas_recientes,
            "last_update": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de anomalías: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =============================================================================
# ENDPOINTS DE PREDICCIONES
# =============================================================================

@app.route("/api/predictions/recent")
def get_recent_predictions():
    """
    Obtiene predicciones recientes
    """
    limit = request.args.get('limit', 50, type=int)

    if limit < 1 or limit > 1000:
        return jsonify({"error": "El parámetro 'limit' debe estar entre 1 y 1000"}), 400

    try:
        predictions = Prediction.query.order_by(
            Prediction.timestamp.desc()
        ).limit(limit).all()

        return jsonify([p.to_dict() for p in predictions])
    except Exception as e:
        logger.error(f"Error al obtener predicciones: {e}")
        return jsonify({"error": "Error al obtener predicciones"}), 500

@app.route("/api/predictions/stats")
def get_predictions_stats():
    """
    Obtiene estadísticas de predicciones
    """
    try:
        total = Prediction.query.count()

        if total == 0:
            return jsonify({
                "total_predictions": 0,
                "message": "No hay predicciones disponibles"
            })

        # Por modelo
        por_modelo = db.session.query(
            Prediction.modelo_usado,
            db.func.count(Prediction.id)
        ).group_by(Prediction.modelo_usado).all()

        # Última predicción
        ultima = Prediction.query.order_by(Prediction.created_at.desc()).first()

        return jsonify({
            "total_predictions": total,
            "by_model": dict(por_modelo),
            "last_prediction": ultima.created_at.isoformat() if ultima else None,
            "last_model_used": ultima.modelo_usado if ultima else None
        })
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de predicciones: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =============================================================================
# ENDPOINTS DE MÉTRICAS DEL MODELO
# =============================================================================

@app.route("/api/metrics/latest")
def get_latest_metrics():
    """
    Obtiene las métricas más recientes del modelo
    """
    modelo = request.args.get('modelo')

    try:
        query = ModelMetric.query.order_by(ModelMetric.created_at.desc())

        if modelo:
            query = query.filter(ModelMetric.nombre_modelo == modelo)

        metric = query.first()

        if not metric:
            return jsonify({"message": "No hay métricas disponibles"}), 404

        return jsonify(metric.to_dict())
    except Exception as e:
        logger.error(f"Error al obtener métricas: {e}")
        return jsonify({"error": "Error al obtener métricas"}), 500

@app.route("/api/metrics/history")
def get_metrics_history():
    """
    Obtiene el historial de métricas
    """
    modelo = request.args.get('modelo')
    limit = request.args.get('limit', 10, type=int)

    if limit < 1 or limit > 100:
        return jsonify({"error": "El parámetro 'limit' debe estar entre 1 y 100"}), 400

    try:
        query = ModelMetric.query.order_by(ModelMetric.created_at.desc())

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

@app.route("/")
@app.route("/dashboard")
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

@app.route("/api/health")
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

@app.route("/api/info")
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
                "/fetch_ree_data",
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
    with app.app_context():
        # Crear todas las tablas si no existen
        db.create_all()
        logger.info("Tablas de base de datos creadas/verificadas")

    logger.info("Iniciando servidor Flask en puerto 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
