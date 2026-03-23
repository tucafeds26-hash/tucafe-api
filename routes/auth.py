from flask import Blueprint, request, jsonify
from config.database import db
from models.usuario import Usuario
from flask_jwt_extended import create_access_token

auth_api = Blueprint('auth_api', __name__)

@auth_api.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify({"msg": "Datos incompletos"}), 400

    user = Usuario.query.filter_by(correo=correo).first()

    if not user or user.password != password:
        return jsonify({"msg": "Credenciales incorrectas"}), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "correo": user.correo
        }
    }), 200