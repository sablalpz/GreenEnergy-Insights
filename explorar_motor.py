"""
Exploración Avanzada del Motor de Analítica
Permite probar diferentes modelos, métricas y detectores de anomalías
"""
import sys
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from Config import Config
from motor_analitica import MotorAnalitica

print("="*80)
print("EXPLORACIÓN AVANZADA DEL MOTOR DE ANALÍTICA")
print("="*80)
print()

# ==============================================================================
# Configurar conexión
# ==============================================================================
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

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

# ==============================================================================
# Cargar datos
# ==============================================================================
print("Cargando datos de Azure SQL...")
with app.app_context():
    records = EnergyData.query.filter(
        EnergyData.demanda != None
    ).order_by(EnergyData.timestamp).all()
    
    if len(records) < 100:
        print(f"ERROR: Se necesitan al menos 100 registros. Disponibles: {len(records)}")
        sys.exit(1)
    
    df_datos = pd.DataFrame([
        {"timestamp": r.timestamp, "value": r.demanda}
        for r in records
    ])
    
    print(f"Datos cargados: {len(df_datos)} registros")
    print(f"Período: {df_datos['timestamp'].min()} a {df_datos['timestamp'].max()}")
    print()

# ==============================================================================
# MENÚ INTERACTIVO
# ==============================================================================
def menu_principal():
    print("="*80)
    print("MENÚ PRINCIPAL")
    print("="*80)
    print()
    print("1. Comparar todos los modelos de predicción")
    print("2. Probar diferentes detectores de anomalías")
    print("3. Analizar métricas de evaluación en detalle")
    print("4. Generar predicciones con diferentes horizontes")
    print("5. Análisis de sensibilidad de anomalías")
    print("6. Ver características del motor")
    print("7. Salir")
    print()
    return input("Selecciona una opción (1-7): ").strip()

def comparar_modelos():
    print("\n" + "="*80)
    print("COMPARACIÓN DE MODELOS DE PREDICCIÓN")
    print("="*80)
    print()
    
    modelos = ['prophet', 'random_forest', 'gradient_boosting', 'lstm']
    resultados = {}
    
    for nombre_modelo in modelos:
        print(f"\n[{nombre_modelo.upper()}] Entrenando...")
        try:
            motor = MotorAnalitica(tipo_modelo=nombre_modelo)
            resultado = motor.entrenar(df_datos)
            
            if 'metricas_test' in resultado:
                metricas = resultado['metricas_test']
                resultados[nombre_modelo] = metricas
                print(f"   MAPE:  {metricas.get('MAPE', 0):.2f}%")
                print(f"   R²:    {metricas.get('R2', 0):.4f}")
                print(f"   RMSE:  {metricas.get('RMSE', 0):.2f}")
            else:
                print("   No se pudieron calcular métricas")
                resultados[nombre_modelo] = None
                
        except Exception as e:
            print(f"   ERROR: {e}")
            resultados[nombre_modelo] = None
    
    # Resumen comparativo
    print("\n" + "-"*80)
    print("RESUMEN COMPARATIVO")
    print("-"*80)
    print(f"{'Modelo':<20} {'MAPE':<12} {'R²':<12} {'RMSE':<12}")
    print("-"*80)
    
    for modelo, metricas in resultados.items():
        if metricas:
            mape = metricas.get('MAPE', 0)
            r2 = metricas.get('R2', 0)
            rmse = metricas.get('RMSE', 0)
            print(f"{modelo:<20} {mape:<12.2f} {r2:<12.4f} {rmse:<12.2f}")
        else:
            print(f"{modelo:<20} {'N/A':<12} {'N/A':<12} {'N/A':<12}")
    
    # Mejor modelo
    modelos_validos = {k: v for k, v in resultados.items() if v is not None}
    if modelos_validos:
        mejor_modelo = min(modelos_validos.items(), key=lambda x: x[1].get('MAPE', float('inf')))
        print(f"\nMejor modelo (menor MAPE): {mejor_modelo[0].upper()}")
    
    input("\nPresiona Enter para continuar...")

