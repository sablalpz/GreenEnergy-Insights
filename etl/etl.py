from flask import jsonify
import requests
from datetime import datetime
from common import db, create_app, EnergyData, Config
from common.db_access import guardar_registro


app = create_app()  # Usa la configuración compartida

# Ruta API para recolectar datos enriquecidos
@app.route("/fetch_ree_data")
def fetch_ree_data():
    # Indicadores de REE que vamos a consultar
    indicadores = {
        "precio": 1001,            # Precio PVPC
        "demanda": 600,            # Demanda real      
    }

    headers = {"Authorization": f"Token {Config.REE_API_TOKEN}"}
    datos_por_indicador = {}

    # Pedimos todos los indicadores y guardamos sus valores por timestamp
    for nombre, indicador_id in indicadores.items():
        url = f"https://api.esios.ree.es/indicators/{indicador_id}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Error: no se pudo obtener {nombre} de REE")
            continue

        try:
            data = response.json()
            if "indicator" in data and "values" in data["indicator"]:
                datos_por_indicador[nombre] = {
                    datetime.fromisoformat(item["datetime"].replace("Z", "+00:00")): item["value"]
                    for item in data["indicator"]["values"]
                }
        except Exception as e:
            print(f"Error procesando {nombre}: {e}")

    new_records = 0

    # Usamos el precio como "base" de timestamps
    if "precio" not in datos_por_indicador:
        return jsonify({"error": "No se pudo obtener datos de precio"}), 500

    for timestamp, precio in datos_por_indicador["precio"].items():
        try:
            demanda = datos_por_indicador.get("demanda", {}).get(timestamp)

            # Features temporales
            dia_semana = timestamp.weekday()
            hora_dia = timestamp.hour
            fin_de_semana = dia_semana >= 5
            month = timestamp.month
            season = (
                "winter" if month in [12, 1, 2] else
                "spring" if month in [3, 4, 5] else
                "summer" if month in [6, 7, 8] else
                "autumn"
            )

            # Evitar duplicados (único por timestamp)
            exists = EnergyData.query.filter_by(timestamp=timestamp).first()
            if not exists:
                guardar_registro(
                    EnergyData,
                    db.session,
                    timestamp=timestamp,
                    precio=precio,
                    demanda=demanda,
                    dia_semana=dia_semana,
                    hora_dia=hora_dia,
                    fin_de_semana=fin_de_semana,
                    estacion=season
                )
                new_records += 1

        except Exception as e:
            print(f"Error al procesar registro en {timestamp}: {e}")
            continue

    db.session.commit()
    return jsonify({"message": f"Proceso ETL completado. {new_records} nuevos datos guardados."})


# Endpoint para consultar datos
@app.route("/energy_data")
def get_energy_data():
    records = EnergyData.query.order_by(EnergyData.timestamp).all()
    return jsonify([
        {
            "timestamp": r.timestamp.isoformat(),
            "precio": r.precio,
            "geo_id": r.geo_id,
            "dia_semana": r.dia_semana,
            "hora_dia": r.hora_dia,
            "fin_de_semana": r.fin_de_semana,
            "estacion": r.estacion,
            "demanda":r.demanda
        }
        for r in records
    ])

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Cargando datos iniciales...")
        try:
            fetch_ree_data()  # Ejecutar la carga al inicio
        except Exception as e:
            print(f"Error al cargar datos automáticamente: {e}")
    app.run(host="0.0.0.0", port=5002, debug=True)
