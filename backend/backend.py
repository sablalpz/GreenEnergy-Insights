# ===========================================
# app.py — Aplicación principal Flask
# ===========================================

from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from auth import token_required, generate_token
import os
from common import db, create_app, User, Config, db_access
from datetime import datetime, timedelta
from flask_cors import CORS
import subprocess
import sys
import pathlib
from jinja2 import TemplateNotFound
import json

# Crear la app indicando la carpeta frontend como ubicación de templates/static
# En contenedor montamos ./frontend en /app/frontend
frontend_templates = os.path.join(os.getcwd(), 'frontend')
app = create_app(template_folder=frontend_templates, static_folder=frontend_templates)
# Habilitar CORS para endpoints /api/* (permite que un frontend en otro origen llame a la API)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Registrar las rutas del motor_analitica si están disponibles
try:
    from motor_analitica.api import motor_bp
    app.register_blueprint(motor_bp)
except Exception as e:
    app.logger.warning(f"No se pudo registrar motor_analitica blueprint: {e}")


# ------------------------------
# Endpoint: datos de energía
# ------------------------------
@app.route("/api/energy/latest")
@token_required
def latest_energy(user_id):
    registros = db_access.get_latest_energy_data(limit=10)
    return jsonify({"user_id": user_id, "data": registros})


# ------------------------------
# Endpoint: login
# ------------------------------
@app.route("/api/login", methods=["GET", "POST"])
def login():
    # GET: devolver instrucción rápida y enlace al formulario visual
    if request.method == 'GET':
        return render_template_string('''
            <!doctype html>
            <html>
              <head><meta charset="utf-8"><title>Login API</title></head>
              <body>
                <p>Usa POST con JSON a <code>/api/login</code> o abre el formulario <a href="/login">/login</a>.</p>
              </body>
            </html>
        ''')

    # POST: aceptar JSON o form-encoded como fallback
    data = request.get_json(silent=True)
    if not data:
        # intentar form data (por ejemplo envío directo desde <form method="post">)
        form = request.form
        if form and 'username' in form and 'password' in form:
            data = {'username': form.get('username'), 'password': form.get('password')}

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Campos obligatorios: username y password"}), 400

    user = User.query.filter_by(username=data["username"]).first()
    if user and user.check_password(data["password"]):
        token = generate_token(user.id)
        return jsonify({"token": token})

    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401