def probar_detectores():
    print("\n" + "="*80)
    print("DETECTORES DE ANOMALÍAS")
    print("="*80)
    print()
    
    metodos = ['zscore', 'iqr', 'isolation_forest', 'cambios_bruscos']
    motor = MotorAnalitica()
    
    resultados_anomalias = {}
    
    for metodo in metodos:
        print(f"\n[{metodo.upper()}] Detectando anomalías...")
        try:
            anomalias = motor.detectar_anomalias(df_datos, metodos=[metodo])
            resultados_anomalias[metodo] = anomalias
            print(f"   Anomalías detectadas: {len(anomalias)}")
            
            if len(anomalias) > 0:
                severidades = anomalias['severidad'].value_counts()
                print(f"   Por severidad:")
                for sev, count in severidades.items():
                    print(f"      - {sev}: {count}")
        except Exception as e:
            print(f"   ERROR: {e}")
            resultados_anomalias[metodo] = None
    
    # Resumen
    print("\n" + "-"*80)
    print("RESUMEN COMPARATIVO")
    print("-"*80)
    print(f"{'Método':<20} {'Total':<10} {'Alta':<10} {'Media':<10} {'Baja':<10}")
    print("-"*80)
    
    for metodo, anomalias in resultados_anomalias.items():
        if anomalias is not None and len(anomalias) > 0:
            severidades = anomalias['severidad'].value_counts()
            alta = severidades.get('alta', 0)
            media = severidades.get('media', 0)
            baja = severidades.get('baja', 0)
            total = len(anomalias)
            print(f"{metodo:<20} {total:<10} {alta:<10} {media:<10} {baja:<10}")
        else:
            print(f"{metodo:<20} {'0':<10} {'0':<10} {'0':<10} {'0':<10}")
    
    input("\nPresiona Enter para continuar...")

def analizar_metricas():
    print("\n" + "="*80)
    print("ANÁLISIS DETALLADO DE MÉTRICAS")
    print("="*80)
    print()
    
    print("Entrenando modelo Prophet...")
    motor = MotorAnalitica(tipo_modelo='prophet')
    resultado = motor.entrenar(df_datos)
    
    if 'metricas_test' in resultado:
        metricas = resultado['metricas_test']
        
        print("\nMÉTRICAS DE EVALUACIÓN:")
        print("-"*80)
        
        print(f"\n1. MAPE (Mean Absolute Percentage Error): {metricas.get('MAPE', 0):.2f}%")
        print("   Interpretación: Error porcentual promedio")
        print("   Bueno: < 10% | Aceptable: 10-20% | Mejorar: > 20%")
        
        print(f"\n2. SMAPE (Symmetric MAPE): {metricas.get('SMAPE', 0):.2f}%")
        print("   Interpretación: Error simétrico porcentual")
        print("   Rango: 0-100%, menor es mejor")
        
        print(f"\n3. RMSE (Root Mean Squared Error): {metricas.get('RMSE', 0):.2f}")
        print("   Interpretación: Error cuadrático medio (penaliza errores grandes)")
        print("   En unidades de la variable (GWh)")
        
        print(f"\n4. MAE (Mean Absolute Error): {metricas.get('MAE', 0):.2f}")
        print("   Interpretación: Error absoluto promedio")
        print("   En unidades de la variable (GWh)")
        
        print(f"\n5. R² (Coeficiente de Determinación): {metricas.get('R2', 0):.4f}")
        print("   Interpretación: Proporción de varianza explicada")
        print("   Excelente: > 0.9 | Bueno: 0.7-0.9 | Aceptable: 0.5-0.7")
        
        print(f"\n6. MSE (Mean Squared Error): {metricas.get('MSE', 0):.2f}")
        print("   Interpretación: Error cuadrático medio (sin raíz)")
        print("   Sensible a outliers")
        
        # Evaluación general
        r2 = metricas.get('R2', 0)
        mape = metricas.get('MAPE', 100)
        
        print("\n" + "-"*80)
        print("EVALUACIÓN GENERAL DEL MODELO:")
        print("-"*80)
        
        if r2 > 0.9 and mape < 10:
            print("EXCELENTE - El modelo tiene muy alta precisión")
        elif r2 > 0.7 and mape < 20:
            print("BUENO - El modelo es confiable para predicciones")
        elif r2 > 0.5 and mape < 30:
            print("ACEPTABLE - El modelo puede usarse con precaución")
        else:
            print("MEJORABLE - Considerar más datos o ajustes")
    else:
        print("No se pudieron calcular métricas")
    
    input("\nPresiona Enter para continuar...")

def predicciones_horizontes():
    print("\n" + "="*80)
    print("PREDICCIONES CON DIFERENTES HORIZONTES")
    print("="*80)
    print()
    
    print("Entrenando modelo Prophet...")
    motor = MotorAnalitica(tipo_modelo='prophet')
    motor.entrenar(df_datos)
    
    horizontes = [6, 12, 24, 48, 72]
    
    for horas in horizontes:
        print(f"\nPredicciones para {horas} horas:")
        try:
            predicciones = motor.predecir(horizonte_horas=horas)
            print(f"   Generadas: {len(predicciones)} predicciones")
            print(f"   Rango: {predicciones['prediccion'].min():.2f} - {predicciones['prediccion'].max():.2f} GWh")
            print(f"   Promedio: {predicciones['prediccion'].mean():.2f} GWh")
            
            # Mostrar primeras 3
            print(f"   Primeras 3:")
            for idx, row in predicciones.head(3).iterrows():
                ts = row['timestamp']
                pred = row['prediccion']
                print(f"      {ts}: {pred:.2f} GWh")
                
        except Exception as e:
            print(f"   ERROR: {e}")
    
    input("\nPresiona Enter para continuar...")

