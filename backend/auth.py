# ===========================================
# auth.py — Manejo de usuarios y autenticación JWT
# ===========================================

from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import datetime
import jwt
import os
from common import db

# ------------------------------
# Modelo de Usuario
# ------------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ------------------------------
# Configuración de JWT
# ------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "mi_clave_supersecreta")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 3600  # 1 hora


# ------------------------------
# Generar token JWT
# ------------------------------
def generate_token(user_id, expires_in=JWT_EXPIRATION_SECONDS):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


# ------------------------------
# Decorador para endpoints protegidos
# ------------------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token requerido"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 403

        return f(user_id, *args, **kwargs)
    return decorated
