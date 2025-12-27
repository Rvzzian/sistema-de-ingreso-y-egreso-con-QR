# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import time
from dotenv import load_dotenv
import os

load_dotenv()
def get_db_connection():
    conn = sqlite3.connect('trabajadores.db', timeout=10.0)
    conn.execute("PRAGMA busy_timeout = 5000")  # Espera hasta 5 segundos si está bloqueada
    return conn

app = Flask(__name__)
app.secret_key =  os.getenv('SECRET_KEY') 

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicia sesión.'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

# Inicializar DB
def init_db():
    conn = sqlite3.connect('trabajadores.db', timeout=10.0)
    c = conn.cursor()
    
    # Crear tablas con IF NOT EXISTS (seguro siempre)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE, 
                  password_hash TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS asistencias
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  trabajador_id INTEGER, 
                  fecha TEXT, 
                  hora TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS trabajadores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nombre TEXT, 
                  cargo TEXT, 
                  dni TEXT UNIQUE)''')
    
    # Verificar si la restricción UNIQUE en DNI ya existe
    c.execute("PRAGMA index_list(trabajadores)")
    indexes = c.fetchall()
    tiene_unique_dni = False
    
    for idx in indexes:
        # idx suele ser (seq, name, unique, origin, partial)
        index_name = idx[1] if len(idx) > 1 else ''
        if 'dni' in str(index_name).lower():
            tiene_unique_dni = True
            break
    
    # Si no tiene UNIQUE en DNI, hacer migración segura
    if not tiene_unique_dni:
        print("Aplicando restricción UNIQUE al DNI (migración)...")
        
        # Crear tabla temporal con UNIQUE
        c.execute('''CREATE TABLE trabajadores_temp
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      nombre TEXT, 
                      cargo TEXT, 
                      dni TEXT UNIQUE)''')
        
        # Copiar datos existentes (INSERT OR IGNORE evita errores por duplicados)
        c.execute('''INSERT OR IGNORE INTO trabajadores_temp (id, nombre, cargo, dni)
                     SELECT id, nombre, cargo, dni FROM trabajadores''')
        
        # Reemplazar tabla vieja
        c.execute("DROP TABLE trabajadores")
        c.execute("ALTER TABLE trabajadores_temp RENAME TO trabajadores")
        print("Restricción UNIQUE aplicada correctamente al DNI.")
    
    admin_username = os.getenv('ADMIN_USERNAME') 
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    c.execute("SELECT * FROM users WHERE username = ?", (admin_username,))
    if not c.fetchone():
        if admin_password:
            hashed = generate_password_hash(admin_password)
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (admin_username, hashed))
            print(f"Usuario admin creado: {admin_username} / {admin_password}")
        else:
            print("ADVERTENCIA: No se encontró ADMIN_PASSWORD en .env. No se creó usuario admin.")
    
    conn.commit()
    conn.close()
    
init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos', 'login_form')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if '_flashes' in session:
        session['_flashes'] = [(cat, msg) for cat, msg in session['_flashes'] 
                               if msg != 'Por favor, inicia sesión.']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM trabajadores")
    trabajadores = c.fetchall()
    conn.close()
    return render_template('index.html', trabajadores=trabajadores)


@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    # Limpiar mensaje automático de Flask-Login si aparece
    if '_flashes' in session:
        session['_flashes'] = [(cat, msg) for cat, msg in session['_flashes'] 
                               if msg != 'Por favor, inicia sesión.']
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        cargo = request.form.get('cargo', '').strip()
        dni = request.form.get('dni', '').strip()
        
        # Validar campos obligatorios
        if not nombre or not cargo or not dni:
            flash('Todos los campos son obligatorios.', 'agregar_form')
            return render_template('agregar.html', nombre=nombre, cargo=cargo, dni=dni)
        
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO trabajadores (nombre, cargo, dni) VALUES (?, ?, ?)", 
                      (nombre, cargo, dni))
            conn.commit()
            conn.close()
            flash('Trabajador agregado exitosamente.', 'success')
            return render_template('agregar.html')
            
        except sqlite3.IntegrityError:
            conn.close()
            flash(f'El DNI {dni} ya está registrado en el sistema.', 'agregar_form')
            return render_template('agregar.html', nombre=nombre, cargo=cargo, dni=dni)
    
    # GET: formulario limpio
    return render_template('agregar.html', nombre='', cargo='', dni='')

@app.route('/qr/<int:trabajador_id>')
def generar_qr(trabajador_id):
    # Esta ruta es pública: siempre genera el QR sin importar login
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM trabajadores WHERE id = ?", (trabajador_id,))
    if not c.fetchone():
        conn.close()
        return "Trabajador no encontrado", 404
    conn.close()
    
    # La URL del QR siempre apunta a la ruta pública /trabajador/<id>
    url = request.url_root.rstrip('/') + url_for('trabajador', trabajador_id=trabajador_id)
    
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    # Devolvemos la imagen directamente como PNG (más eficiente y compatible)
    return send_file(buf, mimetype='image/png')


@app.route('/trabajador/<int:trabajador_id>', methods=['GET', 'POST'])
def trabajador(trabajador_id):
    es_escaner = request.args.get('escaner') == '1' or request.headers.get('User-Agent', '').lower().find('html5-qrcode') != -1
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre, cargo, dni FROM trabajadores WHERE id = ?", (trabajador_id,))
    trabajador = c.fetchone()
    conn.close()
    
    if not trabajador:
        flash('Trabajador no encontrado.', 'danger')
        return redirect(url_for('index'))
    
    if '_flashes' in session:
        session['_flashes'] = [(cat, msg) for cat, msg in session['_flashes'] 
                               if msg != 'Por favor, inicia sesión.']
                               
    # Forzar marcación si viene del escáner o no está logueado
    if es_escaner or not current_user.is_authenticated:
        hoy = datetime.now().strftime('%Y-%m-%d')
        hora_actual = datetime.now().strftime('%H:%M:%S')
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM asistencias WHERE trabajador_id = ? AND fecha = ?", 
                  (trabajador_id, hoy))
        count = c.fetchone()[0]
        ultima_marcacion = c.fetchone()
        
        tipo = "Entrada" if count % 2 == 0 else "Salida"        
        c.execute("INSERT INTO asistencias (trabajador_id, fecha, hora) VALUES (?, ?, ?)",
                  (trabajador_id, hoy, hora_actual))
        conn.commit()
        conn.close()
        
        return render_template('marcar.html', 
                               nombre=trabajador[1],
                               tipo=tipo,
                               fecha=hoy,
                               hora=hora_actual,
                               trabajador_id=trabajador_id)
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'editar':
            nuevo_nombre = request.form['nombre'].strip()
            nuevo_cargo = request.form['cargo'].strip()
            nuevo_dni = request.form['dni'].strip()
            
            if not nuevo_nombre or not nuevo_cargo or not nuevo_dni:
                flash('Todos los campos son obligatorios.', 'danger')
                return render_template('ver.html', trabajador=trabajador)
            
            conn = get_db_connection()
            c = conn.cursor()
            
            # Verificar si el nuevo DNI ya existe (pero no es el mismo trabajador)
            c.execute("SELECT id FROM trabajadores WHERE dni = ? AND id != ?", (nuevo_dni, trabajador_id))
            if c.fetchone():
                conn.close()
                flash(f'El DNI {nuevo_dni} ya está registrado en otro trabajador.', 'danger')
                return render_template('ver.html', trabajador=trabajador)
            
            try:
                c.execute("UPDATE trabajadores SET nombre = ?, cargo = ?, dni = ? WHERE id = ?",
                          (nuevo_nombre, nuevo_cargo, nuevo_dni, trabajador_id))
                conn.commit()
                conn.close()
                flash('Datos del trabajador actualizados exitosamente.', 'success')
                # Actualizar variable para mostrar datos nuevos
                trabajador = (trabajador[0], nuevo_nombre, nuevo_cargo, nuevo_dni)
            except Exception as e:
                conn.close()
                flash('Error al actualizar los datos.', 'danger')
        
        elif accion == 'eliminar':
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("DELETE FROM trabajadores WHERE id = ?", (trabajador_id,))
            conn.commit()
            conn.close()
            flash('Trabajador eliminado permanentemente.', 'warning')
            return redirect(url_for('index'))
    
    return render_template('ver.html', trabajador=trabajador)


@app.route('/reportes', methods=['GET', 'POST'])
@login_required
def reportes():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Obtener parámetros de filtro
    dia = request.args.get('dia') or request.form.get('dia')
    mes = request.args.get('mes') or request.form.get('mes')
    año = request.args.get('año') or request.form.get('año')
    busqueda = request.args.get('busqueda', '').lower().strip()
    
    # Consulta: todas las marcaciones individuales ordenadas por fecha y hora
    query = """
    SELECT 
        t.id, t.nombre, t.cargo, t.dni, a.fecha, a.hora
    FROM asistencias a
    JOIN trabajadores t ON a.trabajador_id = t.id
    """
    params = []
    condiciones = []
    
    if año or mes or dia:
        fecha_parts = []
        if año:
            fecha_parts.append(año)
        else:
            fecha_parts.append('____')
        if mes:
            fecha_parts.append(mes.zfill(2))
        else:
            fecha_parts.append('__')
        if dia:
            fecha_parts.append(dia.zfill(2))
        else:
            fecha_parts.append('__')
        
        patron_fecha = '-'.join(fecha_parts)
        condiciones.append("a.fecha LIKE ?")
        params.append(patron_fecha.replace('_', '%'))
    
    # Búsqueda inteligente
    if busqueda:
        if busqueda.isdigit():
            # Solo números → buscar en DNI
            condiciones.append("t.dni LIKE ?")
            params.append(f"%{busqueda}%")
        else:
            # Contiene letras → buscar solo en nombre
            condiciones.append("LOWER(t.nombre) LIKE ?")
            params.append(f"%{busqueda}%")
    
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    
    query += " ORDER BY a.fecha DESC, t.nombre ASC, a.hora ASC"
    
    c.execute(query, params)
    marcaciones = c.fetchall()
    conn.close()
    
    # Procesar marcaciones en pares Entrada-Salida
    registros = []
    entrada_pendiente = None
    trabajador_actual = None
    fecha_actual = None
    datos_trabajador_actual = None  # Guardamos nombre, cargo, dni del trabajador con entrada pendiente

    for m in marcaciones:
        trabajador_id, nombre, cargo, dni, fecha, hora = m
        
        # Si cambia trabajador o fecha y hay entrada pendiente → cerrar con datos correctos
        if (trabajador_actual != trabajador_id or fecha_actual != fecha) and entrada_pendiente:
            registros.append((trabajador_actual, 
                              datos_trabajador_actual[0],  # nombre correcto
                              datos_trabajador_actual[1],  # cargo correcto
                              datos_trabajador_actual[2],  # dni correcto
                              fecha_actual, 
                              entrada_pendiente, 
                              '—'))
            entrada_pendiente = None
            datos_trabajador_actual = None
        
        # Actualizar contexto actual
        trabajador_actual = trabajador_id
        fecha_actual = fecha
        datos_trabajador_actual = (nombre, cargo, dni)
        
        if entrada_pendiente is None:
            # Primera marcación del par → Entrada
            entrada_pendiente = hora
        else:
            # Segunda marcación → Salida, cerrar par con datos correctos
            registros.append((trabajador_id, nombre, cargo, dni, fecha, entrada_pendiente, hora))
            entrada_pendiente = None
            datos_trabajador_actual = None  # Reset para próximo par
    
    # Al final, cerrar entrada pendiente si existe
    if entrada_pendiente and datos_trabajador_actual:
        registros.append((trabajador_actual, 
                          datos_trabajador_actual[0], 
                          datos_trabajador_actual[1], 
                          datos_trabajador_actual[2], 
                          fecha_actual, 
                          entrada_pendiente, 
                          '—'))
    return render_template('reportes.html', 
                           registros=registros, 
                           dia=dia, 
                           mes=mes, 
                           año=año, 
                           busqueda=busqueda)

@app.route('/escaner')
def escaner():
    return render_template('escaner.html')


@app.route('/logout_all')
@login_required
def logout_all():
    # Invalidar todas las sesiones del usuario actual
    user_id = current_user.id
    
    # Cerrar sesión actual
    logout_user()
    
    app.secret_key = app.secret_key + str(datetime.now().microsecond)  # Cambia ligeramente la key
    
    flash('Todas las sesiones han sido cerradas por seguridad.', 'warning')
    return redirect(url_for('login'))    

if __name__ == '__main__':
    print("========================================")
    print("¡SERVIDOR INICIANDO!")
    print("Accede desde:")
    print("   - Esta PC: http://localhost:5000")
    print("   - Otros dispositivos en la red: http://TU-IP-LOCAL:5000")
    print("Usuario admin: admin")
    print("Contraseña: pepe123")
    print("========================================")
    app.run(host='0.0.0.0', port=5000, debug=True)