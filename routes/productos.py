from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models.producto import Producto

productos_api = Blueprint('productos_api', __name__)

@productos_api.route('/', methods=['GET'])
def lista_productos():
    categoria = request.args.get('categoria')
    q         = request.args.get('q', '').strip()
    query     = Producto.query.filter_by(disponible=True)
    if categoria:
        query = query.filter_by(categoria=categoria)
    if q:
        query = query.filter(Producto.nombre.ilike(f'%{q}%'))
    productos = query.order_by(Producto.categoria, Producto.nombre).all()
    return jsonify({
        'ok':       True,
        'total':    len(productos),
        'productos': [p.to_dict() for p in productos],
    }), 200

@productos_api.route('/<int:prod_id>', methods=['GET'])
def detalle_producto(prod_id):
    producto = Producto.query.get_or_404(prod_id)
    return jsonify({'ok': True, 'producto': producto.to_dict()}), 200

@productos_api.route('/categorias', methods=['GET'])
def categorias():
    return jsonify({
        'ok':        True,
        'categorias': ['hamburguesas', 'pizza', 'tacos', 'sushi', 'postres'],
    }), 200