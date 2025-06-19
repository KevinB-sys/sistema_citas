from typing import Dict, List
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime, timedelta, date
import os
from functools import wraps
import threading
from werkzeug.security import generate_password_hash, check_password_hash
from employees_service import EmployeesService  # Importar el nuevo servicio
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['NEST_API_URL'] = os.getenv('NEST_API_URL', 'http://localhost:3000')

# Inicializar extensiones
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Inicializar servicio de empleados
employees_service = EmployeesService(app.config['NEST_API_URL'])

# Lock para operaciones concurrentes
appointment_lock = threading.Lock()

# Modelos actualizados
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

class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medico_id = db.Column(db.String(50), nullable=False)  # Cambiar a String para IDs de NestJS
    fecha_hora = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.Text)
    estado = db.Column(db.String(20), default='programada')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    notas = db.Column(db.Text)
    
    # Propiedades para obtener datos del médico desde NestJS
    @property
    def medico(self):
        """Obtener datos del médico desde el servicio NestJS"""
        return employees_service.get_doctor_by_id(self.medico_id)
    
    @property
    def medico_nombre(self):
        """Obtener nombre del médico"""
        medico = self.medico
        return medico.get('name', 'Médico no encontrado') if medico else 'Médico no encontrado'

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

# Rutas actualizadas
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

@app.route('/agendar-cita', methods=['GET'])
@login_required
def agendar_cita_form():
    min_date = date.today().isoformat()
    return render_template('agendar_cita.html', min_date=min_date)

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

@app.route('/buscar-medicos')
@login_required
def buscar_medicos():
    especialidad = request.args.get('especialidad')
    fecha = request.args.get('fecha')
    
    # Obtener doctores del servicio NestJS
    if especialidad:
        medicos = employees_service.get_doctors_by_specialty(especialidad)
    else:
        medicos = employees_service.get_all_doctors()
    
    # Filtrar solo doctores activos
    medicos = [m for m in medicos if m.get('activo', False)]
    
    # Si se especifica una fecha, calcular disponibilidad
    medicos_disponibles = []
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            for medico in medicos:
                horarios_disponibles = get_horarios_disponibles_nest(medico, fecha_obj)
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
                         especialidad_seleccionada=especialidad,
                         fecha_seleccionada=fecha)

def get_horarios_disponibles_nest(medico_data: Dict, fecha: date) -> List[str]:
    """Obtener horarios disponibles para un médico usando datos de NestJS"""
    if fecha < datetime.now().date():
        return []
    
    # Obtener citas existentes para ese día
    citas_existentes = Cita.query.filter(
        Cita.medico_id == medico_data['id'],
        db.func.date(Cita.fecha_hora) == fecha,
        Cita.estado == 'programada'
    ).all()
    
    # Generar horarios posibles usando datos de NestJS
    horarios_ocupados = [cita.fecha_hora.time() for cita in citas_existentes]
    horarios_disponibles = []
    
    try:
        # Parsear horarios del médico
        horario_inicio = datetime.strptime(medico_data.get('horario_inicio', '08:00'), '%H:%M').time()
        horario_fin = datetime.strptime(medico_data.get('horario_fin', '17:00'), '%H:%M').time()
        duracion_cita = medico_data.get('duracion_cita', 30)
        
        hora_actual = horario_inicio
        while hora_actual < horario_fin:
            if hora_actual not in horarios_ocupados:
                horarios_disponibles.append(hora_actual.strftime('%H:%M'))
            
            # Incrementar por duración de cita
            tiempo_actual = datetime.combine(fecha, hora_actual)
            tiempo_siguiente = tiempo_actual + timedelta(minutes=duracion_cita)
            hora_actual = tiempo_siguiente.time()
    
    except (ValueError, KeyError) as e:
        logging.error(f"Error procesando horarios del médico {medico_data.get('id')}: {e}")
        return []
    
    return horarios_disponibles