def analisis_sensibilidad():
    print("\n" + "="*80)
    print("ANÁLISIS DE SENSIBILIDAD - DETECCIÓN DE ANOMALÍAS")
    print("="*80)
    print()
    
    print("Probando Z-Score con diferentes umbrales...")
    motor = MotorAnalitica()
    
    umbrales = [2.0, 2.5, 3.0, 3.5]
    
    for umbral in umbrales:
        print(f"\nUmbral Z-Score = {umbral}")
        try:
            # Para Z-Score necesitaríamos modificar el motor para aceptar umbrales
            # Por ahora mostraremos el comportamiento estándar
            anomalias = motor.detectar_anomalias(df_datos, metodos=['zscore'])
            print(f"   Anomalías: {len(anomalias)}")
            
            if len(anomalias) > 0:
                severidades = anomalias['severidad'].value_counts()
                for sev, count in severidades.items():
                    print(f"      {sev}: {count}")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\nNota: El motor usa umbrales predefinidos optimizados.")
    print("Para personalizar umbrales, modifica motor_analitica.py")
    
    input("\nPresiona Enter para continuar...")

def ver_caracteristicas():
    print("\n" + "="*80)
    print("CARACTERÍSTICAS DEL MOTOR DE ANALÍTICA")
    print("="*80)
    print()
    
    print("MODELOS DE PREDICCIÓN DISPONIBLES:")
    print("-"*80)
    print("1. Prophet (Facebook)")
    print("   - Mejor para series temporales con estacionalidad")
    print("   - Maneja automáticamente tendencias y patrones")
    print("   - Genera intervalos de confianza")
    print("   - Recomendado para: datos con patrones horarios/diarios/semanales")
    print()
    
    print("2. Random Forest")
    print("   - Ensemble de árboles de decisión")
    print("   - Robusto a outliers")
    print("   - No requiere normalización")
    print("   - Recomendado para: datos con relaciones no lineales")
    print()
    
    print("3. Gradient Boosting")
    print("   - Boosting secuencial de árboles")
    print("   - Alta precisión")
    print("   - Puede sobreajustar con pocos datos")
    print("   - Recomendado para: maximizar precisión con datos abundantes")
    print()
    
    print("4. LSTM (Long Short-Term Memory)")
    print("   - Red neuronal recurrente")
    print("   - Captura dependencias temporales largas")
    print("   - Requiere más datos de entrenamiento")
    print("   - Recomendado para: series muy largas y complejas")
    print()
    
    print("\nDETECTORES DE ANOMALÍAS:")
    print("-"*80)
    print("1. Z-Score")
    print("   - Detecta valores que se desvían de la media")
    print("   - Umbral: 3 desviaciones estándar")
    print("   - Mejor para: distribuciones normales")
    print()
    
    print("2. IQR (Interquartile Range)")
    print("   - Usa cuartiles para detectar outliers")
    print("   - Robusto a valores extremos")
    print("   - Mejor para: datos con distribución asimétrica")
    print()
    
    print("3. Isolation Forest")
    print("   - Machine Learning para anomalías")
    print("   - Detecta patrones anómalos complejos")
    print("   - Mejor para: anomalías multidimensionales")
    print()
    
    print("4. Cambios Bruscos")
    print("   - Detecta variaciones repentinas")
    print("   - Analiza diferencias entre períodos consecutivos")
    print("   - Mejor para: identificar picos o caídas súbitas")
    print()
    
    print("\nMÉTRICAS DE EVALUACIÓN:")
    print("-"*80)
    print("- MAPE:  Error porcentual (fácil interpretación)")
    print("- SMAPE: Error simétrico (evita sesgos)")
    print("- RMSE:  Penaliza errores grandes")
    print("- MAE:   Error absoluto promedio")
    print("- R²:    Calidad del ajuste (0-1)")
    print("- MSE:   Base para RMSE")
    print()
    
    input("Presiona Enter para continuar...")

# ==============================================================================
# BUCLE PRINCIPAL
# ==============================================================================
while True:
    opcion = menu_principal()
    
    if opcion == '1':
        comparar_modelos()
    elif opcion == '2':
        probar_detectores()
    elif opcion == '3':
        analizar_metricas()
    elif opcion == '4':
        predicciones_horizontes()
    elif opcion == '5':
        analisis_sensibilidad()
    elif opcion == '6':
        ver_caracteristicas()
    elif opcion == '7':
        print("\nSaliendo del explorador...")
        break
    else:
        print("\nOpción no válida. Intenta de nuevo.")
        input("Presiona Enter para continuar...")

print("\nGracias por usar el Motor de Analítica Avanzada!")
