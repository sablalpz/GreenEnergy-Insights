"""
Generador de Gráficos Comparativos
Visualiza predicciones, datos reales y anomalías detectadas
"""
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from common import EnergyData, create_app,Config
from motor_analitica import MotorAnalitica

# Configurar estilo de gráficos
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (15, 8)
plt.rcParams['font.size'] = 10

print("="*80)
print("GENERADOR DE GRÁFICOS COMPARATIVOS")
print("="*80)
print()

# ==============================================================================
# Configurar conexión
# ==============================================================================
app = create_app()

# ==============================================================================
# Cargar datos
# ==============================================================================
print("[1/5] Cargando datos de Azure SQL...")
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
    
    print(f"   Datos cargados: {len(df_datos)} registros")
    print()

# ==============================================================================
# Entrenar modelo
# ==============================================================================
print("[2/5] Entrenando modelo Prophet...")
motor = MotorAnalitica(tipo_modelo='prophet')
resultado = motor.entrenar(df_datos)

if 'metricas_test' in resultado:
    metricas = resultado['metricas_test']
    print(f"   MAPE: {metricas.get('MAPE', 0):.2f}%")
    print(f"   R²: {metricas.get('R2', 0):.4f}")
print()

# ==============================================================================
# Generar predicciones
# ==============================================================================
print("[3/5] Generando predicciones...")
predicciones = motor.predecir(horizonte_horas=48)
print(f"   Predicciones: {len(predicciones)} horas")
print()

# ==============================================================================
# Detectar anomalías
# ==============================================================================
print("[4/5] Detectando anomalías...")
anomalias = motor.detectar_anomalias(df_datos, metodos=['zscore', 'iqr', 'isolation_forest'])
print(f"   Anomalías detectadas: {len(anomalias)}")
print()

# ==============================================================================
# Generar gráficos
# ==============================================================================
print("[5/5] Generando gráficos...")

# Crear carpeta para gráficos
os.makedirs('graficos', exist_ok=True)

# ---------------------------------------------------------------------------
# GRÁFICO 1: Predicciones vs Datos Históricos
# ---------------------------------------------------------------------------
print("   [1/5] Predicciones vs Datos Históricos...")

fig, ax = plt.subplots(figsize=(16, 8))

# Últimas 72 horas de datos históricos
df_historico_plot = df_datos.tail(72)

# Datos históricos
ax.plot(df_historico_plot['timestamp'], df_historico_plot['value'], 
        'o-', label='Datos Históricos', color='#2E86AB', linewidth=2, markersize=4)

# Predicciones
ax.plot(predicciones['timestamp'], predicciones['prediccion'], 
        's--', label='Predicciones', color='#A23B72', linewidth=2, markersize=5)

# Intervalos de confianza (si existen)
if 'limite_inferior' in predicciones.columns and 'limite_superior' in predicciones.columns:
    ax.fill_between(predicciones['timestamp'], 
                    predicciones['limite_inferior'], 
                    predicciones['limite_superior'],
                    alpha=0.2, color='#A23B72', label='Intervalo de Confianza')