# ------------------------------
# Crear usuarios (para pruebas)
# ------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Campos obligatorios: username y password"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "El usuario ya existe"}), 400

    user = User(username=data["username"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Usuario creado correctamente"}), 201


# -----------------------------------------------------------------------------
# Interfaz mínima para registro dinámico desde un frontend
# Devuelve un pequeño formulario que hace POST a /api/register y muestra la respuesta
# -----------------------------------------------------------------------------
@app.route('/register', methods=['GET'])
def register_form():
        html = '''
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8">
                <title>Registro - GreenEnergy Insights</title>
            </head>
            <body>
                <h2>Registro de usuario</h2>
                <form id="regForm">
                    <label>Usuario: <input type="text" id="username" required></label><br><br>
                    <label>Contraseña: <input type="password" id="password" required></label><br><br>
                    <button type="submit">Registrar</button>
                </form>
                <div id="result" style="margin-top:15px;color:green"></div>

                <script>
                document.getElementById('regForm').addEventListener('submit', async function(e){
                    e.preventDefault();
                    const u = document.getElementById('username').value;
                    const p = document.getElementById('password').value;
                    try{
                        const res = await fetch('/api/register', {
                            method: 'POST',
                            headers: {'Content-Type':'application/json'},
                            body: JSON.stringify({username: u, password: p})
                        });
                        const j = await res.json();
                        if(res.ok){
                            document.getElementById('result').style.color='green';
                            document.getElementById('result').innerText = j.message || JSON.stringify(j);
                        } else {
                            document.getElementById('result').style.color='red';
                            document.getElementById('result').innerText = j.error || JSON.stringify(j);
                        }
                    } catch(err){
                        document.getElementById('result').style.color='red';
                        document.getElementById('result').innerText = 'Error: '+err;
                    }
                });
                </script>
            </body>
        </html>
        '''
        return render_template_string(html)


@app.route('/login', methods=['GET'])
def login_form():
        html = '''
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8">
                <title>Login - GreenEnergy Insights</title>
            </head>
            <body>
                <h2>Iniciar sesión</h2>
                <form id="loginForm">
                    <label>Usuario: <input type="text" id="username" required></label><br><br>
                    <label>Contraseña: <input type="password" id="password" required></label><br><br>
                    <button type="submit">Entrar</button>
                </form>
                <div id="result" style="margin-top:15px;color:green"></div>

                <script>
                document.getElementById('loginForm').addEventListener('submit', async function(e){
                    e.preventDefault();
                    const u = document.getElementById('username').value;
                    const p = document.getElementById('password').value;
                    try{
                        const res = await fetch('/api/login', {
                            method: 'POST',
                            headers: {'Content-Type':'application/json'},
                            body: JSON.stringify({username: u, password: p})
                        });
                        const j = await res.json();
                        if(res.ok){
                            document.getElementById('result').style.color='green';
                            document.getElementById('result').innerText = 'Token: ' + (j.token || JSON.stringify(j));
                        } else {
                            document.getElementById('result').style.color='red';
                            document.getElementById('result').innerText = j.error || JSON.stringify(j);
                        }
                    } catch(err){
                        document.getElementById('result').style.color='red';
                        document.getElementById('result').innerText = 'Error: '+err;
                    }
                });
                </script>
            </body>
        </html>
        '''
        return render_template_string(html)


# NOTE: El endpoint /api/generate_graphs se ha eliminado. Se utiliza únicamente
# el script `visualizar_datos.py` (invocado desde /dashboard) para generar el HTML
# y los gráficos.


# ------------------------------
# Servir imágenes generadas por motor_analitica
# ------------------------------
@app.route('/motor_graficos/<path:filename>')
def serve_motor_grafico(filename):
    """Sirve archivos desde /app/motor_analitica/graficos"""
    graf_dir = pathlib.Path('/app/motor_analitica/graficos')
    if not graf_dir.exists():
        return jsonify({"error": "Carpeta de gráficos no encontrada"}), 404
    return send_from_directory(str(graf_dir), filename)


# ------------------------------
# Dashboard: devuelve la página HTML generada por `visualizar_datos.py`
# Si no existe, lanza el script en background y devuelve una página indicando que se está generando
# ------------------------------
@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Intentar renderizar la plantilla del dashboard (si el blueprint la registró)
    try:
        # Preparar datos iniciales en el servidor para que el frontend sea interactivo
        initial_data = {}
        try:
            from common import EnergyData, Anomaly, Prediction, ModelMetric

            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            initial_data['energyData'] = db_access.obtener_registros_rango(EnergyData, db.session, 'timestamp', start=seven_days_ago, order_by='timestamp', limit=10000, columns=['timestamp','demanda','precio'])

            initial_data['anomaliesStats'] = db_access.obtener_agg_anomalias(db.session, Anomaly)

            initial_data['predictions'] = db_access.obtener_registros(Prediction, db.session, order_by='timestamp.desc()', limit=50)

            metrics = db_access.obtener_registros(ModelMetric, db.session, order_by='timestamp.desc()', limit=1)
            initial_data['metrics'] = metrics[0] if metrics else None
        except Exception as e:
            app.logger.warning(f"No se pudieron obtener datos iniciales: {e}")
            initial_data = {'energyData': [], 'anomaliesStats': {}, 'predictions': [], 'metrics': None}

        # Renderizar plantilla y luego inyectar los datos iniciales en una variable global JS
        html = app.jinja_env.get_or_select_template('dashboard.html').render()
        inject_script = f"<script>window.INITIAL_DATA = {json.dumps(initial_data)};</script>"
        # intentar insertar antes de </body>
        if '</body>' in html:
            html = html.replace('</body>', inject_script + '</body>')
        else:
            html = inject_script + html

        return render_template_string(html)
    except TemplateNotFound:
        # Fallback: leer el archivo HTML generado en motor_analitica (si existe)
        # Fallback: primero buscar en la carpeta frontend (migración del dashboard)
        frontend_html = pathlib.Path(frontend_templates) / 'dashboard.html'
        motor_html = pathlib.Path('/app/motor_analitica/dashboard.html')

        candidates = [frontend_html, motor_html]

        for html_path in candidates:
            if html_path.exists():
                try:
                    html_text = html_path.read_text(encoding='utf-8')
                    # Ajustar rutas relativas a la ruta estática del backend
                    html_text = html_text.replace('src="graficos/', 'src="/motor_graficos/')
                    html_text = html_text.replace("href=\"graficos/", "href=\"/motor_graficos/")
                    return render_template_string(html_text)
                except Exception as e:
                    return jsonify({"error": f"Error leyendo HTML: {e}"}), 500

        # Si no existe en ninguna ubicación, devolver 404 indicando que no está generado aún
        return jsonify({"error": "Dashboard no generado aún. Ejecuta 'visualizar_datos.py' en el contenedor para crearlo en 'frontend/' o 'motor_analitica/'."}), 404


""" LLamadas a las herramientas del modelo, en este caso al script de visualización """


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5010, debug=True)
