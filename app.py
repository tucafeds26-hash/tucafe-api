from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config.database import db
from models.usuario import Usuario
from models.producto import Producto
from models.pedido import Pedido, ItemPedido, EstadoSeccion
from routes.auth import auth_api
from routes.productos import productos_api
from routes.pedidos import pedidos_api
from routes.chef import chef_api
from routes.admin import admin_api
import threading, time, os

app = Flask(__name__)

app.config['SECRET_KEY'] = 'tucafe-api-secret-2026'

db_url = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:12345@localhost:5432/tucafe')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY']                 = 'tucafe-jwt-secret-2026'
app.config['JWT_ACCESS_TOKEN_EXPIRES']       = False

db.init_app(app)
jwt  = JWTManager(app)
CORS(app)

app.register_blueprint(auth_api,      url_prefix='/api/v1/auth')
app.register_blueprint(productos_api, url_prefix='/api/v1/productos')
app.register_blueprint(pedidos_api,   url_prefix='/api/v1/pedidos')
app.register_blueprint(chef_api,      url_prefix='/api/v1/chef')
app.register_blueprint(admin_api,     url_prefix='/api/v1/admin')

@app.route('/')
def index():
    return jsonify({
        'nombre':    'TU CAFE API',
        'version':   'v1.0',
        'endpoints': {
            'auth':      '/api/v1/auth',
            'productos': '/api/v1/productos',
            'pedidos':   '/api/v1/pedidos',
            'chef':      '/api/v1/chef',
            'admin':     '/api/v1/admin',
        }
    }), 200

def job_calidad():
    from datetime import datetime
    while True:
        time.sleep(60)
        try:
            with app.app_context():
                ahora    = datetime.now().time()
                vencidos = Pedido.query.filter(
                    Pedido.hora_recoger != None,
                    Pedido.hora_recoger < ahora,
                    Pedido.estado.in_(['pendiente', 'en_preparacion', 'preparado'])
                ).count()
                if vencidos > 0:
                    print(f'[calidad] {vencidos} pedidos pasaron su hora de recoger')
        except Exception as e:
            print(f'[job_calidad] Error: {e}')

hilo = threading.Thread(target=job_calidad, daemon=True)
hilo.start()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)