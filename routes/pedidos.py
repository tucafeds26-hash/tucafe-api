from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.database import db
from models.pedido import Pedido, ItemPedido, EstadoSeccion
from models.producto import Producto
from datetime import datetime, timedelta, time
import qrcode, io, base64
import pytz

pedidos_api = Blueprint('pedidos_api', __name__)

def generar_qr_base64(pedido_id):
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(str(pedido_id))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def crear_estados_seccion(pedido):
    secciones = set()
    for item in pedido.items:
        if item.producto:
            secciones.add(item.producto.categoria)
    for seccion in secciones:
        est = EstadoSeccion(pedido_id=pedido.id, seccion=seccion, estado='pendiente')
        db.session.add(est)

def generar_horas_recoger():
    from datetime import datetime, timedelta, time as dtime
    tz_mexico   = pytz.timezone('America/Mexico_City')
    ahora       = datetime.now(tz_mexico).replace(tzinfo=None)
    minimo      = ahora + timedelta(minutes=20)
    hora_actual = ahora.hour

    if hora_actual < 15:
        turno_inicio = datetime.combine(ahora.date(), dtime(8, 0))
        turno_fin    = datetime.combine(ahora.date(), dtime(14, 0))
        turno_nombre = 'Matutino'
    else:
        turno_inicio = datetime.combine(ahora.date(), dtime(15, 0))
        turno_fin    = datetime.combine(ahora.date(), dtime(20, 0))
        turno_nombre = 'Vespertino'

    slots = []
    t = turno_inicio
    while t <= turno_fin:
        if t >= minimo:
            slots.append(t.strftime('%H:%M'))
        t += timedelta(minutes=15)

    return slots, turno_nombre

@pedidos_api.route('/', methods=['GET'])
@jwt_required()
def mis_pedidos():
    identity = get_jwt_identity()
    pedidos  = Pedido.query.filter_by(
        usuario_id=identity['id'], archivado=False
    ).order_by(Pedido.creado_en.desc()).all()
    activos = [p for p in pedidos if p.estado not in ('entregado',)]
    return jsonify({
        'ok':      True,
        'activos': [p.to_dict() for p in activos],
    }), 200

@pedidos_api.route('/horas', methods=['GET'])
@jwt_required()
def horas_disponibles():
    slots, turno = generar_horas_recoger()
    return jsonify({'ok': True, 'turno': turno, 'horas': slots}), 200

@pedidos_api.route('/notificaciones', methods=['GET'])
@jwt_required()
def check_notificaciones():
    identity = get_jwt_identity()
    pedidos  = Pedido.query.filter_by(usuario_id=identity['id'], archivado=False).all()
    listos   = [p.to_dict() for p in pedidos if any(e.notificacion for e in p.estados)]
    return jsonify({'ok': True, 'tiene': len(listos) > 0, 'pedidos': listos}), 200

@pedidos_api.route('/crear', methods=['POST'])
@jwt_required()
def crear_pedido():
    identity = get_jwt_identity()
    data     = request.get_json()
    if not data or not data.get('items'):
        return jsonify({'error': 'Se requieren items'}), 400

    hora_recoger = None
    if data.get('hora_recoger'):
        try:
            hora_recoger = datetime.strptime(data['hora_recoger'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Hora de recoger invalida'}), 400

    pedido = Pedido(
        usuario_id   = identity['id'],
        notas        = data.get('notas', ''),
        metodo_pago  = data.get('metodo_pago', 'efectivo'),
        hora_recoger = hora_recoger,
        estado       = 'pendiente',
    )
    db.session.add(pedido)
    db.session.flush()

    total = 0
    for it in data['items']:
        producto = Producto.query.get(it['producto_id'])
        if not producto or not producto.disponible:
            continue
        item = ItemPedido(
            pedido_id   = pedido.id,
            producto_id = producto.id,
            cantidad    = it['cantidad'],
            precio_unit = producto.precio,
        )
        db.session.add(item)
        total += float(producto.precio) * it['cantidad']

    pedido.total = total
    db.session.flush()
    crear_estados_seccion(pedido)
    db.session.commit()

    qr_b64 = generar_qr_base64(pedido.id)
    return jsonify({
        'ok':     True,
        'pedido': pedido.to_dict(),
        'qr':     qr_b64,
    }), 201

@pedidos_api.route('/<int:pedido_id>', methods=['GET'])
@jwt_required()
def detalle_pedido(pedido_id):
    identity = get_jwt_identity()
    pedido   = Pedido.query.get_or_404(pedido_id)
    if pedido.usuario_id != identity['id'] and identity['rol'] not in ('admin', 'chef'):
        return jsonify({'error': 'Sin permiso'}), 403
    qr_b64 = generar_qr_base64(pedido.id)
    return jsonify({'ok': True, 'pedido': pedido.to_dict(), 'qr': qr_b64}), 200

@pedidos_api.route('/<int:pedido_id>/pagar', methods=['POST'])
@jwt_required()
def pagar_pedido(pedido_id):
    identity = get_jwt_identity()
    if identity.get('rol') not in ('admin', 'chef'):
        return jsonify({'error': 'Sin permiso'}), 403
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.pagado = True
    db.session.commit()
    return jsonify({'ok': True}), 200

@pedidos_api.route('/<int:pedido_id>/entregar', methods=['POST'])
@jwt_required()
def entregar_pedido(pedido_id):
    identity = get_jwt_identity()
    if identity.get('rol') not in ('admin', 'chef'):
        return jsonify({'error': 'Sin permiso'}), 403
    pedido = Pedido.query.get_or_404(pedido_id)
    if not pedido.pagado:
        return jsonify({'error': 'El pedido no esta pagado'}), 400
    pedido.estado       = 'entregado'
    pedido.notificacion = False
    for est in pedido.estados:
        est.estado       = 'entregado'
        est.notificacion = False
    db.session.commit()
    return jsonify({'ok': True}), 200

@pedidos_api.route('/<int:pedido_id>/entregar_seccion', methods=['POST'])
@jwt_required()
def entregar_seccion_api(pedido_id):
    identity = get_jwt_identity()
    if identity.get('rol') not in ('admin', 'chef'):
        return jsonify({'error': 'Sin permiso'}), 403
    pedido  = Pedido.query.get_or_404(pedido_id)
    if not pedido.pagado:
        return jsonify({'error': 'El pedido no esta pagado'}), 400
    seccion = identity.get('seccion')
    est     = EstadoSeccion.query.filter_by(pedido_id=pedido_id, seccion=seccion).first()
    if not est:
        return jsonify({'error': 'No encontrado'}), 404
    est.estado       = 'entregado'
    est.notificacion = False
    if all(e.estado == 'entregado' for e in pedido.estados):
        pedido.estado       = 'entregado'
        pedido.notificacion = False
    db.session.commit()
    return jsonify({'ok': True}), 200

@pedidos_api.route('/<int:pedido_id>/notificacion/vista', methods=['POST'])
@jwt_required()
def notificacion_vista(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    for est in pedido.estados:
        est.notificacion = False
    pedido.notificacion = False
    db.session.commit()
    return jsonify({'ok': True}), 200

@pedidos_api.route('/<int:pedido_id>/abandonado', methods=['POST'])
@jwt_required()
def abandonar_pedido(pedido_id):
    identity = get_jwt_identity()
    pedido   = Pedido.query.get_or_404(pedido_id)
    if pedido.usuario_id != identity['id']:
        return jsonify({'error': 'Sin permiso'}), 403
    pedido.notificacion = False
    for est in pedido.estados:
        est.notificacion = False
    db.session.commit()
    return jsonify({'ok': True}), 200