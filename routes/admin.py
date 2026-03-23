from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.database import db
from models.pedido import Pedido, ItemPedido, EstadoSeccion
from models.producto import Producto
from models.usuario import Usuario
from datetime import datetime, timedelta, date

admin_api = Blueprint('admin_api', __name__)

def solo_admin(identity):
    return identity.get('rol') == 'admin'

def get_periodo(tipo, fecha_base):
    if tipo == 'semanal':
        inicio = datetime.combine(fecha_base - timedelta(days=fecha_base.weekday()), datetime.min.time())
        fin    = inicio + timedelta(days=7)
    else:
        inicio = datetime.combine(fecha_base, datetime.min.time())
        fin    = inicio + timedelta(days=1)
    return inicio, fin

def calcular_stats(pedidos):
    total_ventas    = sum(float(p.total) for p in pedidos if p.pagado)
    total_efectivo  = sum(float(p.total) for p in pedidos if p.pagado and p.metodo_pago == 'efectivo')
    total_tarjeta   = sum(float(p.total) for p in pedidos if p.pagado and p.metodo_pago == 'tarjeta')
    num_pagados     = sum(1 for p in pedidos if p.pagado)
    num_entregados  = sum(1 for p in pedidos if p.estado == 'entregado')
    ticket_promedio = total_ventas / num_pagados if num_pagados > 0 else 0

    horas = {}
    for p in pedidos:
        h = p.creado_en.hour
        horas[h] = horas.get(h, 0) + 1
    hora_pico = max(horas, key=horas.get) if horas else None

    SECCIONES = ['hamburguesas','pizza','tacos','sushi','postres']
    EMOJIS    = {'hamburguesas':'🍔','pizza':'🍕','tacos':'🌮','sushi':'🍱','postres':'🍰'}
    por_seccion = []
    for sec in SECCIONES:
        items_sec = [i for p in pedidos for i in p.items if i.producto and i.producto.categoria == sec]
        ingresos  = sum(i.subtotal() for i in items_sec if i.pedido.pagado)
        conteo    = {}
        for i in items_sec:
            nombre = i.producto.nombre if i.producto else 'N/A'
            conteo[nombre] = conteo.get(nombre, 0) + i.cantidad
        top = max(conteo, key=conteo.get) if conteo else '—'
        por_seccion.append({
            'nombre': sec, 'emoji': EMOJIS[sec],
            'ingresos': ingresos, 'cantidad': len(items_sec), 'top': top,
        })

    return {
        'total_ventas':    total_ventas,
        'total_efectivo':  total_efectivo,
        'total_tarjeta':   total_tarjeta,
        'num_pedidos':     len(pedidos),
        'num_pagados':     num_pagados,
        'num_entregados':  num_entregados,
        'ticket_promedio': ticket_promedio,
        'hora_pico':       hora_pico,
        'por_seccion':     por_seccion,
    }

# ── DASHBOARD ─────────────────────────────────────────────────
@admin_api.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403

    pedidos = Pedido.query.filter_by(archivado=False).order_by(Pedido.creado_en.desc()).all()

    total_ingresos = sum(float(p.total) for p in pedidos if p.pagado)
    por_cobrar     = sum(float(p.total) for p in pedidos if not p.pagado)
    entregados     = sum(1 for p in pedidos if p.estado == 'entregado')
    en_preparacion = sum(1 for p in pedidos if p.estado in ('pendiente','en_preparacion'))

    SECCIONES = ['hamburguesas','pizza','tacos','sushi','postres']
    EMOJIS    = {'hamburguesas':'🍔','pizza':'🍕','tacos':'🌮','sushi':'🍱','postres':'🍰'}
    stats_por_seccion = []
    for sec in SECCIONES:
        items_sec   = [i for p in pedidos for i in p.items if i.producto and i.producto.categoria == sec]
        pedidos_sec = list({i.pedido_id for i in items_sec})
        ingresos    = sum(i.subtotal() for i in items_sec if i.pedido.pagado)
        stats_por_seccion.append({
            'nombre': sec, 'emoji': EMOJIS[sec],
            'pedidos': len(pedidos_sec), 'ingresos': ingresos,
        })

    pedidos_dict = []
    for p in pedidos[:20]:
        d = p.to_dict()
        d['cliente_nombre'] = p.cliente.nombre if p.cliente else 'N/A'
        pedidos_dict.append(d)

    return jsonify({
        'ok':               True,
        'pedidos':          pedidos_dict,
        'total_ingresos':   total_ingresos,
        'por_cobrar':       por_cobrar,
        'total_pedidos':    len(pedidos),
        'pagados':          sum(1 for p in pedidos if p.pagado),
        'entregados':       entregados,
        'en_preparacion':   en_preparacion,
        'stats_por_seccion': stats_por_seccion,
    }), 200