ax.set_xlabel('Fecha y Hora', fontsize=12, fontweight='bold')
ax.set_ylabel('Demanda Energética (GWh)', fontsize=12, fontweight='bold')
ax.set_title('Predicción de Demanda Energética - Prophet', fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=11)
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('graficos/01_predicciones_vs_historico.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------------------------------------------------------------------------
# GRÁFICO 2: Anomalías Detectadas
# ---------------------------------------------------------------------------
print("   [2/5] Anomalías Detectadas...")

fig, ax = plt.subplots(figsize=(16, 8))

# Todos los datos históricos
ax.plot(df_datos['timestamp'], df_datos['value'], 
        '-', label='Datos Históricos', color='#2E86AB', linewidth=1.5, alpha=0.7)

# Marcar anomalías por severidad
if len(anomalias) > 0:
    # Merge anomalías con datos
    df_con_anomalias = df_datos.copy()
    df_con_anomalias['es_anomalia'] = False
    df_con_anomalias['severidad'] = None
    
    for idx, anomalia in anomalias.iterrows():
        mask = df_con_anomalias['timestamp'] == anomalia['timestamp']
        df_con_anomalias.loc[mask, 'es_anomalia'] = True
        df_con_anomalias.loc[mask, 'severidad'] = anomalia['severidad']
    
    # Plotear anomalías por severidad
    colores_severidad = {
        'critica': '#D32F2F',
        'alta': '#F57C00',
        'media': '#FBC02D',
        'baja': '#388E3C'
    }
    
    for severidad, color in colores_severidad.items():
        anomalias_sev = df_con_anomalias[
            (df_con_anomalias['es_anomalia']) & 
            (df_con_anomalias['severidad'] == severidad)
        ]
        if len(anomalias_sev) > 0:
            ax.scatter(anomalias_sev['timestamp'], anomalias_sev['value'],
                      color=color, s=100, marker='X', 
                      label=f'Anomalía {severidad.capitalize()}', zorder=5)

ax.set_xlabel('Fecha y Hora', fontsize=12, fontweight='bold')
ax.set_ylabel('Demanda Energética (GWh)', fontsize=12, fontweight='bold')
ax.set_title('Detección de Anomalías en Demanda Energética', fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=11)
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('graficos/02_anomalias_detectadas.png', dpi=300, bbox_inches='tight')
plt.close()

# ---------------------------------------------------------------------------
# GRÁFICO 3: Comparación de Modelos
# ---------------------------------------------------------------------------
print("   [3/5] Comparación de Modelos...")

modelos = ['prophet', 'random_forest', 'gradient_boosting', 'lstm']
resultados_modelos = {}

for nombre_modelo in modelos:
    try:
        motor_temp = MotorAnalitica(tipo_modelo=nombre_modelo)
        resultado = motor_temp.entrenar(df_datos)
        if 'metricas_test' in resultado:
            resultados_modelos[nombre_modelo] = resultado['metricas_test']
    except:
        pass

if resultados_modelos:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Comparación de Modelos de Predicción', fontsize=16, fontweight='bold')
    
    # MAPE
    ax = axes[0, 0]
    nombres = [m.replace('_', ' ').title() for m in resultados_modelos.keys()]
    valores = [m.get('MAPE', 0) for m in resultados_modelos.values()]
    bars = ax.bar(nombres, valores, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
    ax.set_ylabel('MAPE (%)', fontweight='bold')
    ax.set_title('Error Porcentual Medio Absoluto', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{valores[i]:.2f}%', ha='center', va='bottom', fontweight='bold')
    
    # R²
    ax = axes[0, 1]
    valores = [m.get('R2', 0) for m in resultados_modelos.values()]
    bars = ax.bar(nombres, valores, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
    ax.set_ylabel('R² Score', fontweight='bold')
    ax.set_title('Coeficiente de Determinación', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 1)
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{valores[i]:.4f}', ha='center', va='bottom', fontweight='bold')
    
    # RMSE
    ax = axes[1, 0]
    valores = [m.get('RMSE', 0) for m in resultados_modelos.values()]
    bars = ax.bar(nombres, valores, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
    ax.set_ylabel('RMSE', fontweight='bold')
    ax.set_title('Raíz del Error Cuadrático Medio', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{valores[i]:.2f}', ha='center', va='bottom', fontweight='bold')
    
    # MAE
    ax = axes[1, 1]
    valores = [m.get('MAE', 0) for m in resultados_modelos.values()]
    bars = ax.bar(nombres, valores, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
    ax.set_ylabel('MAE', fontweight='bold')
    ax.set_title('Error Absoluto Medio', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{valores[i]:.2f}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('graficos/03_comparacion_modelos.png', dpi=300, bbox_inches='tight')
    plt.close()

# ---------------------------------------------------------------------------
# GRÁFICO 4: Distribución de Anomalías
# ---------------------------------------------------------------------------
print("   [4/5] Distribución de Anomalías...")

if len(anomalias) > 0:
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Análisis de Anomalías Detectadas', fontsize=16, fontweight='bold')
    
    # Por severidad
    ax = axes[0]
    severidad_counts = anomalias['severidad'].value_counts()
    colores = [colores_severidad.get(s, '#777777') for s in severidad_counts.index]
    bars = ax.bar(range(len(severidad_counts)), severidad_counts.values, color=colores)
    ax.set_xticks(range(len(severidad_counts)))
    ax.set_xticklabels([s.capitalize() for s in severidad_counts.index])
    ax.set_ylabel('Cantidad', fontweight='bold')
    ax.set_title('Anomalías por Severidad', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    # Por tipo
    ax = axes[1]
    tipo_counts = anomalias['tipo_anomalia'].value_counts()
    bars = ax.bar(range(len(tipo_counts)), tipo_counts.values, 
                  color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(tipo_counts)])
    ax.set_xticks(range(len(tipo_counts)))
    ax.set_xticklabels(tipo_counts.index, rotation=45, ha='right')
    ax.set_ylabel('Cantidad', fontweight='bold')
    ax.set_title('Anomalías por Tipo de Detector', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('graficos/04_distribucion_anomalias.png', dpi=300, bbox_inches='tight')
    plt.close()

# ---------------------------------------------------------------------------
# GRÁFICO 5: Serie Temporal Completa con Predicción
# ---------------------------------------------------------------------------
print("   [5/5] Serie Temporal Completa...")

fig, ax = plt.subplots(figsize=(18, 8))

# Dividir en pasado y futuro
ultimo_timestamp = df_datos['timestamp'].max()

# Datos históricos
ax.plot(df_datos['timestamp'], df_datos['value'], 
        '-', label='Datos Históricos', color='#2E86AB', linewidth=2)

# Línea vertical separando pasado de futuro
ax.axvline(x=ultimo_timestamp, color='red', linestyle='--', linewidth=2, 
           label='Fecha Actual', alpha=0.7)

# Predicciones
ax.plot(predicciones['timestamp'], predicciones['prediccion'], 
        's-', label='Predicciones', color='#A23B72', linewidth=2, markersize=6)

# Intervalos de confianza
if 'limite_inferior' in predicciones.columns:
    ax.fill_between(predicciones['timestamp'], 
                    predicciones['limite_inferior'], 
                    predicciones['limite_superior'],
                    alpha=0.2, color='#A23B72', label='Intervalo 95%')

# Anomalías
if len(anomalias) > 0:
    for severidad, color in colores_severidad.items():
        anomalias_sev = anomalias[anomalias['severidad'] == severidad]
        if len(anomalias_sev) > 0:
            # Merge para obtener valores
            anomalias_sev_plot = pd.merge(
                anomalias_sev[['timestamp']], 
                df_datos, 
                on='timestamp', 
                how='left'
            )
            ax.scatter(anomalias_sev_plot['timestamp'], anomalias_sev_plot['value'],
                      color=color, s=150, marker='X', 
                      label=f'Anomalía {severidad.capitalize()}', zorder=5, 
                      edgecolors='black', linewidths=1)

ax.set_xlabel('Fecha y Hora', fontsize=12, fontweight='bold')
ax.set_ylabel('Demanda Energética (GWh)', fontsize=12, fontweight='bold')
ax.set_title('Serie Temporal Completa: Histórico + Predicciones + Anomalías', 
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=10, ncol=2)
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('graficos/05_serie_temporal_completa.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================================================================
# Resumen
# ==============================================================================
print()
print("="*80)
print("GRÁFICOS GENERADOS EXITOSAMENTE")
print("="*80)
print()
print("Archivos creados en la carpeta 'graficos/':")
print("   [1] 01_predicciones_vs_historico.png")
print("   [2] 02_anomalias_detectadas.png")
print("   [3] 03_comparacion_modelos.png")
print("   [4] 04_distribucion_anomalias.png")
print("   [5] 05_serie_temporal_completa.png")
print()
print("Todos los gráficos están en alta resolución (300 DPI)")
print("Listos para incluir en informes o presentaciones")
print()
print("="*80)
