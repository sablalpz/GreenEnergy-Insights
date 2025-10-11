"""
Visualizador de Datos Históricos y Predicciones
Genera visualización HTML con datos de Azure SQL y predicciones del Motor de Analítica
"""
import sys
import webbrowser
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from Config import Config
from motor_analitica import MotorAnalitica

# ==============================================================================
# Configurar conexión a Azure SQL
# ==============================================================================
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

class EnergyData(db.Model):
    __tablename__ = "energy_data"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, unique=True, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    geo_id = db.Column(db.Integer, nullable=True)
    dia_semana = db.Column(db.Integer, nullable=True)
    hora_dia = db.Column(db.Integer, nullable=True)
    fin_de_semana = db.Column(db.Boolean, nullable=True)
    estacion = db.Column(db.String(10), nullable=True)
    demanda = db.Column(db.Float, nullable=True)

# ==============================================================================
# Cargar datos históricos
# ==============================================================================
with app.app_context():
    records = EnergyData.query.filter(
        EnergyData.demanda != None
    ).order_by(EnergyData.timestamp.desc()).limit(50).all()
    
    if len(records) == 0:
        print("ERROR: No hay datos en la base de datos")
        sys.exit(1)
    
    # Invertir para orden cronológico
    records = list(reversed(records))
    
    df_historico = pd.DataFrame([
        {
            "timestamp": r.timestamp,
            "demanda": r.demanda,
            "precio": r.precio
        }
        for r in records
    ])

# ==============================================================================
# Entrenar modelos y generar predicciones
# ==============================================================================
with app.app_context():
    # Obtener todos los datos para entrenar
    all_records = EnergyData.query.filter(
        EnergyData.demanda != None
    ).order_by(EnergyData.timestamp).all()
    
    if len(all_records) < 100:
        print("ERROR: Se necesitan al menos 100 registros para entrenar")
        sys.exit(1)
    
    # === MODELO 1: PREDICCIÓN DE DEMANDA ===
    df_train_demanda = pd.DataFrame([
        {"timestamp": r.timestamp, "value": r.demanda}
        for r in all_records
    ])
    
    motor_demanda = MotorAnalitica(tipo_modelo='prophet')
    motor_demanda.entrenar(df_train_demanda)
    predicciones_demanda = motor_demanda.predecir(horizonte_horas=24)
    
    # === MODELO 2: PREDICCIÓN DE PRECIO ===
    df_train_precio = pd.DataFrame([
        {"timestamp": r.timestamp, "value": r.precio}
        for r in all_records
    ])
    
    motor_precio = MotorAnalitica(tipo_modelo='prophet')
    motor_precio.entrenar(df_train_precio)
    predicciones_precio = motor_precio.predecir(horizonte_horas=24)
    
    # Combinar predicciones
    df_predicciones = pd.DataFrame({
        "timestamp": predicciones_demanda['timestamp'],
        "demanda_predicha": predicciones_demanda['prediccion'].round(2),
        "precio_predicho": predicciones_precio['prediccion'].round(2),
        "demanda_limite_inferior": predicciones_demanda.get('limite_inferior', predicciones_demanda['prediccion']).round(2),
        "demanda_limite_superior": predicciones_demanda.get('limite_superior', predicciones_demanda['prediccion']).round(2),
        "precio_limite_inferior": predicciones_precio.get('limite_inferior', predicciones_precio['prediccion']).round(2),
        "precio_limite_superior": predicciones_precio.get('limite_superior', predicciones_precio['prediccion']).round(2)
    })

# ==============================================================================
# Calcular estadísticas comparativas
# ==============================================================================
stats_demanda_historico = df_historico['demanda'].describe()
stats_demanda_predicciones = df_predicciones['demanda_predicha'].describe()
stats_precio_historico = df_historico['precio'].describe()
stats_precio_predicciones = df_predicciones['precio_predicho'].describe()

# ==============================================================================
# Preparar datos para HTML
# ==============================================================================
df_historico_html = df_historico.copy()
df_historico_html['tipo'] = 'Histórico'
df_historico_html = df_historico_html.rename(columns={'demanda': 'demanda_valor', 'precio': 'precio_valor'})
df_historico_html['demanda_intervalo'] = None
df_historico_html['precio_intervalo'] = None