# ── CORTE ─────────────────────────────────────────────────────
@admin_api.route('/corte', methods=['GET'])
@jwt_required()
def corte():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403

    tipo      = request.args.get('tipo', 'diario')
    fecha_str = request.args.get('fecha', date.today().isoformat())
    try:
        fecha_base = date.fromisoformat(fecha_str)
    except:
        fecha_base = date.today()

    inicio, fin = get_periodo(tipo, fecha_base)
    pedidos = Pedido.query.filter(
        Pedido.creado_en >= inicio,
        Pedido.creado_en < fin
    ).order_by(Pedido.creado_en.asc()).all()

    stats         = calcular_stats(pedidos)
    ya_archivados = all(p.archivado for p in pedidos) if pedidos else False

    pedidos_dict = []
    for p in pedidos:
        d = p.to_dict()
        d['cliente_nombre'] = p.cliente.nombre if p.cliente else 'N/A'
        pedidos_dict.append(d)

    return jsonify({
        'ok':           True,
        'pedidos':      pedidos_dict,
        'stats':        stats,
        'ya_archivados': ya_archivados,
    }), 200

@admin_api.route('/corte/cerrar', methods=['POST'])
@jwt_required()
def cerrar_corte():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403

    data      = request.get_json()
    tipo      = data.get('tipo', 'diario')
    fecha_str = data.get('fecha', date.today().isoformat())
    try:
        fecha_base = date.fromisoformat(fecha_str)
    except:
        fecha_base = date.today()

    inicio, fin = get_periodo(tipo, fecha_base)
    pedidos = Pedido.query.filter(
        Pedido.creado_en >= inicio,
        Pedido.creado_en < fin,
        Pedido.archivado == False
    ).all()

    count = len(pedidos)
    for p in pedidos:
        p.archivado = True
    db.session.commit()

    return jsonify({'ok': True, 'count': count}), 200

# ── PEDIDOS ───────────────────────────────────────────────────
@admin_api.route('/pedidos', methods=['GET'])
@jwt_required()
def pedidos():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403

    filtro = request.args.get('filtro', 'all')
    query  = Pedido.query.filter_by(archivado=False)
    if filtro == 'no_pagado':
        query = query.filter_by(pagado=False)
    elif filtro == 'abandonado':
        query = query.filter_by(estado='abandonado')
    elif filtro in ('hamburguesas','pizza','tacos','sushi','postres'):
        query = query.join(ItemPedido).join(Producto).filter(Producto.categoria == filtro)
    todos = query.order_by(Pedido.creado_en.desc()).all()

    pedidos_dict = []
    for p in todos:
        d = p.to_dict()
        d['cliente_nombre'] = p.cliente.nombre if p.cliente else 'N/A'
        pedidos_dict.append(d)

    return jsonify({'ok': True, 'pedidos': pedidos_dict}), 200

@admin_api.route('/pedidos/<int:pedido_id>/toggle-pago', methods=['POST'])
@jwt_required()
def toggle_pago(pedido_id):
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.pagado = not pedido.pagado
    db.session.commit()
    return jsonify({'ok': True, 'pagado': pedido.pagado}), 200

# ── PRODUCTOS ─────────────────────────────────────────────────
@admin_api.route('/productos', methods=['GET'])
@jwt_required()
def lista_productos_admin():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    todos = Producto.query.order_by(Producto.categoria, Producto.nombre).all()
    return jsonify({'ok': True, 'productos': [p.to_dict() for p in todos]}), 200

@admin_api.route('/productos', methods=['POST'])
@jwt_required()
def crear_producto():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    data = request.get_json()
    p = Producto(
        nombre      = data['nombre'],
        descripcion = data.get('descripcion', ''),
        precio      = float(data['precio']),
        categoria   = data['categoria'],
        emoji       = data.get('emoji', '🍽️'),
        disponible  = data.get('disponible', True),
        imagen      = data.get('imagen'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True, 'producto': p.to_dict()}), 201

@admin_api.route('/productos/<int:prod_id>', methods=['PUT'])
@jwt_required()
def editar_producto(prod_id):
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    producto = Producto.query.get_or_404(prod_id)
    data = request.get_json()
    producto.nombre      = data.get('nombre', producto.nombre)
    producto.descripcion = data.get('descripcion', producto.descripcion)
    producto.precio      = float(data.get('precio', producto.precio))
    producto.categoria   = data.get('categoria', producto.categoria)
    producto.emoji       = data.get('emoji', producto.emoji)
    producto.disponible  = data.get('disponible', producto.disponible)
    if data.get('imagen'):
        producto.imagen = data['imagen']
    db.session.commit()
    return jsonify({'ok': True, 'producto': producto.to_dict()}), 200

@admin_api.route('/productos/<int:prod_id>', methods=['DELETE'])
@jwt_required()
def eliminar_producto(prod_id):
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    producto = Producto.query.get_or_404(prod_id)
    db.session.delete(producto)
    db.session.commit()
    return jsonify({'ok': True}), 200

# ── USUARIOS ──────────────────────────────────────────────────
@admin_api.route('/usuarios', methods=['GET'])
@jwt_required()
def usuarios():
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    todos = Usuario.query.order_by(Usuario.rol, Usuario.nombre).all()
    return jsonify({'ok': True, 'usuarios': [u.to_dict() for u in todos]}), 200

# ── PEDIDOS — endpoints extra para escanear ───────────────────
@admin_api.route('/pedidos/<int:pedido_id>/pagar', methods=['POST'])
@jwt_required()
def pagar_pedido(pedido_id):
    identity = get_jwt_identity()
    if not solo_admin(identity):
        return jsonify({'error': 'Sin permiso'}), 403
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.pagado = True
    db.session.commit()
    return jsonify({'ok': True}), 200