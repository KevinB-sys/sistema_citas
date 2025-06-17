from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime, timedelta, date
import os
from functools import wraps
import threading
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Lock para operaciones concurrentes
appointment_lock = threading.Lock()

# Modelos de la base de datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    fecha_nacimiento = db.Column(db.Date)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relación con citas
    citas = db.relationship('Cita', backref='paciente', lazy=True)

class Especialidad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    
    # Relación con médicos
    medicos = db.relationship('Medico', backref='especialidad', lazy=True)

class Medico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidad.id'), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    horario_inicio = db.Column(db.Time, default=datetime.strptime('08:00', '%H:%M').time())
    horario_fin = db.Column(db.Time, default=datetime.strptime('17:00', '%H:%M').time())
    duracion_cita = db.Column(db.Integer, default=30)  # minutos
    activo = db.Column(db.Boolean, default=True)
    
    # Relación con citas
    citas = db.relationship('Cita', backref='medico', lazy=True)

class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medico.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.Text)
    estado = db.Column(db.String(20), default='programada')  # programada, completada, cancelada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    notas = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorador para limitar concurrencia
def with_lock(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with appointment_lock:
            return func(*args, **kwargs)
    return wrapper

# Rutas principales
@app.route('/')
def index():
    especialidades = Especialidad.query.all()
    return render_template('index.html', especialidades=especialidades)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() or request.form
        
        # Validar datos
        email = data.get('email')
        password = data.get('password')
        nombre = data.get('nombre')
        telefono = data.get('telefono')
        fecha_nacimiento_str = data.get('fecha_nacimiento')
        
        if not all([email, password, nombre]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'El email ya está registrado'}), 400
        
        # Crear nuevo usuario
        password_hash = generate_password_hash(password)
        fecha_nacimiento = None
        if fecha_nacimiento_str:
            try:
                fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        user = User(
            email=email,
            password_hash=password_hash,
            nombre=nombre,
            telefono=telefono,
            fecha_nacimiento=fecha_nacimiento
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            
            if request.is_json:
                return jsonify({'message': 'Usuario registrado exitosamente', 'redirect': url_for('dashboard')})
            else:
                flash('Usuario registrado exitosamente', 'success')
                return redirect(url_for('dashboard'))
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Error al registrar usuario'}), 500
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if request.is_json:
                return jsonify({'message': 'Login exitoso', 'redirect': url_for('dashboard')})
            else:
                return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'error': 'Credenciales inválidas'}), 401
            else:
                flash('Credenciales inválidas', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Obtener citas del usuario
    citas = Cita.query.filter_by(paciente_id=current_user.id)\
                     .order_by(Cita.fecha_hora.desc()).limit(5).all()
    
    # Obtener especialidades para búsqueda rápida
    especialidades = Especialidad.query.all()
    
    return render_template('dashboard.html', citas=citas, especialidades=especialidades)

@app.route('/buscar-horarios')
@login_required
def buscar_horarios():
    medico_id = request.args.get('medico_id')
    fecha_str = request.args.get('fecha')

    if not medico_id or not fecha_str:
        return jsonify({'horarios': []})

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        medico = Medico.query.get(medico_id)
        if not medico:
            return jsonify({'horarios': []})

        horarios = get_horarios_disponibles(medico, fecha)
        return jsonify({'horarios': horarios})
    except Exception:
        return jsonify({'horarios': []})

@app.route('/agendar-cita', methods=['GET'])
@login_required
def agendar_cita_form():
    min_date = date.today().isoformat()
    return render_template('agendar_cita.html', min_date=min_date)

@app.route('/buscar-medicos')
@login_required
def buscar_medicos():
    especialidad_id = request.args.get('especialidad_id')
    fecha = request.args.get('fecha')
    
    query = Medico.query.filter_by(activo=True)
    
    if especialidad_id:
        query = query.filter_by(especialidad_id=especialidad_id)
    
    medicos = query.all()
    
    # Si se especifica una fecha, calcular disponibilidad
    medicos_disponibles = []
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            for medico in medicos:
                horarios_disponibles = get_horarios_disponibles(medico, fecha_obj)
                if horarios_disponibles:
                    medicos_disponibles.append({
                        'medico': medico,
                        'horarios': horarios_disponibles
                    })
        except ValueError:
            medicos_disponibles = [{'medico': m, 'horarios': []} for m in medicos]
    else:
        medicos_disponibles = [{'medico': m, 'horarios': []} for m in medicos]
    
    especialidades = Especialidad.query.all()
    
    return render_template('buscar_medicos.html', 
                         medicos_disponibles=medicos_disponibles,
                         especialidades=especialidades,
                         especialidad_seleccionada=especialidad_id,
                         fecha_seleccionada=fecha)

def get_horarios_disponibles(medico, fecha):
    """Obtener horarios disponibles para un médico en una fecha específica"""
    if fecha < datetime.now().date():
        return []
    
    # Obtener citas existentes para ese día
    citas_existentes = Cita.query.filter(
        Cita.medico_id == medico.id,
        db.func.date(Cita.fecha_hora) == fecha,
        Cita.estado == 'programada'
    ).all()
    
    # Generar horarios posibles
    horarios_ocupados = [cita.fecha_hora.time() for cita in citas_existentes]
    horarios_disponibles = []
    
    hora_actual = medico.horario_inicio
    while hora_actual < medico.horario_fin:
        if hora_actual not in horarios_ocupados:
            horarios_disponibles.append(hora_actual.strftime('%H:%M'))
        
        # Incrementar por duración de cita
        tiempo_actual = datetime.combine(fecha, hora_actual)
        tiempo_siguiente = tiempo_actual + timedelta(minutes=medico.duracion_cita)
        hora_actual = tiempo_siguiente.time()
    
    return horarios_disponibles

@app.route('/agendar-cita', methods=['POST'])
@login_required
@with_lock
def agendar_cita():
    data = request.get_json() or request.form
    
    medico_id = data.get('medico_id')
    fecha = data.get('fecha')
    hora = data.get('hora')
    motivo = data.get('motivo', '')
    
    if not all([medico_id, fecha, hora]):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400
    
    try:
        # Verificar que el médico existe
        medico = Medico.query.get(medico_id)
        if not medico or not medico.activo:
            return jsonify({'error': 'Médico no disponible'}), 400
        
        # Crear fecha y hora de la cita
        fecha_hora = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
        
        # Verificar que la fecha/hora está disponible
        cita_existente = Cita.query.filter(
            Cita.medico_id == medico_id,
            Cita.fecha_hora == fecha_hora,
            Cita.estado == 'programada'
        ).first()
        
        if cita_existente:
            return jsonify({'error': 'El horario ya está ocupado'}), 400
        
        # Crear nueva cita
        nueva_cita = Cita(
            paciente_id=current_user.id,
            medico_id=medico_id,
            fecha_hora=fecha_hora,
            motivo=motivo
        )
        
        db.session.add(nueva_cita)
        db.session.commit()
        
        return jsonify({
            'message': 'Cita agendada exitosamente',
            'cita_id': nueva_cita.id,
            'redirect': url_for('mis_citas')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al agendar la cita'}), 500

# @app.route('/mis-citas')
# @login_required
# def mis_citas():
#     citas = Cita.query.filter_by(paciente_id=current_user.id)\
#                      .order_by(Cita.fecha_hora.desc()).all()
#     return render_template('mis_citas.html', citas=citas)
@app.route('/mis-citas-json')
@login_required
def mis_citas_json():
    citas = Cita.query.filter_by(paciente_id=current_user.id).order_by(Cita.fecha_hora.desc()).all()

    citas_lista = []
    for cita in citas:
        citas_lista.append({
            'id': cita.id,
            'medico_nombre': cita.medico.nombre,
            'fecha_hora': cita.fecha_hora.strftime('%Y-%m-%d %H:%M'),
            'motivo': cita.motivo,
            'estado': cita.estado,
        })

    return jsonify({'citas': citas_lista})

@app.route('/mis-citas')
@login_required
def mis_citas():
    return render_template('mis_citas.html')

@app.route('/cancelar-cita/<int:cita_id>', methods=['POST'])
@login_required
def cancelar_cita(cita_id):
    cita = Cita.query.get_or_404(cita_id)
    
    if cita.paciente_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    
    if cita.fecha_hora < datetime.now():
        return jsonify({'error': 'No se puede cancelar una cita pasada'}), 400
    
    cita.estado = 'cancelada'
    db.session.commit()
    
    return jsonify({'message': 'Cita cancelada exitosamente'})

# API endpoints para obtener datos
@app.route('/api/especialidades')
def api_especialidades():
    especialidades = Especialidad.query.all()
    return jsonify([{
        'id': e.id,
        'nombre': e.nombre,
        'descripcion': e.descripcion
    } for e in especialidades])

@app.route('/api/medicos/<int:especialidad_id>')
def api_medicos_especialidad(especialidad_id):
    medicos = Medico.query.filter_by(especialidad_id=especialidad_id, activo=True).all()
    return jsonify([{
        'id': m.id,
        'nombre': m.nombre,
        'telefono': m.telefono,
        'email': m.email
    } for m in medicos])

# Función para inicializar datos de prueba
def init_db():
    with app.app_context():
        db.create_all()
        
        # Crear especialidades si no existen
        if not Especialidad.query.first():
            especialidades = [
                Especialidad(nombre='Medicina General', descripcion='Atención médica general'),
                Especialidad(nombre='Cardiología', descripcion='Especialista en corazón'),
                Especialidad(nombre='Dermatología', descripcion='Especialista en piel'),
                Especialidad(nombre='Neurología', descripcion='Especialista en sistema nervioso'),
                Especialidad(nombre='Pediatría', descripcion='Especialista en niños'),
                Especialidad(nombre='Ginecología', descripcion='Especialista en salud femenina'),
                Especialidad(nombre='Ortopedia', descripcion='Especialista en huesos y articulaciones'),
                Especialidad(nombre='Psicología', descripcion='Especialista en salud mental')
            ]
            
            for esp in especialidades:
                db.session.add(esp)
            
            # Crear médicos de prueba
            medicos = [
                Medico(nombre='Dr. Juan Pérez', cedula='1234567890', especialidad_id=1, telefono='555-0001', email='juan.perez@hospital.com'),
                Medico(nombre='Dra. María García', cedula='1234567891', especialidad_id=2, telefono='555-0002', email='maria.garcia@hospital.com'),
                Medico(nombre='Dr. Carlos López', cedula='1234567892', especialidad_id=3, telefono='555-0003', email='carlos.lopez@hospital.com'),
                Medico(nombre='Dra. Ana Martínez', cedula='1234567893', especialidad_id=4, telefono='555-0004', email='ana.martinez@hospital.com'),
                Medico(nombre='Dr. Luis Rodríguez', cedula='1234567894', especialidad_id=5, telefono='555-0005', email='luis.rodriguez@hospital.com'),
            ]
            
            for medico in medicos:
                db.session.add(medico)
            
            db.session.commit()
            print("Base de datos inicializada con datos de prueba")

if __name__ == '__main__':
    init_db()
    # Para producción usar gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:app
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)