df_predicciones_html = df_predicciones.copy()
df_predicciones_html['tipo'] = 'Predicción'
df_predicciones_html = df_predicciones_html.rename(columns={'demanda_predicha': 'demanda_valor', 'precio_predicho': 'precio_valor'})
df_predicciones_html['demanda_intervalo'] = df_predicciones_html.apply(
    lambda x: f"{x['demanda_limite_inferior']:.2f} - {x['demanda_limite_superior']:.2f}", axis=1
)
df_predicciones_html['precio_intervalo'] = df_predicciones_html.apply(
    lambda x: f"{x['precio_limite_inferior']:.2f} - {x['precio_limite_superior']:.2f}", axis=1
)

# Combinar últimas 24 horas históricas + 24 horas predicciones
df_combined = pd.concat([
    df_historico_html[['timestamp', 'demanda_valor', 'demanda_intervalo', 'precio_valor', 'precio_intervalo', 'tipo']].tail(24),
    df_predicciones_html[['timestamp', 'demanda_valor', 'demanda_intervalo', 'precio_valor', 'precio_intervalo', 'tipo']]
], ignore_index=True)

# ==============================================================================
# Generar HTML
# ==============================================================================
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Datos Históricos y Predicciones - GreenEnergy Insights</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #2c3e50;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .historico {{
            background-color: #e8f4f8;
        }}
        .prediccion {{
            background-color: #fff4e6;
        }}
        .stats {{
            background-color: #e8f8f5;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .comparison-table {{
            width: 100%;
            margin: 20px 0;
            background: white;
            border-collapse: collapse;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .comparison-table th {{
            background-color: #2c3e50;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        .comparison-table td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .metric-label {{
            font-weight: bold;
            color: #34495e;
        }}
    </style>
</head>
<body>
    <h1>GreenEnergy Insights - Análisis de Demanda Energética</h1>
    
    <div class="stats">
        <h2>Resumen Estadístico</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Demanda Promedio Histórica</div>
                <div class="stat-value">{stats_demanda_historico['mean']:.2f} GWh</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Demanda Promedio Predicha</div>
                <div class="stat-value">{stats_demanda_predicciones['mean']:.2f} GWh</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Precio Promedio Histórico</div>
                <div class="stat-value">{stats_precio_historico['mean']:.2f} €/MWh</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Precio Promedio Predicho</div>
                <div class="stat-value">{stats_precio_predicciones['mean']:.2f} €/MWh</div>
            </div>
        </div>
    </div>
    
    <div class="stats">
        <h2>Estadísticas Comparativas Detalladas</h2>
        
        <h3>DEMANDA ENERGÉTICA (GWh)</h3>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Métrica</th>
                    <th>Histórico</th>
                    <th>Predicción</th>
                    <th>Diferencia</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="metric-label">Promedio</td>
                    <td>{stats_demanda_historico['mean']:.2f}</td>
                    <td>{stats_demanda_predicciones['mean']:.2f}</td>
                    <td>{(stats_demanda_predicciones['mean'] - stats_demanda_historico['mean']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">Desviación Estándar</td>
                    <td>{stats_demanda_historico['std']:.2f}</td>
                    <td>{stats_demanda_predicciones['std']:.2f}</td>
                    <td>{(stats_demanda_predicciones['std'] - stats_demanda_historico['std']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">Mínimo</td>
                    <td>{stats_demanda_historico['min']:.2f}</td>
                    <td>{stats_demanda_predicciones['min']:.2f}</td>
                    <td>{(stats_demanda_predicciones['min'] - stats_demanda_historico['min']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">Máximo</td>
                    <td>{stats_demanda_historico['max']:.2f}</td>
                    <td>{stats_demanda_predicciones['max']:.2f}</td>
                    <td>{(stats_demanda_predicciones['max'] - stats_demanda_historico['max']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">25% Percentil</td>
                    <td>{stats_demanda_historico['25%']:.2f}</td>
                    <td>{stats_demanda_predicciones['25%']:.2f}</td>
                    <td>{(stats_demanda_predicciones['25%'] - stats_demanda_historico['25%']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">50% Percentil (Mediana)</td>
                    <td>{stats_demanda_historico['50%']:.2f}</td>
                    <td>{stats_demanda_predicciones['50%']:.2f}</td>
                    <td>{(stats_demanda_predicciones['50%'] - stats_demanda_historico['50%']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">75% Percentil</td>
                    <td>{stats_demanda_historico['75%']:.2f}</td>
                    <td>{stats_demanda_predicciones['75%']:.2f}</td>
                    <td>{(stats_demanda_predicciones['75%'] - stats_demanda_historico['75%']):.2f}</td>
                </tr>
            </tbody>
        </table>
        
        <h3>PRECIO DEL MERCADO (€/MWh)</h3>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Métrica</th>
                    <th>Histórico</th>
                    <th>Predicción</th>
                    <th>Diferencia</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="metric-label">Promedio</td>
                    <td>{stats_precio_historico['mean']:.2f}</td>
                    <td>{stats_precio_predicciones['mean']:.2f}</td>
                    <td>{(stats_precio_predicciones['mean'] - stats_precio_historico['mean']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">Desviación Estándar</td>
                    <td>{stats_precio_historico['std']:.2f}</td>
                    <td>{stats_precio_predicciones['std']:.2f}</td>
                    <td>{(stats_precio_predicciones['std'] - stats_precio_historico['std']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">Mínimo</td>
                    <td>{stats_precio_historico['min']:.2f}</td>
                    <td>{stats_precio_predicciones['min']:.2f}</td>
                    <td>{(stats_precio_predicciones['min'] - stats_precio_historico['min']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">Máximo</td>
                    <td>{stats_precio_historico['max']:.2f}</td>
                    <td>{stats_precio_predicciones['max']:.2f}</td>
                    <td>{(stats_precio_predicciones['max'] - stats_precio_historico['max']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">25% Percentil</td>
                    <td>{stats_precio_historico['25%']:.2f}</td>
                    <td>{stats_precio_predicciones['25%']:.2f}</td>
                    <td>{(stats_precio_predicciones['25%'] - stats_precio_historico['25%']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">50% Percentil (Mediana)</td>
                    <td>{stats_precio_historico['50%']:.2f}</td>
                    <td>{stats_precio_predicciones['50%']:.2f}</td>
                    <td>{(stats_precio_predicciones['50%'] - stats_precio_historico['50%']):.2f}</td>
                </tr>
                <tr>
                    <td class="metric-label">75% Percentil</td>
                    <td>{stats_precio_historico['75%']:.2f}</td>
                    <td>{stats_precio_predicciones['75%']:.2f}</td>
                    <td>{(stats_precio_predicciones['75%'] - stats_precio_historico['75%']):.2f}</td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <h2>Datos Históricos (Últimas 24 horas) + Predicciones (Próximas 24 horas)</h2>
    
    <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; border-radius: 4px;">
        <strong>Predicción Dual:</strong> El sistema entrena dos modelos Prophet independientes para predecir 
        <strong>demanda energética</strong> y <strong>precio del mercado eléctrico</strong>.
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Fecha y Hora</th>
                <th>Demanda (GWh)</th>
                <th>Intervalo Demanda</th>
                <th>Tipo</th>
                <th>Precio (€/MWh)</th>
                <th>Intervalo Precio</th>
            </tr>
        </thead>
        <tbody>
"""

for idx, row in df_combined.iterrows():
    clase = 'historico' if row['tipo'] == 'Histórico' else 'prediccion'
    timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M') if isinstance(row['timestamp'], datetime) else str(row['timestamp'])
    
    # Para predicciones, mostrar valores predichos con intervalos
    if row['tipo'] == 'Predicción':
        precio_str = f"<strong>{row['precio_valor']:.2f}</strong>" if pd.notna(row['precio_valor']) else '-'
        intervalo_demanda_str = f"<small style='color: #7f8c8d;'>[{row['demanda_intervalo']}]</small>" if pd.notna(row['demanda_intervalo']) else '-'
        intervalo_precio_str = f"<small style='color: #7f8c8d;'>[{row['precio_intervalo']}]</small>" if pd.notna(row['precio_intervalo']) else '-'
    else:
        precio_str = f"{row['precio_valor']:.2f}" if pd.notna(row['precio_valor']) else '-'
        intervalo_demanda_str = '-'
        intervalo_precio_str = '-'
    
    html_content += f"""
            <tr class="{clase}">
                <td>{timestamp_str}</td>
                <td><strong>{row['demanda_valor']:.2f}</strong></td>
                <td>{intervalo_demanda_str}</td>
                <td><strong>{row['tipo']}</strong></td>
                <td>{precio_str}</td>
                <td>{intervalo_precio_str}</td>
            </tr>
    """

html_content += """
        </tbody>
    </table>
    
    <h2>Gráficos Comparativos</h2>
    
    <div style="background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; border-radius: 4px;">
        <strong>Nota:</strong> Los siguientes gráficos muestran análisis detallados de las predicciones, 
        comparación de modelos y anomalías detectadas. Los gráficos se generan automáticamente al ejecutar 
        <code>generar_graficos.py</code>
    </div>
    
    <div style="margin: 20px 0;">
        <h3 style="color: #2c3e50; margin-top: 30px;">Predicciones vs Datos Históricos</h3>
        <p style="color: #7f8c8d; margin-bottom: 15px;">
            Comparación de las últimas 72 horas de datos históricos con las predicciones para las próximas 48 horas.
        </p>
        <img src="graficos/01_predicciones_vs_historico.png" alt="Predicciones vs Histórico" 
             style="width: 100%; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0;" 
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display: none; background-color: #fff4e6; padding: 15px; border-radius: 5px; border-left: 4px solid #F57C00;">
            Gráfico no disponible. Ejecuta <code>python generar_graficos.py</code> para generarlo.
        </div>
    </div>
    
    <div style="margin: 20px 0;">
        <h3 style="color: #2c3e50; margin-top: 30px;">Anomalías Detectadas</h3>
        <p style="color: #7f8c8d; margin-bottom: 15px;">
            Visualización de todas las anomalías detectadas en la serie temporal, clasificadas por severidad.
        </p>
        <img src="graficos/02_anomalias_detectadas.png" alt="Anomalías Detectadas" 
             style="width: 100%; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display: none; background-color: #fff4e6; padding: 15px; border-radius: 5px; border-left: 4px solid #F57C00;">
            Gráfico no disponible. Ejecuta <code>python generar_graficos.py</code> para generarlo.
        </div>
    </div>
    
    <div style="margin: 20px 0;">
        <h3 style="color: #2c3e50; margin-top: 30px;">Comparación de Modelos</h3>
        <p style="color: #7f8c8d; margin-bottom: 15px;">
            Evaluación comparativa de cuatro modelos de Machine Learning: Prophet, Random Forest, Gradient Boosting y LSTM.
        </p>
        <img src="graficos/03_comparacion_modelos.png" alt="Comparación de Modelos" 
             style="width: 100%; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display: none; background-color: #fff4e6; padding: 15px; border-radius: 5px; border-left: 4px solid #F57C00;">
            Gráfico no disponible. Ejecuta <code>python generar_graficos.py</code> para generarlo.
        </div>
    </div>
    
    <div style="margin: 20px 0;">
        <h3 style="color: #2c3e50; margin-top: 30px;">Distribución de Anomalías</h3>
        <p style="color: #7f8c8d; margin-bottom: 15px;">
            Análisis estadístico de las anomalías detectadas por severidad y método de detección.
        </p>
        <img src="graficos/04_distribucion_anomalias.png" alt="Distribución de Anomalías" 
             style="width: 100%; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display: none; background-color: #fff4e6; padding: 15px; border-radius: 5px; border-left: 4px solid #F57C00;">
            Gráfico no disponible. Ejecuta <code>python generar_graficos.py</code> para generarlo.
        </div>
    </div>
    
    <div style="margin: 20px 0;">
        <h3 style="color: #2c3e50; margin-top: 30px;">Serie Temporal Completa</h3>
        <p style="color: #7f8c8d; margin-bottom: 15px;">
            Vista panorámica que integra datos históricos, predicciones futuras y todas las anomalías detectadas.
        </p>
        <img src="graficos/05_serie_temporal_completa.png" alt="Serie Temporal Completa" 
             style="width: 100%; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display: none; background-color: #fff4e6; padding: 15px; border-radius: 5px; border-left: 4px solid #F57C00;">
            Gráfico no disponible. Ejecuta <code>python generar_graficos.py</code> para generarlo.
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 30px; color: #7f8c8d; font-size: 0.9em;">
        <p>Generado por Motor de Analítica Avanzada - GreenEnergy Insights</p>
        <p>Fecha de generación: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </div>
</body>
</html>
"""

# ==============================================================================
# Guardar y abrir HTML
# ==============================================================================
output_file = 'visualizacion_datos_predicciones.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Visualización generada: {output_file}")

# Abrir automáticamente en el navegador
try:
    webbrowser.open(output_file)
    print("   Abriendo en el navegador...")
except:
    print("   Abre manualmente el archivo HTML en tu navegador")