@app.route('/buscar-horarios')
@login_required
def buscar_horarios():
    medico_id = request.args.get('medico_id')
    fecha_str = request.args.get('fecha')

    if not medico_id or not fecha_str:
        return jsonify({'horarios': []})

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        medico_data = employees_service.get_doctor_by_id(medico_id)
        
        if not medico_data:
            return jsonify({'horarios': []})

        horarios = get_horarios_disponibles_nest(medico_data, fecha)
        return jsonify({'horarios': horarios})
    except Exception as e:
        logging.error(f"Error buscando horarios: {e}")
        return jsonify({'horarios': []})

@app.route('/agendar-cita', methods=['POST'])
@login_required
@with_lock
def agendar_cita():
    data = request.get_json() or request.form

    medico_id = data.get('medico_id')
    fecha = data.get('fecha')
    hora = data.get('hora')
    motivo = data.get('motivo', '')

    if not medico_id:
        return jsonify({'error': f'{current_user.nombre}: Debe seleccionar un médico para agendar la cita.'}), 400
    if not fecha:
        return jsonify({'error': f'{current_user.nombre}: Debe especificar una fecha para la cita.'}), 400
    if not hora:
        return jsonify({'error': f'{current_user.nombre}: Debe especificar una hora para la cita.'}), 400

    try:
        # Verificar que el médico existe en NestJS
        medico_data = employees_service.get_doctor_by_id(medico_id)
        if not medico_data:
            return jsonify({'error': f'{current_user.nombre}: El médico con ID {medico_id} no existe.'}), 404
        
        if not medico_data.get('activo', False):
            return jsonify({'error': f'{current_user.nombre}: El médico {medico_data.get("name", "desconocido")} no está activo.'}), 400

        # Crear datetime
        try:
            fecha_hora = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
        except ValueError:
            return jsonify({'error': f'{current_user.nombre}: El formato de fecha u hora es inválido.'}), 400

        if fecha_hora < datetime.now():
            return jsonify({'error': f'{current_user.nombre}: No puede agendar una cita en el pasado ({fecha} {hora}).'}), 400

        # Verificar disponibilidad
        cita_existente = Cita.query.filter(
            Cita.medico_id == medico_id,
            Cita.fecha_hora == fecha_hora,
            Cita.estado == 'programada'
        ).first()

        if cita_existente:
            return jsonify({
                'error': f'{current_user.nombre}: El horario {hora} del {fecha} ya está ocupado para el Dr./Dra. {medico_data.get("name", "desconocido")}.',
                'detalle': {
                    'paciente': current_user.nombre,
                    'medico': medico_data.get('name'),
                    'fecha': fecha,
                    'hora': hora
                }
            }), 409

        # Crear nueva cita
        nueva_cita = Cita(
            paciente_id=current_user.id,
            medico_id=medico_id,  # Ahora es String ID de NestJS
            fecha_hora=fecha_hora,
            motivo=motivo
        )

        db.session.add(nueva_cita)
        db.session.commit()

        return jsonify({
            'message': f'Cita agendada exitosamente para {current_user.nombre} con el Dr./Dra. {medico_data.get("name", "desconocido")} el {fecha} a las {hora}.',
            'cita_id': nueva_cita.id,
            'detalle': {
                'paciente': current_user.nombre,
                'medico': medico_data.get('name', 'desconocido'),
                'fecha': fecha,
                'hora': hora,
                'motivo': motivo
            },
            'redirect': url_for('mis_citas')
        })

    except Exception as e:
        db.session.rollback()
        medico_name = medico_data.get('name', 'desconocido') if 'medico_data' in locals() else 'desconocido'
        return jsonify({
            'error': f'{current_user.nombre}: Error interno al agendar la cita con el Dr./Dra. {medico_name} el {fecha} a las {hora}.',
            'detalle': str(e),
            'paciente': current_user.nombre,
            'fecha': fecha,
            'hora': hora
        }), 500

