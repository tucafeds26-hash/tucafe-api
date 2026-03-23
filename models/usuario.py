from config.database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    password    = db.Column(db.String(255), nullable=False)
    rol         = db.Column(db.String(20), default='cliente')
    seccion     = db.Column(db.String(50), nullable=True)
    verificado  = db.Column(db.Boolean, default=False)
    codigo_ver  = db.Column(db.String(6), nullable=True)
    creado_en   = db.Column(db.DateTime, default=datetime.utcnow)
    pedidos     = db.relationship('Pedido', backref='cliente', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def to_dict(self):
        return {
            'id':         self.id,
            'nombre':     self.nombre,
            'email':      self.email,
            'rol':        self.rol,
            'seccion':    self.seccion,
            'verificado': self.verificado,
            'creado_en':  self.creado_en.isoformat(),
        }