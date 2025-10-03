from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
from Config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Modelo de tabla
class EnergyData(db.Model):
    __tablename__ = "energy_data"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, unique=True, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    potencia = db.Column(db.Float, nullable=True)
    geo_id = db.Column(db.Integer, nullable=True)
    geo_name = db.Column(db.String(255), nullable=True)
    dia_semana = db.Column(db.Integer, nullable=True)
    hora_dia = db.Column(db.Integer, nullable=True)
    fin_de_semana = db.Column(db.Boolean, nullable=True)
    estacion = db.Column(db.String(50), nullable=True)
    demanda = db.Column(db.Float, nullable=True)
    generacion_total = db.Column(db.Float, nullable=True)
    renovables = db.Column(db.Float, nullable=True)
    co2 = db.Column(db.Float, nullable=True)

    
# Ruta para obtener datos de la API de REE y almacenarlos en la base de datos
@app.route("/fetch_ree_data")
def fetch_ree_data():
    url = "https://api.esios.ree.es/indicators/1001"
    headers = {"Authorization": f"Token {Config.REE_API_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "No se pudo obtener datos de REE"}), 500

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        return jsonify({"error": "La API de REE devolvió una respuesta no válida."}), 500

    new_records = 0  # FIX: inicializar contador

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
                print(f"Error al procesar registro: {e} en item: {item}")
                continue
    else:
        return jsonify({"error": "Estructura de datos de REE no reconocida."}), 500

    db.session.commit()
    return jsonify({"message": f"Proceso ETL completado. {new_records} nuevos datos guardados."}), 200


# Ruta para devolver datos al frontend
@app.route("/energy_data")
def get_energy_data():
    records = EnergyData.query.order_by(EnergyData.timestamp).all()
    return jsonify([
        {
            "timestamp": r.timestamp, 
            "precio": r.precio,
            "demanda": r.demanda,
            "renovables": r.renovables,
            "co2": r.co2
        } for r in records
    ])


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)  # debug=True activa autoreload

