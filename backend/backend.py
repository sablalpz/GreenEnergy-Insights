# ===========================================
# app.py — Aplicación principal Flask
# ===========================================

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from auth import token_required, generate_token
import os
from common import db, create_app, User, Config, db_access

app = create_app()


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
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
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


""" LLamadas a las herramientas del modelo, en este caso al script de visualización """


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5010, debug=True)
