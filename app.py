import os
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, flash, session

import database as db

from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bendecida-desing-secreto-2026-venezuela')

# Carpeta de subida de imágenes
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image_file(file):
    if not file or file.filename == '':
        return ''
    if allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        clean_name = secure_filename(file.filename.rsplit('.', 1)[0])
        unique_name = f"prenda_{int(time.time())}_{clean_name[:20]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(filepath)
        return f"/static/uploads/{unique_name}"
    return ''

# Inicializar base de datos al arrancar
with app.app_context():
    db.init_db()

# Control de Acceso: Redirigir a Login si no está autenticado
@app.before_request
def require_login():
    # Permitir archivos estáticos y la ruta de login sin autenticación
    if request.endpoint in ['login', 'static'] or (request.path and request.path.startswith('/static')):
        return
    if not session.get('user_id'):
        return redirect(url_for('login', next=request.url))

# Inyectar configuración, tasa y usuario en todos los templates
@app.context_processor
def inject_global_data():
    config = db.get_config_dict()
    tasa = db.get_tasa_dolar()
    return {
        'config': config,
        'tasa_dolar': tasa,
        'ultima_actualizacion_bcv': config.get('ultima_actualizacion_bcv', ''),
        'current_user': session.get('user_name', 'Administrador'),
        'username': session.get('username', 'admin'),
        'user_rol': session.get('rol', 'admin'),
        'anio_actual': datetime.now().year
    }

# ================= RUTAS DE AUTENTICACIÓN =================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    error = None
    usuarios = db.get_todos_usuarios()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            error = 'Por favor ingrese tanto el usuario como la contraseña.'
        else:
            user = db.verificar_usuario(username, password)
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_name'] = user['nombre']
                session['rol'] = user['rol']
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                error = 'Usuario o contraseña incorrectos. Verifique sus datos.'

    return render_template('login.html', error=error, usuarios=usuarios)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/auth/verificar_admin', methods=['POST'])
def api_verificar_admin():
    """Valida la contraseña de administrador para autorizar operaciones críticas"""
    try:
        data = request.get_json() or request.form
        admin_password = data.get('password', '').strip()
        if not admin_password:
            return jsonify({'success': False, 'message': 'Debe ingresar la contraseña de administrador'}), 400
        
        if db.verificar_admin_password(admin_password):
            return jsonify({'success': True, 'message': 'Autorización concedida'})
        else:
            return jsonify({'success': False, 'message': 'Contraseña de administrador incorrecta'}), 403
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# ================= RUTAS DE VISTAS =================

@app.route('/')
def dashboard():
    kpis = db.get_dashboard_kpis()
    return render_template('dashboard.html', kpis=kpis, active_page='dashboard')

@app.route('/inventario')
def inventario():
    busqueda = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', 'TODAS')
    stock_bajo = request.args.get('stock_bajo', '0') == '1'
    
    prendas = db.get_todas_prendas(
        solo_activas=True,
        filtro_busqueda=busqueda if busqueda else None,
        categoria=categoria if categoria else None,
        solo_stock_bajo=stock_bajo
    )
    categorias = db.get_categorias()
    proveedores = db.get_todos_proveedores(solo_activos=True)
    tasa = db.get_tasa_dolar()
    
    return render_template(
        'inventario.html',
        prendas=prendas,
        categorias=categorias,
        proveedores=proveedores,
        busqueda=busqueda,
        categoria_actual=categoria,
        stock_bajo=stock_bajo,
        tasa=tasa,
        active_page='inventario'
    )

@app.route('/pos')
def pos():
    prendas = db.get_todas_prendas(solo_activas=True)
    categorias = db.get_categorias()
    tasa = db.get_tasa_dolar()
    return render_template('pos.html', prendas=prendas, categorias=categorias, tasa=tasa, active_page='pos')

@app.route('/ventas')
def ventas():
    # Por defecto mostrar solo ventas REALES (completadas)
    ver_anuladas = request.args.get('ver_anuladas', '0') == '1'
    ventas_lista = db.get_ventas_recientes(200, incluir_anuladas=ver_anuladas)
    tasa = db.get_tasa_dolar()
    return render_template('ventas.html', ventas=ventas_lista, tasa=tasa, ver_anuladas=ver_anuladas, active_page='ventas')

@app.route('/proveedores')
def proveedores():
    proveedores_lista = db.get_todos_proveedores(solo_activos=True)
    compras_lista = db.get_compras_proveedores(limite=50)
    abonos_lista = db.get_abonos_proveedores(limite=50)
    categorias = db.get_categorias()
    tasa = db.get_tasa_dolar()
    return render_template(
        'proveedores.html',
        proveedores=proveedores_lista,
        compras=compras_lista,
        abonos=abonos_lista,
        categorias=categorias,
        tasa=tasa,
        active_page='proveedores'
    )

