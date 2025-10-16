"""
Script para generar datos sint\u00e9ticos de prueba en la base de datos
"""

from models import db, EnergyData
from Config import Config
from flask import Flask
from datetime import datetime, timedelta
import numpy as np

# Configurar Flask y BD
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def generar_datos_sinteticos(num_dias=7):
    """Genera datos sint\u00e9ticos realistas para pruebas"""

    with app.app_context():
        print("="*80)
        print(f"GENERANDO DATOS SINTETICOS ({num_dias} DIAS)")
        print("="*80)

        # Comenzar desde hace num_dias
        inicio = datetime.now() - timedelta(days=num_dias)

        registros_generados = 0

        for dia in range(num_dias):
            for hora in range(24):
                timestamp = inicio + timedelta(days=dia, hours=hora)

                # Verificar si ya existe
                existe = EnergyData.query.filter_by(timestamp=timestamp).first()
                if existe:
                    continue

                # Generar precio realista con patron diario
                # Patron: m\u00e1s alto en horas pico (18-22h), m\u00e1s bajo en madrugada (2-6h)
                base = 200  # Precio base
                hora_del_dia = timestamp.hour

                # Variacion por hora del dia
                if 7 <= hora_del_dia <= 9:  # Pico manana
                    variacion_hora = np.random.uniform(30, 50)
                elif 18 <= hora_del_dia <= 22:  # Pico tarde
                    variacion_hora = np.random.uniform(40, 60)
                elif 2 <= hora_del_dia <= 6:  # Valle madrugada
                    variacion_hora = np.random.uniform(-60, -40)
                else:
                    variacion_hora = np.random.uniform(-20, 20)

                # Variacion aleatoria
                ruido = np.random.normal(0, 15)

                # Variacion por dia de la semana
                es_fin_semana = timestamp.weekday() >= 5
                if es_fin_semana:
                    variacion_semanal = -10
                else:
                    variacion_semanal = 5

                precio = base + variacion_hora + ruido + variacion_semanal

                # Generar demanda correlacionada con precio (mayor demanda = mayor precio)
                demanda_base = 85
                correlacion = (precio - 200) * 0.15  # 15% de correlacion
                demanda = demanda_base + correlacion + np.random.normal(0, 5)

                # Asegurar valores positivos
                precio = max(50, precio)
                demanda = max(30, demanda)

                # Crear registro
                record = EnergyData(
                    timestamp=timestamp,
                    precio=round(precio, 2),
                    demanda=round(demanda, 2)
                )
                db.session.add(record)
                registros_generados += 1

        # Guardar en BD
        try:
            db.session.commit()
            print(f"\n[OK] Se generaron {registros_generados} registros sinteticos")
            print(f"[OK] Rango: {inicio.strftime('%Y-%m-%d %H:%M')} a {(datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')}")

            # Mostrar estadisticas
            total = EnergyData.query.count()
            print(f"[OK] Total de registros en BD: {total}")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error al guardar datos: {e}")

        print("="*80)

if __name__ == "__main__":
    generar_datos_sinteticos(num_dias=7)
