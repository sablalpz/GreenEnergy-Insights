"""
Script para verificar que los modelos son compatibles con el esquema SQL
"""
import sys
import os

# Configurar encoding para Windows
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from models import EnergyData, Anomaly, Prediction, ModelMetric

print("="*80)
print("VERIFICACIÓN DE COMPATIBILIDAD DE MODELOS SQL")
print("="*80)

tests_passed = 0
tests_failed = 0

# Test 1: Verificar columnas de EnergyData
print("\n[1/4] Verificando modelo EnergyData...")
try:
    required_columns = ['id', 'timestamp', 'precio', 'demanda', 'geo_id',
                       'dia_semana', 'hora_dia', 'fin_de_semana', 'estacion']
    model_columns = [col.name for col in EnergyData.__table__.columns]

    missing = [col for col in required_columns if col not in model_columns]

    if missing:
        print(f"   ✗ Columnas faltantes: {', '.join(missing)}")
        tests_failed += 1
    else:
        print(f"   ✓ Todas las columnas requeridas presentes: {len(required_columns)}")
        print(f"   ✓ Tabla: {EnergyData.__tablename__}")
        tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 2: Verificar columnas de Anomaly
print("\n[2/4] Verificando modelo Anomaly...")
try:
    required_columns = ['id', 'timestamp', 'value', 'tipo_anomalia',
                       'severidad', 'metodo_deteccion', 'score_anomalia', 'created_at']
    model_columns = [col.name for col in Anomaly.__table__.columns]

    missing = [col for col in required_columns if col not in model_columns]

    if missing:
        print(f"   ✗ Columnas faltantes: {', '.join(missing)}")
        tests_failed += 1
    else:
        print(f"   ✓ Todas las columnas requeridas presentes: {len(required_columns)}")
        print(f"   ✓ Tabla: {Anomaly.__tablename__}")
        tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 3: Verificar columnas de Prediction
print("\n[3/4] Verificando modelo Prediction...")
try:
    required_columns = ['id', 'timestamp', 'prediccion', 'limite_inferior',
                       'limite_superior', 'modelo_usado', 'created_at']
    model_columns = [col.name for col in Prediction.__table__.columns]

    missing = [col for col in required_columns if col not in model_columns]

    if missing:
        print(f"   ✗ Columnas faltantes: {', '.join(missing)}")
        tests_failed += 1
    else:
        print(f"   ✓ Todas las columnas requeridas presentes: {len(required_columns)}")
        print(f"   ✓ Tabla: {Prediction.__tablename__}")
        tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Test 4: Verificar columnas de ModelMetric
print("\n[4/4] Verificando modelo ModelMetric...")
try:
    required_columns = ['id', 'nombre_modelo', 'mape', 'smape', 'rmse',
                       'mae', 'r2', 'n_samples', 'model_metadata', 'created_at']
    model_columns = [col.name for col in ModelMetric.__table__.columns]

    missing = [col for col in required_columns if col not in model_columns]

    if missing:
        print(f"   ✗ Columnas faltantes: {', '.join(missing)}")
        tests_failed += 1
    else:
        print(f"   ✓ Todas las columnas requeridas presentes: {len(required_columns)}")
        print(f"   ✓ Tabla: {ModelMetric.__tablename__}")
        tests_passed += 1
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    tests_failed += 1

# Resumen
print("\n" + "="*80)
print("RESUMEN DE VERIFICACIÓN")
print("="*80)
print(f"Tests pasados: {tests_passed}/4")
print(f"Tests fallidos: {tests_failed}/4")

if tests_failed == 0:
    print("\n✅ TODOS LOS MODELOS SON COMPATIBLES CON EL ESQUEMA SQL")
    sys.exit(0)
else:
    print(f"\n❌ {tests_failed} TESTS FALLARON - Revisar errores arriba")
    sys.exit(1)
