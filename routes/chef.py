from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.database import db
from models.pedido import Pedido, ItemPedido, EstadoSeccion
from models.producto import Producto
from datetime import datetime

chef_api = Blueprint('chef_api', __name__)

def verificar_chef(identity):
    return identity.get('rol') in ('chef', 'admin')

@chef_api.route('/comandas', methods=['GET'])
@jwt_required()
def comandas():
    identity = get_jwt_identity()
    if not verificar_chef(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    seccion = identity.get('seccion')
    pedidos_seccion = (
        Pedido.query
        .join(ItemPedido)
        .join(Producto)
        .filter(Producto.categoria == seccion)
        .filter(Pedido.estado.in_(['pendiente', 'en_preparacion']))
        .filter(Pedido.archivado == False)
        .order_by(Pedido.creado_en.asc())
        .distinct()
        .all()
    )
    resultado = []
    for pedido in pedidos_seccion:
        est = EstadoSeccion.query.filter_by(pedido_id=pedido.id, seccion=seccion).first()
        if est and est.estado in ('pendiente', 'en_preparacion'):
            d = pedido.to_dict()
            d['estado_seccion'] = est.estado
            d['items'] = [i.to_dict() for i in pedido.items if i.producto and i.producto.categoria == seccion]
            resultado.append(d)
    return jsonify({'ok': True, 'comandas': resultado}), 200

@chef_api.route('/comandas/count', methods=['GET'])
@jwt_required()
def count():
    identity = get_jwt_identity()
    if not verificar_chef(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    seccion = identity.get('seccion')
    n = EstadoSeccion.query.filter_by(seccion=seccion).filter(
        EstadoSeccion.estado.in_(['pendiente', 'en_preparacion'])
    ).count()
    return jsonify({'ok': True, 'count': n}), 200

@chef_api.route('/comandas/<int:pedido_id>/preparar', methods=['POST'])
@jwt_required()
def preparar(pedido_id):
    identity = get_jwt_identity()
    if not verificar_chef(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    seccion = identity.get('seccion')
    est = EstadoSeccion.query.filter_by(pedido_id=pedido_id, seccion=seccion).first()
    if not est:
        return jsonify({'error': 'No encontrado'}), 404
    est.estado = 'en_preparacion'
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.estado = 'en_preparacion'
    db.session.commit()
    return jsonify({'ok': True, 'estado': est.estado}), 200

@chef_api.route('/comandas/<int:pedido_id>/listo', methods=['POST'])
@jwt_required()
def listo(pedido_id):
    identity = get_jwt_identity()
    if not verificar_chef(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    seccion = identity.get('seccion')
    est = EstadoSeccion.query.filter_by(pedido_id=pedido_id, seccion=seccion).first()
    if not est:
        return jsonify({'error': 'No encontrado'}), 404
    est.estado       = 'preparado'
    est.notificacion = True
    est.listo_en     = datetime.utcnow()
    pedido = Pedido.query.get_or_404(pedido_id)
    if all(e.estado == 'preparado' for e in pedido.estados):
        pedido.estado       = 'preparado'
        pedido.notificacion = True
    db.session.commit()
    return jsonify({'ok': True, 'estado': est.estado}), 200

@chef_api.route('/escanear/<int:pedido_id>/entregar', methods=['POST'])
@jwt_required()
def entregar(pedido_id):
    identity = get_jwt_identity()
    if not verificar_chef(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    pedido = Pedido.query.get_or_404(pedido_id)
    if not pedido.pagado:
        return jsonify({'error': 'El pedido no esta pagado'}), 400
    seccion = identity.get('seccion')
    est = EstadoSeccion.query.filter_by(pedido_id=pedido_id, seccion=seccion).first()
    if not est:
        return jsonify({'error': 'No encontrado'}), 404
    est.estado       = 'entregado'
    est.notificacion = False
    if all(e.estado == 'entregado' for e in pedido.estados):
        pedido.estado       = 'entregado'
        pedido.notificacion = False
    db.session.commit()
    return jsonify({'ok': True}), 200