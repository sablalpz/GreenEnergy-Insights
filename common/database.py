# /common/models.py
import os
from . import db 
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# ==============================
# Configuración base
# ==============================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))



def create_app():
    """Crea y configura la aplicación Flask con SQLAlchemy."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///fallback.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


# ==============================
# MODELOS UNIFICADOS
# ==============================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        """Cifra y almacena la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica una contraseña contra su hash."""
        return check_password_hash(self.password_hash, password)


class EnergyData(db.Model):
    __tablename__ = "energy_data"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    precio = db.Column(db.Float, nullable=False)  # €/MWh
    geo_id = db.Column(db.Integer, nullable=True)
    dia_semana = db.Column(db.Integer)
    hora_dia = db.Column(db.Integer)
    fin_de_semana = db.Column(db.Boolean)
    estacion = db.Column(db.String(10))
    demanda = db.Column(db.Float)  # Demanda eléctrica total

    __table_args__ = (
        db.UniqueConstraint("timestamp", "geo_id", name="unique_timestamp_geo"),
    )


# ==============================
# Crear tablas (opcional al ejecutar)
# ==============================
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Base de datos creada con las tablas 'users' y 'energy_data'")
