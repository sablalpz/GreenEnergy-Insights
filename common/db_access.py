# db_manager.py
from common import db  # importa db y modelo desde tu ETL (api.py)
from datetime import datetime, timedelta
import json


def row_to_dict(row, columns=None):
    """
    Convierte un registro en un dict serializable.
    Args:
        row: instancia de modelo SQLAlchemy
        columns: lista de columnas a incluir (opcional)
    Returns:
        dict
    """
    if columns is None:
        columns = row.__table__.columns.keys()
    result = {}
    for col in columns:
        val = getattr(row, col)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        result[col] = val
    return result


#################################################################################
            #Adición de nuevos datos a las tablas de la base de datos# 
#################################################################################
def guardar_registro(model_class, session, **kwargs):
    """
    Inserta un nuevo registro en la tabla indicada por model_class.
    Args:
        model_class: clase del modelo SQLAlchemy
        session: sesión de SQLAlchemy
        kwargs: campos del modelo
    Returns:
        id del registro creado
    """
    record = model_class(**kwargs)
    session.add(record)
    session.commit()
    return record.id


def guardar_registros_desde_df(df, model_class, session, unique_fields=None, extra_fields=None):
    """
    Guarda registros desde un DataFrame en la tabla indicada por model_class.
    Args:
        df: DataFrame con los datos
        model_class: clase del modelo SQLAlchemy
        session: sesión de SQLAlchemy
        unique_fields: lista de campos para verificar duplicados
        extra_fields: dict de campos extra a añadir a cada registro
    Returns:
        int: número de registros guardados
    """
    nuevas = 0
    extra_fields = extra_fields or {}
    for _, row in df.iterrows():
        filtro = {f: row[f] for f in unique_fields} if unique_fields else {}
        existe = session.query(model_class).filter_by(**filtro).first() if filtro else None
        if not existe:
            datos = {**row.to_dict(), **extra_fields}
            registro = model_class(**datos)
            session.add(registro)
            nuevas += 1
    session.commit()
    return nuevas
    


    # Usar guardar_registros_desde_df para anomalias también

def guardar_metricas(model_class, session, nombre_modelo, metricas_dict, n_samples=None, metadata=None):
    """
    Guarda métricas del modelo en la tabla indicada por model_class.
    Args:
        model_class: clase del modelo SQLAlchemy
        session: sesión de SQLAlchemy
        nombre_modelo: nombre del modelo
        metricas_dict: dict de métricas
        n_samples: número de muestras
        metadata: dict de información extra
    Returns:
        id del registro guardado
    """
    metrica = model_class(
        nombre_modelo=nombre_modelo,
        timestamp=datetime.now(),
        mape=metricas_dict.get('MAPE'),
        smape=metricas_dict.get('SMAPE'),
        rmse=metricas_dict.get('RMSE'),
        mae=metricas_dict.get('MAE'),
        r2=metricas_dict.get('R2'),
        n_samples=n_samples,
        metadata_json=json.dumps(metadata) if metadata else None
    )
    session.add(metrica)
    session.commit()
    return metrica.id

#################################################################################
                    #Lectura de datos de las tablas# 
#################################################################################

def obtener_registros(model_class, session, filters=None, order_by=None, limit=100, columns=None):
    """
    Obtiene registros de la tabla indicada por model_class.
    Args:
        model_class: clase del modelo SQLAlchemy
        session: sesión de SQLAlchemy
        filters: dict de filtros
        order_by: campo para ordenar (descendente si termina en .desc())
        limit: límite de registros
        columns: columnas a devolver
    Returns:
        list de dicts
    """
    query = session.query(model_class)
    if filters:
        for k, v in filters.items():
            query = query.filter(getattr(model_class, k) == v)
    if order_by:
        if order_by.endswith('.desc()'):
            col = order_by.replace('.desc()', '')
            query = query.order_by(getattr(model_class, col).desc())
        else:
            query = query.order_by(getattr(model_class, order_by))
    query = query.limit(limit)
    registros = query.all()
    return [row_to_dict(r, columns) for r in registros]


    # Usar obtener_registros para anomalias también


    # Usar obtener_registros para métricas también


#################################################################################
                    #Lectura de datos de las tablas# 
#################################################################################


def limpiar_registros_antiguos(model_class, session, fecha_field, dias=30):
    """
    Elimina registros más antiguos de X días en la tabla indicada por model_class.
    Args:
        model_class: clase del modelo SQLAlchemy
        session: sesión de SQLAlchemy
        fecha_field: campo de fecha para filtrar
        dias: número de días a mantener
    Returns:
        int: número de registros eliminados
    """
    fecha_limite = datetime.now() - timedelta(days=dias)
    eliminadas = session.query(model_class).filter(
        getattr(model_class, fecha_field) < fecha_limite
    ).delete()
    session.commit()
    print(f"   ✓ Eliminadas {eliminadas} registros antiguos")
    return eliminadas


def obtener_estadisticas(session, model_classes):
    """
    Obtiene estadísticas generales de las tablas indicadas.
    Args:
        session: sesión de SQLAlchemy
        model_classes: dict con nombres y clases de modelos
    Returns:
        dict: estadísticas
    """
    stats = {}
    for nombre, model_class in model_classes.items():
        stats[f'total_{nombre}'] = session.query(model_class).count()
    # Ejemplo para modelos únicos y última predicción si existen los campos
    if 'predicciones' in model_classes:
        Prediction = model_classes['predicciones']
        stats['modelos_unicos'] = session.query(Prediction.modelo_usado).distinct().count()
        total_predicciones = stats['total_predicciones']
        if total_predicciones > 0:
            stats['ultima_prediccion'] = session.query(Prediction).order_by(
                Prediction.fecha_generacion.desc()
            ).first().fecha_generacion
        else:
            stats['ultima_prediccion'] = None
    return stats
