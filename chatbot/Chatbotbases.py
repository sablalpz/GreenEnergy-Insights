import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import pyodbc

model_name = "microsoft/phi-2"
print("Cargando modelo y tokenizer...")
# Workaround: permite ejecutar aún si hay más de un runtime OpenMP cargado.
# Preferible solucionar en el entorno (ver instrucciones en la terminal),
# pero esto ayuda para pruebas locales rápidas.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

# Algunos modelos remotos (repos privados o con código personalizado) requieren
# permiso para ejecutar código remoto. Para pruebas locales puedes activar
# trust_remote_code=True (acepta ejecutar el código del repo del modelo).
try:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
except Exception as e:
    print("Error cargando el modelo solicitado (", model_name, ").")
    print("Motivo:", e)
    print()
    print("Opciones:")
    print(" - Actualizar 'transformers' a la última versión: pip install -U transformers accelerate safetensors")
    print(" - Usar otro modelo más pequeño para pruebas (p.ej. 'gpt2')")
    print()
    # Intentar cargar un modelo de fallback ligero para permitir pruebas locales
    fallback = "gpt2"
    try:
        print(f"Intentando cargar modelo de fallback '{fallback}'...")
        tokenizer = AutoTokenizer.from_pretrained(fallback)
        model = AutoModelForCausalLM.from_pretrained(fallback)
        print("Modelo de fallback cargado. Nota: comportamiento y calidad diferentes.")
    except Exception as e2:
        print("No se pudo cargar el modelo de fallback. Debes actualizar 'transformers' o elegir otro modelo.")
        print("Excepción fallback:", e2)
        raise

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

server = "udcserver2025.database.windows.net"
database = "grupo_2"
username = "ugrupo2"
password = "SYfL1sTc5EQzehpOjopx"

conn = pyodbc.connect(
    f"DRIVER={{SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
)
cursor = conn.cursor()

def consultar_base(tabla, fecha=None, hora=None):
    """Consulta tablas energy_data o predictions según fecha y hora."""
    query = f"SELECT * FROM {tabla}"
    conditions = []
    if fecha:
        conditions.append(f"fecha = '{fecha}'")
    if hora:
        conditions.append(f"hora = '{hora}'")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    cursor.execute(query)
    filas = cursor.fetchall()
    return filas

def generar_respuesta(prompt, max_tokens=150):
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    outputs = model.generate(**inputs, max_new_tokens=max_tokens)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print("Chatbot listo. Escribe 'salir' para terminar.")

while True:
    user_input = input("Tú: ")
    if user_input.lower() == "salir":
        break

    # Detección de intención de consulta de datos
    if any(p in user_input.lower() for p in ["consumo", "predicción", "energia", "anomalía"]):
        # Extraer fecha y hora de la pregunta 
        import re
        fecha_match = re.search(r"\b(\d{1,2}-\d{1,2}-\d{4})\b", user_input)
        hora_match = re.search(r"\b(\d{1,2}:\d{1,2})\b", user_input)
        fecha = fecha_match.group(1) if fecha_match else None
        hora = hora_match.group(1) if hora_match else None

        tabla = "predictions" if "predicción" in user_input.lower() else "energy_data"
        try:
            resultado = consultar_base(tabla, fecha, hora)
            if resultado:
                print("Base de datos:", resultado)
            else:
                print("No se encontraron datos para la consulta.")
        except Exception as e:
            print("Error en la consulta:", e)
        continue

    respuesta = generar_respuesta(user_input)
    print("Chatbot:", respuesta)