"""
Script de prueba para verificar todas las importaciones
"""
import sys
import os

# Configurar encoding para Windows
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("="*80)
print("VERIFICACIÓN DE IMPORTACIONES")
print("="*80)

tests_passed = 0
tests_failed = 0

# Test 1: Importar models.py
print("\n[1/5] Probando importación de models.py...")
try:
    from models import db, EnergyData, Anomaly, Prediction, ModelMetric
    print("   ✓ models.py importado correctamente")
    print(f"   ✓ Modelos encontrados: EnergyData, Anomaly, Prediction, ModelMetric")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 2: Importar Config
print("\n[2/5] Probando importación de Config.py...")
try:
    from Config import Config
    print("   ✓ Config.py importado correctamente")
    print(f"   ✓ Token REE: {'***' + Config.REE_API_TOKEN[-10:] if hasattr(Config, 'REE_API_TOKEN') else 'NO ENCONTRADO'}")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 3: Importar motor_analitica
print("\n[3/5] Probando importación de motor_analitica...")
try:
    sys.path.append('motor_analitica')
    from motor_analitica.motor_analitica import MotorAnalitica, TipoModelo, TipoAnomalia
    print("   ✓ motor_analitica.py importado correctamente")
    print(f"   ✓ Clases encontradas: MotorAnalitica, TipoModelo, TipoAnomalia")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 4: Importar persistencia
print("\n[4/5] Probando importación de persistencia...")
try:
    from motor_analitica.persistencia import guardar_predicciones, guardar_anomalias, guardar_metricas
    print("   ✓ persistencia.py importado correctamente")
    print(f"   ✓ Funciones encontradas: guardar_predicciones, guardar_anomalias, guardar_metricas")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 5: Verificar dependencias clave
print("\n[5/5] Probando dependencias clave...")
try:
    import flask
    import pandas
    import numpy
    import sklearn
    import prophet
    print("   ✓ Flask instalado")
    print("   ✓ Pandas instalado")
    print("   ✓ NumPy instalado")
    print("   ✓ Scikit-learn instalado")
    print("   ✓ Prophet instalado")
    tests_passed += 1
except ImportError as e:
    print(f"   ✗ ERROR: Falta instalar: {e}")
    tests_failed += 1

# Resumen
print("\n" + "="*80)
print("RESUMEN DE VERIFICACIÓN")
print("="*80)
print(f"Tests pasados: {tests_passed}/5")
print(f"Tests fallidos: {tests_failed}/5")

if tests_failed == 0:
    print("\n✅ TODAS LAS IMPORTACIONES FUNCIONAN CORRECTAMENTE")
    sys.exit(0)
else:
    print(f"\n❌ {tests_failed} TESTS FALLARON - Revisar errores arriba")
    sys.exit(1)
