from flask import Blueprint, request, jsonify
from config.database import db
from models.pedido import Pedido
from models.detalle_pedido import DetallePedido

pedidos_api = Blueprint('pedidos_api', __name__)

@pedidos_api.route('/', methods=['POST'])
def crear_pedido():
    data = request.get_json()

    items = data.get('items', [])
    hora = data.get('hora')

    if not items:
        return jsonify({"msg": "No hay items"}), 400

    nuevo_pedido = Pedido(
        hora_recoger=hora,
        estado='pendiente'
    )

    db.session.add(nuevo_pedido)
    db.session.commit()

    for item in items:
        detalle = DetallePedido(
            pedido_id=nuevo_pedido.id,
            producto_id=item['producto_id'],
            cantidad=item['cantidad']
        )
        db.session.add(detalle)

    db.session.commit()

    return jsonify({
        "msg": "Pedido creado",
        "pedido_id": nuevo_pedido.id
    }), 201