@app.route('/mis-citas-json')
@login_required
def mis_citas_json():
    try:
        app.logger.info(f"Obteniendo citas para usuario {current_user.id}")
        
        # Obtener las citas y loggear cantidad
        citas = Cita.query.filter_by(paciente_id=current_user.id)\
                         .order_by(Cita.fecha_hora.desc()).all()
        app.logger.info(f"Se encontraron {len(citas)} citas")
        
        citas_lista = []
        for cita in citas:
            try:
                app.logger.debug(f"Procesando cita ID: {cita.id}")
                medico_data = employees_service.get_doctor_by_id(cita.medico_id)
                app.logger.debug(f"Datos del médico: {medico_data}")
                
                medico_nombre = medico_data.get('name', 'Médico no encontrado') if medico_data else 'Médico no encontrado'
                
                cita_dict = {
                    'id': cita.id,
                    'medico_nombre': medico_nombre,
                    'fecha_hora': cita.fecha_hora.isoformat(),
                    'motivo': cita.motivo or '',
                    'estado': cita.estado or 'desconocido',
                }
                citas_lista.append(cita_dict)
                app.logger.debug(f"Cita procesada: {cita_dict}")
                
            except Exception as e:
                app.logger.error(f"Error procesando cita {cita.id}: {str(e)}")
                continue

        app.logger.info(f"Retornando {len(citas_lista)} citas procesadas")
        return jsonify({'citas': citas_lista})
        
    except Exception as e:
        app.logger.error(f"Error en mis-citas-json: {str(e)}")
        return jsonify({
            'error': 'Error al obtener las citas',
            'message': str(e)
        }), 500

# API endpoints actualizados
@app.route('/api/especialidades')
def get_especialidades():
    try:
        # Obtener todos los doctores del servicio
        doctores = employees_service.get_all_doctors()
        # Extraer especialidades únicas
        especialidades = list({doc.get('especialidad') for doc in doctores if doc.get('especialidad')})
        return jsonify([{"nombre": esp} for esp in sorted(especialidades)])
    except Exception as e:
        app.logger.error(f"Error al obtener especialidades: {e}")
        return jsonify({"error": "Error al obtener especialidades"}), 500

@app.route('/api/medicos/<especialidad>')
def get_medicos_por_especialidad(especialidad):
    try:
        # Usar el método del servicio para obtener médicos por especialidad
        medicos = employees_service.get_doctors_by_specialty(especialidad)
        return jsonify(medicos)
    except Exception as e:
        app.logger.error(f"Error al obtener médicos por especialidad {especialidad}: {e}")
        return jsonify({"error": f"Error al obtener médicos de {especialidad}"}), 500

