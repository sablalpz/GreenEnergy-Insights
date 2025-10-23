from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import pyodbc
import re
from datetime import datetime


# Configuración del modelo
model_name = "microsoft/phi-2"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Cargando modelo y tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    cache_dir="/root/.cache/huggingface",
    dtype=torch.float16,
)
model = model.to(device)


# Conexión base de datos
server = "udcserver2025.database.windows.net"
database = "grupo_2"
username = "ugrupo2"
password = "SYfL1sTc5EQzehpOjopx"


conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
    f"Encrypt=no;TrustServerCertificate=yes;Connection Timeout=80;"
)
cursor = conn.cursor()


# Extracción de fecha y hora
def columnas_actuales(cur):
    return [c[0].lower() for c in cur.description] if cur.description else []


def extraer_fecha_hora(texto):
    fecha_match = re.search(r"\b(\d{1,2}-\d{1,2}-\d{4})\b", texto)
    hora_match = re.search(r"\b(\d{1,2}:\d{2})\b", texto)
    if not (fecha_match and hora_match):
        return None, None
    fecha = fecha_match.group(1)
    hora = hora_match.group(1)
    try:
        _ = datetime.strptime(f"{fecha} {hora}", "%d-%m-%Y %H:%M")
        return fecha, hora
    except ValueError:
        return None, None


# Consulta de tablas
def consultar_base(tabla, fecha=None, hora=None):
    tablas_validas = {"energy_data", "predictions"}
    if tabla not in tablas_validas:
        raise ValueError("Nombre de tabla no permitido")
    if not (fecha and hora):
        return None
    try:
        fecha_hora = datetime.strptime(f"{fecha} {hora}", "%d-%m-%Y %H:%M")
        query = f"""
        SELECT TOP 1 *
        FROM {tabla}
        WHERE ABS(DATEDIFF(MINUTE, timestamp, ?)) <= 30
        ORDER BY ABS(DATEDIFF(MINUTE, timestamp, ?))
        """
        cursor.execute(query, fecha_hora, fecha_hora)
        fila = cursor.fetchone()
        if not fila:
            return None
        cols = columnas_actuales(cursor)
        return fila, cols
    except Exception as e:
        print("Error en la consulta SQL:", e)
        return None


# Recuperar contexto adicional
def recuperar_conocimiento(pregunta):
    try:
        cursor.execute("SELECT TOP 3 descripcion FROM knowledge_base WHERE descripcion LIKE ?", f"%{pregunta}%")
        rows = cursor.fetchall()
        if not rows:
            return ""
        return " ".join([r[0] for r in rows if r and r[0]])
    except Exception:
        return ""


def generar_respuesta(prompt, max_tokens=400):
    """
    Genera texto largo, coherente y detallado.
    Ajustes:
    - max_new_tokens elevado a 400
    - min_new_tokens y early_stopping para mantener longitud
    - temperature 0.7 y top_p 0.9 para mayor creatividad
    - repetition_penalty bajo para fluidez
    """
    with torch.no_grad():
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            min_new_tokens=150,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.03,
            do_sample=True,
            early_stopping=False,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    texto = tokenizer.decode(outputs[0], skip_special_tokens=True)
    texto = re.sub(r"(Exercise\s*\d*:.*|Answer:)", "", texto, flags=re.IGNORECASE)
    texto = texto.replace("Eres experto en redes eléctricas.", "").strip()
    return texto


# Intención de respuesta
def detectar_intencion(texto):
    t = texto.lower().strip()


    # Explicaciones
    if any(t.startswith(p) for p in (
        "cómo", "como", "qué es", "que es", "por qué", "porque",
        "método", "metodo", "definir", "explica", "explícame", "explicame"
    )):
        return "explicacion"


    # Comprobación de fechas
    fecha, hora = extraer_fecha_hora(texto)
    if fecha and hora:
        if any(p in t for p in ["predic", "proyección", "proyeccion", "estimación", "estimacion"]):
            return "consulta_prediccion"
        if any(p in t for p in ["consumo", "demanda", "energía", "energia"]):
            return "consulta_real"
        if any(p in t for p in ["precio", "price", "€/mwh", "eur/mwh", "euro/mwh"]):
            return "consulta_precio"


    return "general"


