"""
Demo completo del Motor de Analítica Avanzada
Usando datos de Azure SQL Database
"""
import sys
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from Config import Config
from motor_analitica import MotorAnalitica

print("="*80)
print("MOTOR DE ANALÍTICA AVANZADA - Demo con Azure SQL")
print("="*80)
print("Este script demostrará el sistema completo usando datos reales de Azure SQL\n")

# ==============================================================================
# PASO 1: Configurar conexión a Azure SQL
# ==============================================================================
print("[1/6] Configurando conexión a Azure SQL...")

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Definir modelo
class EnergyData(db.Model):
    __tablename__ = "energy_data"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, unique=True, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    demanda = db.Column(db.Float, nullable=True)
    potencia = db.Column(db.Float, nullable=True)
    generacion_total = db.Column(db.Float, nullable=True)
    renovables = db.Column(db.Float, nullable=True)
    co2 = db.Column(db.Float, nullable=True)

with app.app_context():
    db.create_all()
    print("   Conectado a Azure SQL Database")
    print(f"   Servidor: udcserver2025.database.windows.net\n")

# ==============================================================================
# PASO 2: Verificar/Obtener datos históricos
# ==============================================================================
print("[2/6] Verificando datos históricos en Azure SQL...")

with app.app_context():
    total_registros = EnergyData.query.count()
    
    if total_registros == 0:
        print("   No hay datos en la base de datos.")
        print("   Por favor, ejecuta 'python api.py' y luego accede a:")
        print("   http://localhost:5000/fetch_ree_data")
        print("   para sincronizar datos desde la API de REE\n")
        sys.exit(1)
    else:
        print(f"   Datos disponibles: {total_registros} registros históricos")
    
    # Obtener rango de fechas
    primer_dato = EnergyData.query.order_by(EnergyData.timestamp.asc()).first()
    ultimo_dato = EnergyData.query.order_by(EnergyData.timestamp.desc()).first()
    
    if primer_dato and ultimo_dato:
        print(f"   Período: {primer_dato.timestamp} a {ultimo_dato.timestamp}")
        dias = (ultimo_dato.timestamp - primer_dato.timestamp).days
        print(f"   Cobertura: {dias} días\n")

# ==============================================================================
# PASO 3: Cargar datos para análisis
# ==============================================================================
print("[3/6] Cargando datos para análisis...")

with app.app_context():
    # Obtener últimos 90 días (o todos si hay menos)
    fecha_inicio = datetime.utcnow() - timedelta(days=90)
    records = EnergyData.query.filter(
        EnergyData.timestamp >= fecha_inicio,
        EnergyData.demanda != None  # Solo registros con demanda
    ).order_by(EnergyData.timestamp).all()
    
    if len(records) < 100:
        print(f"   ADVERTENCIA: Solo hay {len(records)} registros con demanda. Se recomienda al menos 100.")
        print("   Usando todos los datos disponibles...")
        records = EnergyData.query.filter(
            EnergyData.demanda != None
        ).order_by(EnergyData.timestamp).all()
    
    if len(records) == 0:
        print("   ERROR: No hay registros con datos de demanda")
        sys.exit(1)
    
    # Convertir a DataFrame
    df_datos = pd.DataFrame([
        {"timestamp": r.timestamp, "value": r.demanda}
        for r in records
    ])
    
    print(f"   Datos cargados: {len(df_datos)} registros")
    print(f"   Rango de valores: {df_datos['value'].min():.2f} - {df_datos['value'].max():.2f} GWh")
    print(f"   Promedio: {df_datos['value'].mean():.2f} GWh\n")

# ==============================================================================
# PASO 4: Entrenar Modelo Prophet
# ==============================================================================
print("[4/6] Entrenando Modelo Prophet con datos de Azure SQL...")

try:
    # Crear y entrenar modelo
    motor = MotorAnalitica(tipo_modelo='prophet')
    resultado = motor.entrenar(df_datos)
    
    print("   Modelo entrenado exitosamente!")
    
    if 'metricas_test' in resultado:
        metricas = resultado['metricas_test']
        print(f"\n   Métricas del modelo:")
        print(f"   - MAPE:  {metricas.get('MAPE', 'N/A'):.2f}%")
        print(f"   - SMAPE: {metricas.get('SMAPE', 'N/A'):.2f}%")
        print(f"   - RMSE:  {metricas.get('RMSE', 'N/A'):.2f}")
        print(f"   - MAE:   {metricas.get('MAE', 'N/A'):.2f}")
        print(f"   - R²:    {metricas.get('R2', 'N/A'):.4f}")
    print()
    