@app.route('/estadisticas')
def estadisticas():
    stats = db.get_estadisticas_completas()
    tasa = db.get_tasa_dolar()
    return render_template('estadisticas.html', stats=stats, tasa=tasa, active_page='estadisticas')

@app.route('/configuracion')
def configuracion():
    config = db.get_config_dict()
    categorias = db.get_categorias()
    return render_template('configuracion.html', config=config, categorias=categorias, active_page='configuracion')

# ================= RUTAS DE EXPORTACIÓN Y RESPALDO =================

@app.route('/respaldo/descargar')
def descargar_respaldo():
    """Descarga directa del archivo SQLite .db para copias de seguridad del cliente"""
    if not os.path.exists(db.DB_PATH):
        flash('Base de datos no encontrada', 'error')
        return redirect(url_for('configuracion'))
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d_%H%M')
    nombre_descarga = f"respaldo_inventario_euler_{fecha_hoy}.db"
    return send_file(
        db.DB_PATH,
        as_attachment=True,
        download_name=nombre_descarga,
        mimetype='application/x-sqlite3'
    )

@app.route('/ventas/exportar')
def exportar_ventas_csv():
    """Exporta historial de ventas a formato CSV compatible con Microsoft Excel"""
    ventas_lista = db.get_ventas_recientes(500)
    
    si = io.StringIO()
    # Escribir BOM para que Excel en español reconozca caracteres y tildes correctamente
    si.write('\ufeff')
    writer = csv.writer(si, delimiter=';')
    
    writer.writerow([
        'Nro Recibo', 'Fecha y Hora', 'Cliente', 'Teléfono',
        'Método de Pago', 'Tasa Usada (Bs/$)', 'Total (USD $)',
        'Total (VES Bs)', 'Estado', 'Notas'
    ])
    
    for v in ventas_lista:
        writer.writerow([
            v['numero_recibo'],
            v['fecha'],
            v['cliente_nombre'],
            v['cliente_telefono'],
            v['metodo_pago'],
            f"{v['tasa_momento']:.2f}",
            f"{v['total_usd']:.2f}",
            f"{v['total_bs']:.2f}",
            v['estado'],
            v.get('notas', '')
        ])
    
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8-sig'))
    output.seek(0)
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"reporte_ventas_euler_{fecha_hoy}.csv"
    )

# ================= APIS AJAX =================

@app.route('/api/tasa/sincronizar_bcv', methods=['GET', 'POST'])
def api_sincronizar_bcv():
    """Consulta la API del BCV en vivo y actualiza la tasa activa"""
    try:
        nueva_tasa, fecha_act = db.sincronizar_tasa_bcv()
        return jsonify({
            'success': True,
            'nueva_tasa': nueva_tasa,
            'fecha_bcv': fecha_act,
            'message': f'Tasa oficial BCV actualizada a {nueva_tasa:.2f} Bs/$ ({fecha_act})'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'No se pudo sincronizar automáticamente con el BCV: {str(e)}'
        }), 400

