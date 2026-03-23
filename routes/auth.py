from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from models import Usuario
from extensions import db
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    correo = data.get('correo')
    password = data.get('password')

    usuario = Usuario.query.filter_by(correo=correo).first()

    if not usuario or not check_password_hash(usuario.password, password):
        return jsonify({"msg": "Credenciales incorrectas"}), 401

    # ✅ IMPORTANTE: ahora identity es un dict
    access_token = create_access_token(identity={
        "id": usuario.id,
        "rol": usuario.rol
    })

    return jsonify(access_token=access_token), 200