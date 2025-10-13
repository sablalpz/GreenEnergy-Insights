"""
Generador de datos sintéticos de demanda para Azure SQL
Solo genera datos SI NO hay suficientes datos reales de demanda
"""
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import numpy as np
import random

# Agregar el directorio padre al path para importar Config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Config import Config

print("="*80)
print("GENERADOR DE DATOS SINTÉTICOS DE DEMANDA")
print("="*80)
print()

# Configurar Flask y SQLAlchemy
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Modelo de la tabla
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

def obtener_estacion(fecha):
    """Determina la estación del año"""
    mes = fecha.month
    if mes in [12, 1, 2]:
        return 'invierno'
    elif mes in [3, 4, 5]:
        return 'primavera'
    elif mes in [6, 7, 8]:
        return 'verano'
    else:
        return 'otoño'

def generar_demanda_realista(timestamp):
    """
    Genera un valor de demanda sintético pero realista
    Basado en patrones reales de demanda eléctrica en España
    """
    hora = timestamp.hour
    dia_semana = timestamp.weekday()  # 0=Lunes, 6=Domingo
    mes = timestamp.month
    
    # Demanda base por hora (patrón típico español en GWh)
    demanda_por_hora = {
        0: 75, 1: 70, 2: 68, 3: 67, 4: 68, 5: 72,
        6: 78, 7: 85, 8: 95, 9: 105, 10: 110, 11: 112,
        12: 110, 13: 108, 14: 105, 15: 103, 16: 105, 17: 108,
        18: 115, 19: 125, 20: 130, 21: 120, 22: 105, 23: 88
    }
    
    demanda_base = demanda_por_hora[hora]
    
    # Ajuste por día de la semana
    if dia_semana >= 5:  # Fin de semana
        demanda_base *= 0.85
    
    # Ajuste por estación
    if mes in [1, 2, 12, 7, 8]:  # Invierno y verano (más demanda)
        demanda_base *= 1.15
    elif mes in [3, 4, 10, 11]:  # Primavera y otoño
        demanda_base *= 1.0
    else:  # Mayo, junio, septiembre
        demanda_base *= 0.95
    
    # Añadir variabilidad aleatoria ±5%
    variacion = random.uniform(-0.05, 0.05)
    demanda_final = demanda_base * (1 + variacion)
    
    # Añadir ocasionalmente picos o valles más pronunciados (5% de probabilidad)
    if random.random() < 0.05:
        factor_anomalo = random.choice([0.7, 1.3])  # Valle o pico
        demanda_final *= factor_anomalo
    
    return round(demanda_final, 2)

def generar_datos_sinteticos(num_dias=90):
    """
    Genera datos sintéticos de demanda para los últimos N días
    SOLO si no hay suficientes datos reales
    """
    with app.app_context():
        # Verificar cuántos registros con demanda existen
        registros_con_demanda = EnergyData.query.filter(
            EnergyData.demanda != None
        ).count()
        
        print(f"Registros actuales con demanda: {registros_con_demanda}")
        
        MINIMO_REQUERIDO = 100  # Mínimo para entrenar modelos
        
        if registros_con_demanda >= MINIMO_REQUERIDO:
            print(f"\n[OK] Ya hay {registros_con_demanda} registros con demanda.")
            print("No es necesario generar datos sintéticos.")
            print("El sistema usará los datos reales existentes.")
            return 0
        
        print(f"\n[INFO] Solo hay {registros_con_demanda} registros con demanda.")
        print(f"[INFO] Se necesitan al menos {MINIMO_REQUERIDO} para entrenar modelos ML.")
        print(f"\nGenerando {num_dias} días de datos sintéticos de demanda...")
        print("Estos datos son realistas y basados en patrones reales de España.\n")
        
        # Obtener el último timestamp en la BD
        ultimo_registro = EnergyData.query.order_by(
            EnergyData.timestamp.desc()
        ).first()
        
        if ultimo_registro:
            # Empezar después del último registro
            fecha_inicio = ultimo_registro.timestamp + timedelta(hours=1)
        else:
            # Si no hay registros, empezar hace N días
            fecha_inicio = datetime.utcnow() - timedelta(days=num_dias)
        
        registros_nuevos = 0
        registros_hora = num_dias * 24
        
        print(f"Generando {registros_hora} registros (1 por hora)...")
        
        for i in range(registros_hora):
            timestamp = fecha_inicio + timedelta(hours=i)
            
            # Verificar si ya existe ese timestamp
            existe = EnergyData.query.filter_by(timestamp=timestamp).first()
            if existe:
                # Si existe, solo actualizar demanda si está vacía
                if existe.demanda is None:
                    existe.demanda = generar_demanda_realista(timestamp)
                    existe.dia_semana = timestamp.weekday()
                    existe.hora_dia = timestamp.hour
                    existe.fin_de_semana = timestamp.weekday() >= 5
                    existe.estacion = obtener_estacion(timestamp)
                    registros_nuevos += 1
            else:
                # Crear nuevo registro con datos sintéticos
                demanda = generar_demanda_realista(timestamp)
                precio = round(random.uniform(50, 300), 2)  # Precio sintético
                
                nuevo = EnergyData(
                    timestamp=timestamp,
                    precio=precio,
                    demanda=demanda,
                    dia_semana=timestamp.weekday(),
                    hora_dia=timestamp.hour,
                    fin_de_semana=timestamp.weekday() >= 5,
                    estacion=obtener_estacion(timestamp)
                )
                db.session.add(nuevo)
                registros_nuevos += 1
            
            # Commit cada 100 registros para mejor performance
            if (i + 1) % 100 == 0:
                db.session.commit()
                print(f"   Procesados {i + 1}/{registros_hora} registros...")
        
        # Commit final
        db.session.commit()
        
        print(f"\n[OK] Generación completada!")
        print(f"Registros nuevos/actualizados: {registros_nuevos}")
        
        # Mostrar estadísticas finales
        total_con_demanda = EnergyData.query.filter(
            EnergyData.demanda != None
        ).count()
        
        print(f"\nEstadísticas finales:")
        print(f"   - Total registros con demanda: {total_con_demanda}")
        
        if total_con_demanda > 0:
            demandas = db.session.query(EnergyData.demanda).filter(
                EnergyData.demanda != None
            ).all()
            valores = [d[0] for d in demandas]
            print(f"   - Demanda mínima: {min(valores):.2f} GWh")
            print(f"   - Demanda máxima: {max(valores):.2f} GWh")
            print(f"   - Demanda promedio: {sum(valores)/len(valores):.2f} GWh")
        
        return registros_nuevos

if __name__ == "__main__":
    print("Este script generará datos sintéticos SOLO si no hay suficientes datos reales.\n")
    
    try:
        nuevos = generar_datos_sinteticos(num_dias=90)
        
        if nuevos > 0:
            print("\n" + "="*80)
            print("DATOS SINTÉTICOS GENERADOS EXITOSAMENTE")
            print("="*80)
            print("\nAhora puedes ejecutar:")
            print("   python demo_motor_avanzado.py")
            print("\nPara entrenar modelos con estos datos.")
        else:
            print("\n" + "="*80)
            print("NO SE GENERARON DATOS SINTÉTICOS")
            print("="*80)
            print("\nYa hay suficientes datos reales en la base de datos.")
        
    except Exception as e:
        print(f"\nERROR al generar datos: {e}")
        import traceback
        traceback.print_exc()