@app.route('/api/tasa/actualizar', methods=['POST'])
def api_actualizar_tasa():
    try:
        data = request.get_json() or request.form
        nueva_tasa = float(data.get('tasa', 0))
        if nueva_tasa <= 0:
            return jsonify({'success': False, 'message': 'La tasa debe ser mayor a 0'}), 400
        
        db.set_config_value('tasa_dolar', f"{nueva_tasa:.2f}")
        return jsonify({
            'success': True,
            'message': f'Tasa del día actualizada a {nueva_tasa:.2f} Bs/$',
            'nueva_tasa': nueva_tasa
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/prendas', methods=['GET'])
def api_obtener_prendas():
    prendas = db.get_todas_prendas(solo_activas=True)
    tasa = db.get_tasa_dolar()
    for p in prendas:
        p['precio_venta_bs'] = round(p['precio_venta'] * tasa, 2)
    return jsonify({'success': True, 'prendas': prendas, 'tasa': tasa})

@app.route('/api/prendas/crear', methods=['POST'])
def api_crear_prenda():
    try:
        data = request.form.to_dict() if request.form else (request.get_json() or {})
        codigo = data.get('codigo', '').strip().upper()
        nombre = data.get('nombre', '').strip()
        
        if not codigo or not nombre:
            return jsonify({'success': False, 'message': 'Código y nombre son obligatorios'}), 400
        
        existente = db.get_prenda_por_codigo(codigo)
        if existente:
            return jsonify({'success': False, 'message': f"Ya existe una prenda activa con el código '{codigo}'"}), 400

        # Procesar imagen si fue enviada
        if 'imagen' in request.files and request.files['imagen'].filename != '':
            ruta_imagen = save_image_file(request.files['imagen'])
            if ruta_imagen:
                data['imagen'] = ruta_imagen

        nuevo_id = db.crear_prenda(data)
        return jsonify({'success': True, 'message': 'Prenda registrada con éxito', 'id': nuevo_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/prendas/<int:prenda_id>/editar', methods=['POST'])
def api_editar_prenda(prenda_id):
    try:
        data = request.form.to_dict() if request.form else (request.get_json() or {})
        prenda = db.get_prenda_por_id(prenda_id)
        if not prenda:
            return jsonify({'success': False, 'message': 'Prenda no encontrada'}), 404
        
        # Procesar nueva imagen si fue subida
        if 'imagen' in request.files and request.files['imagen'].filename != '':
            ruta_imagen = save_image_file(request.files['imagen'])
            if ruta_imagen:
                data['imagen'] = ruta_imagen

        db.actualizar_prenda(prenda_id, data)
        return jsonify({'success': True, 'message': 'Prenda actualizada con éxito'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/prendas/<int:prenda_id>/stock', methods=['POST'])
def api_ajustar_stock(prenda_id):
    try:
        data = request.get_json() or request.form
        delta = int(data.get('delta', 0))
        nuevo_stock = db.ajustar_stock(prenda_id, delta)
        return jsonify({'success': True, 'nuevo_stock': nuevo_stock})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/prendas/<int:prenda_id>/eliminar', methods=['POST'])
def api_eliminar_prenda(prenda_id):
    try:
        accion = db.eliminar_o_desactivar_prenda(prenda_id)
        msg = 'Prenda eliminada del sistema' if accion == 'eliminada' else 'Prenda desactivada (preservada para historial de ventas)'
        return jsonify({'success': True, 'message': msg, 'accion': accion})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/ventas/crear', methods=['POST'])
def api_crear_venta():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos de venta no recibidos'}), 400
        
        items = data.get('items', [])
        if not items:
            return jsonify({'success': False, 'message': 'El carrito de venta está vacío'}), 400

        resultado = db.registrar_venta(data, items)
        return jsonify({'success': True, 'resultado': resultado})
    except ValueError as ve:
        return jsonify({'success': False, 'message': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al procesar la venta: {str(e)}"}), 500

@app.route('/api/ventas/<int:venta_id>/anular', methods=['POST'])
def api_anular_venta(venta_id):
    try:
        data = request.get_json() or request.form
        admin_password = data.get('admin_password', '').strip()
        # Si el usuario logueado no es admin o si se solicita autorización estricta
        if not admin_password or not db.verificar_admin_password(admin_password):
            return jsonify({'success': False, 'message': 'Autorización denegada: Contraseña de Administrador incorrecta o no suministrada'}), 403

        db.anular_venta(venta_id)
        return jsonify({'success': True, 'message': 'Venta autorizada y anulada con éxito. Prendas devueltas al inventario.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/ventas/<int:venta_id>/eliminar_definitiva', methods=['POST'])
def api_eliminar_venta_definitiva(venta_id):
    try:
        data = request.get_json() or request.form
        admin_password = data.get('admin_password', '').strip()
        if not admin_password or not db.verificar_admin_password(admin_password):
            return jsonify({'success': False, 'message': 'Autorización denegada: Contraseña de Administrador incorrecta o requerida'}), 403

        db.eliminar_venta_definitiva(venta_id)
        return jsonify({'success': True, 'message': 'Venta anulada eliminada definitivamente del sistema'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/ventas/purgar_anuladas', methods=['POST'])
def api_purgar_ventas_anuladas():
    try:
        data = request.get_json() or request.form
        admin_password = data.get('admin_password', '').strip()
        if not admin_password or not db.verificar_admin_password(admin_password):
            return jsonify({'success': False, 'message': 'Autorización requerida: Ingrese contraseña de Administrador'}), 403

        total = db.purgar_ventas_anuladas()
        return jsonify({'success': True, 'message': f'Se han purgado {total} ventas anuladas. El historial está limpio.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/ventas/<int:venta_id>', methods=['GET'])
def api_ver_venta(venta_id):
    detalle = db.get_venta_completa(venta_id)
    if not detalle:
        return jsonify({'success': False, 'message': 'Venta no encontrada'}), 404
    return jsonify({'success': True, 'datos': detalle})

# ================= APIS PROVEEDORES, COMPRAS Y ABONOS =================

@app.route('/api/proveedores', methods=['GET'])
def api_obtener_proveedores():
    provs = db.get_todos_proveedores(solo_activos=True)
    return jsonify({'success': True, 'proveedores': provs})

@app.route('/api/proveedores/crear', methods=['POST'])
def api_crear_proveedor():
    try:
        data = request.get_json() or request.form
        nombre = data.get('nombre', '').strip()
        if not nombre:
            return jsonify({'success': False, 'message': 'El nombre del proveedor es obligatorio'}), 400
        
        nuevo_id = db.crear_proveedor(data)
        return jsonify({'success': True, 'message': 'Proveedor registrado exitosamente', 'id': nuevo_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/proveedores/<int:proveedor_id>/editar', methods=['POST'])
def api_editar_proveedor(proveedor_id):
    try:
        data = request.get_json() or request.form
        db.actualizar_proveedor(proveedor_id, data)
        return jsonify({'success': True, 'message': 'Proveedor actualizado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/proveedores/<int:proveedor_id>/eliminar', methods=['POST'])
def api_eliminar_proveedor(proveedor_id):
    try:
        data = request.get_json() or request.form
        admin_password = data.get('admin_password', '').strip()
        forzar_completo = data.get('forzar_completo', True)  # Limpiar deudas asociadas para no dejar deuda huérfana
        
        if not admin_password or not db.verificar_admin_password(admin_password):
            return jsonify({'success': False, 'message': 'Autorización denegada: Ingrese la contraseña de Administrador'}), 403

        accion = db.eliminar_o_desactivar_proveedor(proveedor_id, forzar_completo=forzar_completo)
        msg = 'Proveedor y sus cuentas asociadas eliminados correctamente' if accion == 'eliminado' else 'Proveedor desactivado'
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/proveedores/compras/<int:compra_id>/eliminar', methods=['POST'])
def api_eliminar_compra_proveedor(compra_id):
    try:
        data = request.get_json() or request.form
        admin_password = data.get('admin_password', '').strip()
        if not admin_password or not db.verificar_admin_password(admin_password):
            return jsonify({'success': False, 'message': 'Autorización denegada: Ingrese la contraseña de Administrador'}), 403

        db.eliminar_compra_proveedor(compra_id)
        return jsonify({'success': True, 'message': 'Factura de compra y su saldo pendiente eliminados con éxito'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/proveedores/compras/crear', methods=['POST'])
def api_crear_compra_proveedor():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos de la factura'}), 400
        
        prendas = data.get('prendas', [])
        compra_id = db.registrar_compra_proveedor(data, prendas_ingresadas=prendas)
        return jsonify({
            'success': True,
            'message': 'Factura de compra e inventario registrados exitosamente en divisas ($ USD)',
            'compra_id': compra_id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/proveedores/abonos/crear', methods=['POST'])
def api_crear_abono_proveedor():
    try:
        data = request.get_json() or request.form
        abono_id = db.registrar_abono_proveedor(data)
        return jsonify({
            'success': True,
            'message': 'Abono a proveedor registrado y saldo amortizado exitosamente',
            'abono_id': abono_id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/configuracion/guardar', methods=['POST'])
def api_guardar_configuracion():
    try:
        data = request.get_json() or request.form
        for k in ['nombre_tienda', 'telefono', 'direccion', 'mensaje_recibo']:
            if k in data:
                db.set_config_value(k, data[k].strip())
        return jsonify({'success': True, 'message': 'Configuración guardada correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/categorias/crear', methods=['POST'])
def api_crear_categoria():
    try:
        data = request.get_json() or request.form
        nombre = data.get('nombre', '').strip()
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre de categoría requerido'}), 400
        db.agregar_categoria(nombre)
        return jsonify({'success': True, 'message': 'Categoría añadida', 'categoria': nombre})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/usuario/cambiar_password', methods=['POST'])
def api_cambiar_password():
    try:
        data = request.get_json() or request.form
        actual = data.get('password_actual', '')
        nueva = data.get('password_nueva', '')
        
        user_id = session.get('user_id')
        username = session.get('username')
        
        if not db.verificar_usuario(username, actual):
            return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta'}), 400
        
        if len(nueva) < 4:
            return jsonify({'success': False, 'message': 'La nueva contraseña debe tener al menos 4 caracteres'}), 400
            
        db.cambiar_password(user_id, nueva)
        return jsonify({'success': True, 'message': '¡Contraseña actualizada exitosamente!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
