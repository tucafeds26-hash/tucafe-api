from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Pedido, DetallePedido, Producto
from extensions import db
from datetime import datetime

pedidos_bp = Blueprint('pedidos', __name__)

@pedidos_bp.route('/crear', methods=['POST'])
@jwt_required()
def crear_pedido():
    try:
        data = request.get_json()
        identity = get_jwt_identity()

        usuario_id = identity["id"]  # ✅ ahora correcto

        items = data.get('items', [])
        hora = data.get('hora')

        if not items:
            return jsonify({"msg": "No hay items"}), 400

        nuevo_pedido = Pedido(
            usuario_id=usuario_id,
            hora=hora,
            fecha=datetime.now()
        )

        db.session.add(nuevo_pedido)
        db.session.flush()

        for item in items:
            producto = Producto.query.get(item['producto_id'])

            if not producto:
                return jsonify({"msg": "Producto no existe"}), 404

            detalle = DetallePedido(
                pedido_id=nuevo_pedido.id,
                producto_id=producto.id,
                cantidad=item['cantidad']
            )

            db.session.add(detalle)

        db.session.commit()

        return jsonify({"msg": "Pedido creado"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500