# db_manager.py
from common import db, EnergyData  # importa db y modelo desde tu ETL (api.py)

def _row_to_dict(r: EnergyData):
    """Convierte un registro EnergyData en un dict serializable (incluye id)."""
    return {
        "id": r.id,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        "precio": r.precio,
        "potencia": r.potencia,
        "geo_id": r.geo_id,
        "dia_semana": r.dia_semana,
        "hora_dia": r.hora_dia,
        "fin_de_semana": r.fin_de_semana,
        "estacion": r.estacion,
        "demanda": r.demanda,
    }

def insert_energy_data(timestamp, precio, demanda=None,
                       dia_semana=None, hora_dia=None, fin_de_semana=None,
                       estacion=None, geo_id=None, potencia=None):
    """Inserta un nuevo registro en energy_data y devuelve su id."""
    record = EnergyData(
        timestamp=timestamp,
        precio=precio,
        demanda=demanda,
        dia_semana=dia_semana,
        hora_dia=hora_dia,
        fin_de_semana=fin_de_semana,
        estacion=estacion,
        geo_id=geo_id,
        potencia=potencia
    )
    db.session.add(record)
    db.session.commit()
    return record.id

def get_all_energy_data():
    """Devuelve todos los registros como lista de dicts."""
    rows = EnergyData.query.order_by(EnergyData.timestamp).all()
    return [_row_to_dict(r) for r in rows]

def get_latest_energy_data(limit=10):
    """Devuelve los últimos registros como lista de dicts."""
    rows = EnergyData.query.order_by(EnergyData.timestamp.desc()).limit(limit).all()
    return [_row_to_dict(r) for r in rows]

def get_energy_data_by_id(record_id: int):
    """Devuelve un registro por id (dict o None)."""
    r = EnergyData.query.get(record_id)
    return _row_to_dict(r) if r else None

def delete_energy_data_by_id(record_id: int) -> bool:
    """Elimina un registro por id. Devuelve True si se eliminó."""
    record = EnergyData.query.get(record_id)
    if record:
        db.session.delete(record)
        db.session.commit()
        return True
    return False