# Rutas de administración (mantener las del código original)
@app.route('/admin/cancelar-todas-citas', methods=['POST'])
@login_required
def cancelar_todas_las_citas():
    """
    Ruta para cancelar todas las citas con estado 'programada' en la base de datos.
    Solo debe ser accesible por administradores en un entorno real.
    """
    try:
        # Obtener todas las citas programadas
        citas_programadas = Cita.query.filter_by(estado='programada').all()
        
        if not citas_programadas:
            return jsonify({
                'message': 'No hay citas programadas para cancelar',
                'citas_canceladas': 0
            }), 200
        
        # Contar las citas antes de cancelar
        total_citas = len(citas_programadas)
        
        # Cancelar todas las citas programadas
        Cita.query.filter_by(estado='programada').update({'estado': 'cancelada'})
        
        # Confirmar los cambios
        db.session.commit()
        
        return jsonify({
            'message': f'Se han cancelado exitosamente {total_citas} citas programadas',
            'citas_canceladas': total_citas,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        # Revertir cambios en caso de error
        db.session.rollback()
        return jsonify({
            'error': 'Error interno al cancelar las citas',
            'detalle': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/admin/cancelar-todas-citas-confirmacion', methods=['GET'])
@login_required
def cancelar_todas_citas_confirmacion():
    """
    Ruta GET para mostrar información sobre las citas que se cancelarían
    """
    try:
        # Contar citas programadas
        total_citas = Cita.query.filter_by(estado='programada').count()
        
        # Obtener información detallada de las citas
        citas_info = db.session.query(
            Cita.id,
            User.nombre.label('paciente'),
            Cita.medico_id,
            Cita.fecha_hora,
            Cita.motivo
        ).join(User, Cita.paciente_id == User.id)\
         .filter(Cita.estado == 'programada')\
         .order_by(Cita.fecha_hora).all()
        
        citas_lista = []
        for cita in citas_info:
            # Obtener nombre del médico desde NestJS
            medico_data = employees_service.get_doctor_by_id(cita.medico_id)
            medico_nombre = medico_data.get('name', 'Médico no encontrado') if medico_data else 'Médico no encontrado'
            
            citas_lista.append({
                'id': cita.id,
                'paciente': cita.paciente,
                'medico': medico_nombre,
                'fecha_hora': cita.fecha_hora.strftime('%Y-%m-%d %H:%M'),
                'motivo': cita.motivo or 'Sin motivo especificado'
            })
        
        return jsonify({
            'total_citas_programadas': total_citas,
            'citas': citas_lista,
            'mensaje': f'Se encontraron {total_citas} citas programadas que serían canceladas'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error al obtener información de las citas',
            'detalle': str(e)
        }), 500

@app.route('/admin/cancelar-todas-citas-seguro', methods=['POST'])
@login_required
def cancelar_todas_citas_seguro():
    """
    Versión más segura que requiere confirmación explícita
    """
    data = request.get_json() or request.form
    confirmacion = data.get('confirmar_cancelacion')
    
    if confirmacion != 'SI_CANCELAR_TODAS':
        return jsonify({
            'error': 'Se requiere confirmación explícita',
            'mensaje': 'Para cancelar todas las citas, envíe "confirmar_cancelacion": "SI_CANCELAR_TODAS"'
        }), 400
    
    try:
        # Obtener todas las citas programadas con información detallada
        citas_programadas = db.session.query(Cita, User.nombre)\
            .join(User, Cita.paciente_id == User.id)\
            .filter(Cita.estado == 'programada').all()
        
        if not citas_programadas:
            return jsonify({
                'message': 'No hay citas programadas para cancelar',
                'citas_canceladas': 0
            }), 200
        
        total_citas = len(citas_programadas)
        
        # Crear lista de citas canceladas para el log
        citas_canceladas_info = []
        for cita_info in citas_programadas:
            cita, paciente_nombre = cita_info
            # Obtener nombre del médico desde NestJS
            medico_data = employees_service.get_doctor_by_id(cita.medico_id)
            medico_nombre = medico_data.get('name', 'Médico no encontrado') if medico_data else 'Médico no encontrado'
            
            citas_canceladas_info.append({
                'id': cita.id,
                'paciente': paciente_nombre,
                'medico': medico_nombre,
                'fecha_hora': cita.fecha_hora.strftime('%Y-%m-%d %H:%M'),
                'motivo': cita.motivo
            })
        
        # Cancelar todas las citas programadas
        Cita.query.filter_by(estado='programada').update({'estado': 'cancelada'})
        db.session.commit()
        
        return jsonify({
            'message': f'Se han cancelado exitosamente {total_citas} citas programadas',
            'citas_canceladas': total_citas,
            'citas_info': citas_canceladas_info,
            'timestamp': datetime.now().isoformat(),
            'cancelado_por': current_user.nombre
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Error interno al cancelar las citas',
            'detalle': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # No necesitamos init_db para médicos ya que vienen de NestJS
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
            db.session.commit()
            print("Base de datos inicializada")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