def formatear_respuesta_sql(tabla, fila, cols, fecha, hora, intencion):
    if tabla == "energy_data":
        colmap = {name: cols.index(name) for name in cols}
        if intencion == "consulta_real":
            v = fila[colmap.get("demanda")]
            if v is None:
                return f"No hay dato de demanda para el {fecha} a las {hora}."
            return f"El consumo real el {fecha} a las {hora} fue de {v} MW."
        elif intencion == "consulta_precio":
            p = fila[colmap.get("precio")]
            if p is None:
                return f"No hay dato de precio para el {fecha} a las {hora}."
            return f"El precio el {fecha} a las {hora} fue de {p} €/MWh."
        else:
            return "Consulta no soportada para esta tabla."


    else:
        colmap = {name: cols.index(name) for name in cols}
        pred = fila[colmap.get("prediccion")]
        inf = fila[colmap.get("limite_inferior")]
        sup = fila[colmap.get("limite_superior")]
        modelo = fila[colmap.get("modelo_usado")]
        rango = f"(rango: {inf}-{sup} MW)" if inf and sup else "(sin rango)"
        return f"La predicción para el {fecha} a las {hora} es de {pred} MW {rango}, modelo: {modelo}."


# Prompts
def prompt_explicacion(user_input, contexto):
    instrucciones = (
        "Eres experto en redes eléctricas. Si la pregunta es conceptual, "
        "responde en 6-8 viñetas amplias y detalladas. No consultes base de datos. "
        "Incluye ejemplos técnicos y causas comunes."
    )
    return (
        f"{instrucciones}\n\n"
        f"Contexto (opcional): {contexto}\n\n"
        f"Pregunta: {user_input}\n"
        f"Responde de manera extensa, clara y concisa."
    )


def responder_chat(user_input):
    t = (user_input or "").strip()
    if not t:
        return "Por favor, escribe una pregunta."


    intencion = detectar_intencion(t)


    if intencion in ("consulta_real", "consulta_prediccion", "consulta_precio", "consulta_dia_semana"):
        fecha, hora = extraer_fecha_hora(t)
        if not (fecha and hora):
            if detectar_intencion("cómo " + t) == "explicacion":
                intencion = "explicacion"
            else:
                intencion = "general"
        else:
            tabla = "predictions" if intencion == "consulta_prediccion" else "energy_data"
            result = consultar_base(tabla, fecha, hora)
            if result:
                fila, cols = result
                return formatear_respuesta_sql(tabla, fila, cols, fecha, hora, intencion)
            else:
                return "No se encontraron datos cercanos a esa fecha y hora."


    if intencion == "explicacion":
        contexto = recuperar_conocimiento(t)
        prompt = prompt_explicacion(t, contexto)
        return generar_respuesta(prompt, max_tokens=400)


    contexto = recuperar_conocimiento(t)
    prompt = (
        "Actúa como un ingeniero eléctrico experto en sistemas de energía y redes eléctricas. "
        "Responde de forma clara, técnica y detallada a la pregunta que te hagan, "
        "ofreciendo ejemplos prácticos y explicaciones completas cuando corresponda. "
        "Evita repetir la pregunta ni formular subpreguntas en la respuesta. "
        "Puedes abordar una variedad de temas relacionados con ingeniería eléctrica, "
        "incluyendo funcionamiento, anomalías, componentes y predicciones.\n\n"
        f"Contexto adicional (si disponible): {contexto}\n\n"
        f"Pregunta del usuario: {user_input}\n\n"
        "Respuesta:"
    )
    return generar_respuesta(prompt, max_tokens=400)

