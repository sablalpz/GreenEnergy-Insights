from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import pyodbc
import re
from datetime import datetime

#Configuraciónd e modelo 
model_name = "microsoft/phi-2"
print("Cargando modelo y tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

#Conexión base de datos 
server = "udcserver2025.database.windows.net"
database = "grupo_2"
username = "ugrupo2"
password = "SYfL1sTc5EQzehpOjopx"

conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
    f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=50;"
)
cursor = conn.cursor()

#Extracción fehcay hora
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
    
#Consulta de tablas 
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

#RAG 
def recuperar_conocimiento(pregunta):
    try:
        cursor.execute("SELECT TOP 3 descripcion FROM knowledge_base WHERE descripcion LIKE ?", f"%{pregunta}%")
        rows = cursor.fetchall()
        if not rows:
            return ""
        return " ".join([r[0] for r in rows if r and r[0]])
    except Exception:
        return ""

def generar_respuesta(prompt, max_tokens=200):
    with torch.no_grad():
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.3,
            top_p=0.95,
            repetition_penalty=1.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    texto = tokenizer.decode(outputs[0], skip_special_tokens=True)
    texto = re.sub(r"(Exercise\s*\d*:.*|Answer:)", "", texto, flags=re.IGNORECASE)
    return texto.strip()

#intención de respuesta 
def detectar_intencion(texto):
    t = texto.lower().strip()

    #explicaciones 
    if any(t.startswith(p) for p in (
        "cómo", "como", "qué es", "que es", "por qué", "porque",
        "método", "metodo", "definir", "explica", "explícame", "explicame"
    )):
        return "explicacion"

    #comprobación de fechas y hora válidas 
    fecha, hora = extraer_fecha_hora(texto)
    if fecha and hora:
        if any(p in t for p in ["predic", "proyección", "proyeccion", "estimación", "estimacion"]):
            return "consulta_prediccion"
        if any(p in t for p in ["consumo", "demanda", "energía", "energia"]):
            return "consulta_real"
        #consultas de precio
        if any(p in t for p in ["precio", "price", "€/mwh", "eur/mwh", "euro/mwh"]):
            return "consulta_precio"

    #modelo 
    return "general"

def formatear_respuesta_sql(tabla, fila, cols, fecha, hora, intencion):
    if tabla == "energy_data":
        # esquema energy data 
        colmap = {name: cols.index(name) for name in cols}
        if intencion == "consulta_real":
            if "demanda" not in colmap:
                return "No se encontró la columna demanda en energy_data."
            v = fila[colmap["demanda"]]
            if v is None:
                return f"No hay dato de demanda para el {fecha} a las {hora}."
            return f"El consumo real el {fecha} a las {hora} fue de {v} MW."
        elif intencion == "consulta_precio":
            if "precio" not in colmap:
                return "No se encontró la columna precio en energy_data."
            p = fila[colmap["precio"]]
            if p is None:
                return f"No hay dato de precio para el {fecha} a las {hora}."
            return f"El precio el {fecha} a las {hora} fue de {p} €/MWh."
        else:
            return "Consulta no soportada para esta tabla."
    else:
        #esquema predictions
        colmap = {name: cols.index(name) for name in cols}
        if "prediccion" not in colmap:
            return "No se encontró la columna prediccion en predictions."
        pred = fila[colmap["prediccion"]]
        lim_inf = fila[colmap["limite_inferior"]] if "limite_inferior" in colmap else None
        lim_sup = fila[colmap["limite_superior"]] if "limite_superior" in colmap else None
        modelo = fila[colmap["modelo_usado"]] if "modelo_usado" in colmap else "desconocido"
        rango = (f"(rango: {lim_inf}-{lim_sup} MW)" 
                 if (lim_inf is not None and lim_sup is not None) else "(sin rango)")
        return f"La predicción para el {fecha} a las {hora} es de {pred} MW {rango}, modelo: {modelo}."
    
#Contexto para el chatbot
def prompt_explicacion(user_input, contexto):
    instrucciones = (
        "Eres experto en redes eléctricas. Si la pregunta es conceptual, "
        "responde en 4-6 viñetas, claras y concisas. No consultes base de datos. "
        "Usa pasos verificables (umbral, ventana, validación)."
    )
    return (
        f"{instrucciones}\n\n"
        f"Contexto (opcional): {contexto}\n\n"
        f"Pregunta: {user_input}\n"
        f"Responde en viñetas, conciso."
    )

print("Chatbot listo. Escribe 'salir' para terminar.\n")

while True:
    user_input = input("Tú: ").strip()
    if user_input.lower() == "salir":
        print("Chatbot: Adiós.")
        break

    intencion = detectar_intencion(user_input)

    if intencion in ("consulta_real", "consulta_prediccion", "consulta_precio"):
        fecha, hora = extraer_fecha_hora(user_input)
        if not (fecha and hora):
            if detectar_intencion("cómo " + user_input) == "explicacion":
                intencion = "explicacion"
            else:
                intencion = "general"
        else:
            tabla = "predictions" if intencion == "consulta_prediccion" else "energy_data"
            resultado = consultar_base(tabla, fecha, hora)
            if resultado:
                fila, cols = resultado
                print(formatear_respuesta_sql(tabla, fila, cols, fecha, hora, intencion))
                continue
            else:
                print("No se encontraron datos cercanos a esa fecha y hora.")
                continue

    if intencion == "explicacion":
        contexto = recuperar_conocimiento(user_input)
        prompt = prompt_explicacion(user_input, contexto)
        respuesta = generar_respuesta(prompt, max_tokens=220)
        print("Chatbot:", respuesta)
        continue

    #para preguntas generales 
    contexto = recuperar_conocimiento(user_input)
    prompt = (
        "Eres experto en redes eléctricas. Responde de forma clara y concisa.\n\n"
        f"Contexto (opcional): {contexto}\n\n"
        f"Pregunta: {user_input}\n"
        "Respuesta:"
    )
    respuesta = generar_respuesta(prompt, max_tokens=200)
    print("Chatbot:", respuesta)