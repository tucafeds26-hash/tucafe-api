from config.database import db
from datetime import datetime

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id           = db.Column(db.Integer, primary_key=True)
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    total        = db.Column(db.Numeric(10, 2), default=0)
    estado       = db.Column(db.String(20), default='pendiente')
    pagado       = db.Column(db.Boolean, default=False)
    notas        = db.Column(db.Text, nullable=True)
    metodo_pago  = db.Column(db.String(20), default='efectivo')
    notificacion = db.Column(db.Boolean, default=False)
    hora_recoger = db.Column(db.Time, nullable=True)
    archivado    = db.Column(db.Boolean, default=False)
    creado_en    = db.Column(db.DateTime, default=datetime.utcnow)
    items        = db.relationship('ItemPedido', backref='pedido', lazy=True)
    estados      = db.relationship('EstadoSeccion', backref='pedido', lazy=True)

    def to_dict(self):
        return {
            'id':           self.id,
            'usuario_id':   self.usuario_id,
            'total':        float(self.total),
            'estado':       self.estado,
            'pagado':       self.pagado,
            'notas':        self.notas,
            'metodo_pago':  self.metodo_pago,
            'notificacion': self.notificacion,
            'hora_recoger': self.hora_recoger.strftime('%H:%M') if self.hora_recoger else None,
            'archivado':    self.archivado,
            'creado_en':    self.creado_en.isoformat(),
            'items':        [i.to_dict() for i in self.items],
        }

class ItemPedido(db.Model):
    __tablename__ = 'items_pedido'
    id          = db.Column(db.Integer, primary_key=True)
    pedido_id   = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=True)
    cantidad    = db.Column(db.Integer, nullable=False)
    precio_unit = db.Column(db.Numeric(10, 2), nullable=False)
    producto    = db.relationship('Producto', foreign_keys=[producto_id], lazy=True)

    def subtotal(self):
        return float(self.precio_unit) * self.cantidad

    def to_dict(self):
        return {
            'id':          self.id,
            'producto_id': self.producto_id,
            'cantidad':    self.cantidad,
            'precio_unit': float(self.precio_unit),
            'subtotal':    self.subtotal(),
            'producto':    self.producto.to_dict() if self.producto else None,
        }

class EstadoSeccion(db.Model):
    __tablename__ = 'estados_seccion'
    id           = db.Column(db.Integer, primary_key=True)
    pedido_id    = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    seccion      = db.Column(db.String(50), nullable=False)
    estado       = db.Column(db.String(20), default='pendiente')
    notificacion = db.Column(db.Boolean, default=False)
    listo_en     = db.Column(db.DateTime, nullable=True)
    creado_en    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'pedido_id':    self.pedido_id,
            'seccion':      self.seccion,
            'estado':       self.estado,
            'notificacion': self.notificacion,
            'listo_en':     self.listo_en.isoformat() if self.listo_en else None,
        }