except Exception as e:
    print(f"   ERROR al entrenar modelo: {e}\n")
    motor = None

# ==============================================================================
# PASO 5: Generar Predicciones
# ==============================================================================
print("[5/6] Generando predicciones para las próximas 24 horas...")

if motor and motor.entrenado:
    try:
        predicciones = motor.predecir(horizonte_horas=24)
        
        print(f"   Predicciones generadas: {len(predicciones)} horas")
        print(f"   Rango predicho: {predicciones['prediccion'].min():.2f} - {predicciones['prediccion'].max():.2f} GWh")
        print(f"   Promedio predicho: {predicciones['prediccion'].mean():.2f} GWh")
        
        # Mostrar primeras 5 predicciones
        print(f"\n   Primeras 5 predicciones:")
        for idx, row in predicciones.head(5).iterrows():
            ts = row['timestamp']
            pred = row['prediccion']
            lower = row.get('limite_inferior', pred)
            upper = row.get('limite_superior', pred)
            print(f"      {ts}: {pred:.2f} GWh (IC: {lower:.2f} - {upper:.2f})")
        print()
        
    except Exception as e:
        print(f"   ERROR generando predicciones: {e}\n")
        predicciones = None
else:
    print("   OMITIDO: No hay modelo entrenado\n")
    predicciones = None

# ==============================================================================
# PASO 6: Detectar Anomalías
# ==============================================================================
print("[6/6] Detectando anomalías en datos históricos...")

try:
    # Crear motor y analizar
    if not motor:
        motor = MotorAnalitica()
    
    anomalias = motor.detectar_anomalias(df_datos, metodos=['zscore', 'iqr', 'isolation_forest'])
    
    print(f"   Anomalías detectadas: {len(anomalias)}")
    
    if len(anomalias) > 0:
        # Por severidad
        severidades = anomalias['severidad'].value_counts()
        print(f"\n   Por severidad:")
        for sev, count in severidades.items():
            print(f"      - {sev}: {count}")
        
        # Por tipo
        tipos = anomalias['tipo_anomalia'].value_counts()
        print(f"\n   Por tipo:")
        for tipo, count in tipos.items():
            print(f"      - {tipo}: {count}")
        
        # Top 5 anomalías más recientes
        print(f"\n   Anomalías más recientes (últimas 5):")
        for idx, row in anomalias.tail(5).iterrows():
            ts = row['timestamp']
            val = row['value']
            tipo = row['tipo_anomalia']
            sev = row['severidad']
            print(f"      {ts}: {val:.2f} GWh - {tipo} ({sev})")
    else:
        print("   No se detectaron anomalías significativas")
    print()
    
except Exception as e:
    print(f"   ERROR detectando anomalías: {e}\n")
    anomalias = None

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
print("="*80)
print("RESUMEN DE LA EJECUCIÓN")
print("="*80)

print("\nComponentes ejecutados:")
print(f"   [OK] Conexión a Azure SQL Database")
print(f"   [{'OK' if total_registros > 0 else 'ERROR'}] Datos históricos ({total_registros} registros)")
print(f"   [{'OK' if motor else 'ERROR'}] Modelo de predicción (Prophet)")
print(f"   [{'OK' if predicciones is not None else 'SKIP'}] Predicciones generadas")
print(f"   [{'OK' if anomalias is not None else 'ERROR'}] Detección de anomalías")

print("\nEstadísticas:")
print(f"   - Registros en BD: {total_registros}")
print(f"   - Datos analizados: {len(df_datos)}")
if predicciones is not None:
    print(f"   - Predicciones generadas: {len(predicciones)}")
if anomalias is not None:
    print(f"   - Anomalías detectadas: {len(anomalias)}")

# Mostrar ruta del modelo si existe
if motor and motor.entrenado and hasattr(motor, 'ruta_modelo'):
    print(f"\nModelo guardado en: {motor.ruta_modelo}")

print("\n" + "="*80)
print("DEMO COMPLETADA")
print("="*80)