from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config.database import db
from models.usuario import Usuario
import random, string

auth_api = Blueprint('auth_api', __name__)

@auth_api.route('/registro', methods=['POST'])
def registro():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('nombre'):
        return jsonify({'error': 'Faltan campos requeridos'}), 400
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El email ya esta registrado'}), 409
    usuario = Usuario(
        nombre = data['nombre'],
        email  = data['email'],
        rol    = 'cliente',
    )
    usuario.set_password(data['password'])
    db.session.add(usuario)
    db.session.commit()
    return jsonify({'ok': True, 'mensaje': 'Usuario creado correctamente'}), 201

@auth_api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email y password requeridos'}), 400
    usuario = Usuario.query.filter_by(email=data['email']).first()
    if not usuario or not usuario.check_password(data['password']):
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    token = create_access_token(identity=str(usuario.id))
    return jsonify({
        'ok':     True,
        'token':  token,
        'usuario': usuario.to_dict(),
    }), 200

@auth_api.route('/me', methods=['GET'])
@jwt_required()
def me():
    usuario_id = get_jwt_identity()
    usuario  = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({'ok': True, 'usuario': usuario.to_dict()}), 200
@auth_api.route('/verificar', methods=['POST'])
def verificar():
    data    = request.get_json()
    email   = data.get('email', '').strip()
    codigo  = data.get('codigo', '').strip()
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if usuario.codigo_ver != codigo:
        return jsonify({'error': 'Codigo incorrecto'}), 400
    usuario.verificado = True
    usuario.codigo_ver = None
    db.session.commit()
    token = create_access_token(identity=str(usuario.id))
    return jsonify({'ok': True, 'token': token, 'usuario': usuario.to_dict()}), 200