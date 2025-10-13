"""
Script para verificar el motor de analítica
"""
import sys
import os

# Configurar encoding para Windows
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
sys.path.append('motor_analitica')
from motor_analitica.motor_analitica import MotorAnalitica, crear_dataframe_ejemplo

print("="*80)
print("VERIFICACIÓN DEL MOTOR DE ANALÍTICA")
print("="*80)

tests_passed = 0
tests_failed = 0

# Test 1: Crear datos de ejemplo
print("\n[1/5] Creando datos de ejemplo...")
try:
    df_ejemplo = crear_dataframe_ejemplo(num_registros=200)
    print(f"   ✓ DataFrame creado: {len(df_ejemplo)} registros")
    print(f"   ✓ Columnas: {', '.join(df_ejemplo.columns)}")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 2: Crear instancia del motor
print("\n[2/5] Creando instancia del motor...")
try:
    motor = MotorAnalitica(tipo_modelo='prophet')
    print(f"   ✓ Motor creado: tipo={motor.tipo_modelo}")
    print(f"   ✓ Estado: entrenado={motor.entrenado}")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 3: Entrenar modelo
print("\n[3/5] Entrenando modelo Prophet...")
try:
    resultado = motor.entrenar(df_ejemplo, test_size=0.2)
    print(f"   ✓ Modelo entrenado exitosamente")
    print(f"   ✓ Registros train: {resultado['registros_train']}")
    print(f"   ✓ Registros test: {resultado['registros_test']}")
    if 'metricas_test' in resultado:
        metricas = resultado['metricas_test']
        print(f"   ✓ MAPE: {metricas.get('MAPE', 'N/A'):.2f}%")
        print(f"   ✓ RMSE: {metricas.get('RMSE', 'N/A'):.2f}")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 4: Generar predicciones
print("\n[4/5] Generando predicciones...")
try:
    predicciones = motor.predecir(horizonte_horas=24)
    print(f"   ✓ Predicciones generadas: {len(predicciones)} horas")
    print(f"   ✓ Columnas: {', '.join(predicciones.columns)}")
    print(f"   ✓ Rango: {predicciones['prediccion'].min():.2f} - {predicciones['prediccion'].max():.2f}")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 5: Detectar anomalías
print("\n[5/5] Detectando anomalías...")
try:
    anomalias = motor.detectar_anomalias(df_ejemplo, metodos=['zscore', 'iqr'])
    print(f"   ✓ Anomalías detectadas: {len(anomalias)}")
    if len(anomalias) > 0:
        print(f"   ✓ Columnas: {', '.join(anomalias.columns)}")
        print(f"   ✓ Severidades: {anomalias['severidad'].unique()}")
    else:
        print(f"   ℹ No se detectaron anomalías (es normal con datos sintéticos)")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Resumen
print("\n" + "="*80)
print("RESUMEN DE VERIFICACIÓN")
print("="*80)
print(f"Tests pasados: {tests_passed}/5")
print(f"Tests fallidos: {tests_failed}/5")

if tests_failed == 0:
    print("\n✅ EL MOTOR DE ANALÍTICA FUNCIONA CORRECTAMENTE")
    sys.exit(0)
else:
    print(f"\n❌ {tests_failed} TESTS FALLARON - Revisar errores arriba")
    sys.exit(1)
