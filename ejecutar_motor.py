"""
Script para ejecutar el motor de analítica y poblar la base de datos
con predicciones y anomalías.
"""

from motor_analitica.motor_analitica import MotorAnalitica
from models import db, EnergyData, Prediction, Anomaly, ModelMetric
from Config import Config
from flask import Flask
import pandas as pd
from datetime import datetime

# Configurar Flask y BD
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def ejecutar_motor():
    """Ejecuta el motor de analítica completo"""

    with app.app_context():
        print("="*80)
        print("EJECUTANDO MOTOR DE ANALÍTICA")
        print("="*80)

        # 1. Cargar datos desde la BD
        print("\n1. Cargando datos desde la base de datos...")
        energy_records = EnergyData.query.filter(EnergyData.demanda != None).order_by(EnergyData.timestamp).all()

        if len(energy_records) < 24:
            print(f"Error: Se necesitan al menos 24 registros. Solo hay {len(energy_records)}")
            print("Ejecuta primero: python generar_datos_sinteticos.py")
            return

        print(f"   [OK] Se cargaron {len(energy_records)} registros")

        # Convertir a DataFrame
        df = pd.DataFrame([{
            'timestamp': r.timestamp,
            'value': r.demanda
        } for r in energy_records])

        print(f"   [OK] Rango de datos: {df['timestamp'].min()} a {df['timestamp'].max()}")

        # 2. Crear y entrenar motor
        print("\n2. Entrenando modelo Prophet...")
        motor = MotorAnalitica(tipo_modelo='prophet', umbral_anomalia=3.0)

        try:
            info_entrenamiento = motor.entrenar(df, test_size=0.2)
            print(f"   [OK] Modelo entrenado exitosamente")
            print(f"   [OK] Registros train: {info_entrenamiento['registros_train']}")
            print(f"   [OK] Registros test: {info_entrenamiento['registros_test']}")
            print(f"   [OK] Metricas:")
            for metrica, valor in info_entrenamiento['metricas_test'].items():
                print(f"      - {metrica}: {valor:.4f}")
        except Exception as e:
            print(f"   [ERROR] Error al entrenar: {e}")
            return

        # 3. Generar predicciones
        print("\n3. Generando predicciones para las proximas 24 horas...")
        try:
            # Limpiar predicciones antiguas primero
            print("   [INFO] Limpiando predicciones antiguas...")
            Prediction.query.delete()
            db.session.commit()
            print("   [OK] Predicciones antiguas eliminadas")

            predicciones_df = motor.predecir(horizonte_horas=24)
            print(f"   [OK] Se generaron {len(predicciones_df)} predicciones")

            # Guardar predicciones en BD
            nuevas_predicciones = 0
            for _, row in predicciones_df.iterrows():
                pred = Prediction(
                    timestamp=row['timestamp'],
                    prediccion=float(row['prediccion']),
                    limite_inferior=float(row.get('limite_inferior', 0)),
                    limite_superior=float(row.get('limite_superior', 0)),
                    modelo_usado='prophet'
                )
                db.session.add(pred)
                nuevas_predicciones += 1

            db.session.commit()
            print(f"   [OK] {nuevas_predicciones} predicciones guardadas en BD")
        except Exception as e:
            print(f"   [ERROR] Error al generar predicciones: {e}")
            db.session.rollback()

        # 4. Detectar anomalias
        print("\n4. Detectando anomalias...")
        try:
            # Limpiar anomalías antiguas primero
            print("   [INFO] Limpiando anomalías antiguas...")
            Anomaly.query.delete()
            db.session.commit()
            print("   [OK] Anomalías antiguas eliminadas")

            anomalias_df = motor.detectar_anomalias(
                df,
                metodos=['zscore', 'iqr', 'isolation_forest', 'cambios_bruscos']
            )
            print(f"   [OK] Se detectaron {len(anomalias_df)} anomalias")

            if len(anomalias_df) > 0:
                # Debug: ver columnas disponibles
                print(f"   [DEBUG] Columnas disponibles: {anomalias_df.columns.tolist()}")

                # Guardar anomalias en BD
                nuevas_anomalias = 0
                for _, row in anomalias_df.iterrows():
                    # Verificar que todas las columnas necesarias existen
                    if 'timestamp' not in row.index or 'value' not in row.index:
                        continue

                    anomalia = Anomaly(
                        timestamp=row['timestamp'],
                        value=float(row['value']),
                        tipo_anomalia=row.get('tipo_anomalia', 'unknown'),
                        severidad=row.get('severidad', 'media'),
                        metodo_deteccion=row.get('metodo_deteccion', 'unknown'),
                        score_anomalia=float(row.get('anomaly_score', 0))
                    )
                    db.session.add(anomalia)
                    nuevas_anomalias += 1

                db.session.commit()
                print(f"   [OK] {nuevas_anomalias} anomalias guardadas en BD")

                # Mostrar resumen por severidad
                if 'severidad' in anomalias_df.columns:
                    print("\n   Resumen por severidad:")
                    severidades = anomalias_df['severidad'].value_counts()
                    for sev, count in severidades.items():
                        print(f"      - {sev}: {count}")
            else:
                print("   [INFO] No se detectaron anomalias")
        except Exception as e:
            print(f"   [ERROR] Error al detectar anomalias: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

        # 5. Guardar metricas del modelo
        print("\n5. Guardando metricas del modelo...")
        try:
            metricas = motor.obtener_metricas()

            model_metric = ModelMetric(
                nombre_modelo='prophet',
                mape=metricas['MAPE'],
                smape=metricas['SMAPE'],
                rmse=metricas['RMSE'],
                mae=metricas['MAE'],
                r2=metricas['R2'],
                n_samples=len(df)
            )
            db.session.add(model_metric)
            db.session.commit()
            print(f"   [OK] Metricas guardadas en BD")
        except Exception as e:
            print(f"   [ERROR] Error al guardar metricas: {e}")
            db.session.rollback()

        print("\n" + "="*80)
        print("MOTOR DE ANALITICA EJECUTADO EXITOSAMENTE")
        print("="*80)
        print("\nPuedes ver los resultados en: http://127.0.0.1:5000/dashboard")

if __name__ == "__main__":
    ejecutar_motor()
