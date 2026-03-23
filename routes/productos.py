from flask import Blueprint, jsonify
from models.producto import Producto

productos_api = Blueprint('productos_api', __name__)

@productos_api.route('/', methods=['GET'])
def obtener_productos():
    productos = Producto.query.all()

    return jsonify([
        {
            "id": p.id,
            "nombre": p.nombre,
            "precio": p.precio
        }
        for p in productos
    ])