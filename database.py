import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventario.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT DEFAULT 'admin'
        )
    ''')

    # Crear usuario administrador por defecto si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        default_hash = generate_password_hash('bendecida2026')
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?, ?, ?, ?)",
            ('admin', default_hash, 'Administrador Bendecida', 'admin')
        )

    # Crear usuario vendedor/cajero si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'vendedor'")
    if cursor.fetchone()[0] == 0:
        cajero_hash = generate_password_hash('1234')
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?, ?, ?, ?)",
            ('vendedor', cajero_hash, 'Caja y Ventas', 'cajero')
        )

    # Tabla de configuración
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')

    # Tabla de categorías
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    ''')

    # Tabla de prendas de ropa
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            talla TEXT NOT NULL,
            color TEXT NOT NULL,
            precio_costo REAL NOT NULL DEFAULT 0.0,
            precio_venta REAL NOT NULL DEFAULT 0.0,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 3,
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL,
            imagen TEXT DEFAULT ''
        )
    ''')

    # Migración: Verificar si la columna 'imagen' existe en prendas si la tabla ya existía
    cursor.execute("PRAGMA table_info(prendas)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'imagen' not in columns:
        cursor.execute("ALTER TABLE prendas ADD COLUMN imagen TEXT DEFAULT ''")

    # Tabla de ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_recibo TEXT UNIQUE NOT NULL,
            fecha TEXT NOT NULL,
            cliente_nombre TEXT DEFAULT 'Cliente General',
            cliente_telefono TEXT DEFAULT '',
            metodo_pago TEXT NOT NULL,
            tasa_momento REAL NOT NULL,
            total_usd REAL NOT NULL,
            total_bs REAL NOT NULL,
            estado TEXT DEFAULT 'COMPLETADA',
            notas TEXT DEFAULT ''
        )
    ''')

    # Detalle de prendas vendidas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS venta_detalles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            prenda_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            talla TEXT NOT NULL,
            color TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario_usd REAL NOT NULL,
            precio_unitario_bs REAL NOT NULL,
            subtotal_usd REAL NOT NULL,
            subtotal_bs REAL NOT NULL,
            FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
            FOREIGN KEY (prenda_id) REFERENCES prendas(id)
        )
    ''')

    # Tabla de proveedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            contacto TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            direccion TEXT DEFAULT '',
            notas TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_registro TEXT NOT NULL
        )
    ''')

    # Tabla de facturas / compras a proveedores (en divisas USD)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras_proveedor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id INTEGER NOT NULL,
            numero_factura TEXT NOT NULL,
            fecha TEXT NOT NULL,
            monto_total_usd REAL NOT NULL,
            monto_pagado_usd REAL NOT NULL DEFAULT 0.0,
            saldo_pendiente_usd REAL NOT NULL,
            tasa_cambio REAL NOT NULL,
            estado TEXT DEFAULT 'PENDIENTE',
            notas TEXT DEFAULT '',
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE CASCADE
        )
    ''')

    # Tabla de abonos / pagos a proveedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abonos_proveedor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id INTEGER NOT NULL,
            compra_id INTEGER,
            fecha TEXT NOT NULL,
            monto_usd REAL NOT NULL,
            monto_bs REAL NOT NULL,
            tasa_cambio REAL NOT NULL,
            metodo_pago TEXT NOT NULL,
            referencia TEXT DEFAULT '',
            notas TEXT DEFAULT '',
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE CASCADE,
            FOREIGN KEY (compra_id) REFERENCES compras_proveedor(id) ON DELETE SET NULL
        )
    ''')

    # Migración: Verificar si columnas proveedor_id y compra_proveedor_id existen en prendas
    cursor.execute("PRAGMA table_info(prendas)")
    cols_prendas = [col[1] for col in cursor.fetchall()]
    if 'proveedor_id' not in cols_prendas:
        cursor.execute("ALTER TABLE prendas ADD COLUMN proveedor_id INTEGER DEFAULT NULL")
    if 'compra_proveedor_id' not in cols_prendas:
        cursor.execute("ALTER TABLE prendas ADD COLUMN compra_proveedor_id INTEGER DEFAULT NULL")

    # Configuraciones iniciales por defecto si no existen
    config_defaults = {
        'nombre_tienda': 'Bendecida Desing',
        'telefono': '04243361204',
        'direccion': 'Centro Comercial Galería, Nivel 1, Local 14',
        'tasa_dolar': '65.50',
        'moneda_principal': 'USD',
        'moneda_secundaria': 'VES',
        'simbolo_principal': '$',
        'simbolo_secundaria': 'Bs.',
        'mensaje_recibo': '¡Gracias por elegir Bendecida Desing! Moda que te bendice y te hace brillar.'
    }

    for k, v in config_defaults.items():
        cursor.execute('INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)', (k, v))

    # Asegurar actualización forzada del teléfono solicitado
    cursor.execute("UPDATE configuracion SET valor = '04243361204' WHERE clave = 'telefono' AND valor LIKE '%412%'")

    # Categorías sugeridas iniciales
    categorias_iniciales = [
        'Vestidos', 'Blusas y Tops', 'Pantalones y Jeans', 'Shorts y Faldas', 
        'Chaquetas y Abrigos', 'Ropa Deportiva', 'Calzado', 'Accesorios'
    ]
    for cat in categorias_iniciales:
        cursor.execute('INSERT OR IGNORE INTO categorias (nombre) VALUES (?)', (cat,))

    # Prendas de prueba iniciales si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM prendas')
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prendas_muestra = [
            ('PREN-001', 'Vestido Midi Floral Primavera', 'Vestidos', 'M', 'Rosa Estampado', 14.00, 25.00, 8, 3, now_str),
            ('PREN-002', 'Vestido Corto Casual Lino', 'Vestidos', 'S', 'Beige', 12.50, 22.00, 2, 3, now_str),
            ('PREN-003', 'Blusa Elegante Cuello V', 'Blusas y Tops', 'L', 'Blanco', 8.00, 16.00, 12, 4, now_str),
            ('PREN-004', 'Crop Top Rib Algodón', 'Blusas y Tops', 'S', 'Negro', 5.00, 10.00, 15, 5, now_str),
            ('PREN-005', 'Jeans Mom Fit Tiro Alto', 'Pantalones y Jeans', '30', 'Azul Claro', 16.00, 30.00, 1, 3, now_str),
            ('PREN-006', 'Jeans Skinny Elasticados', 'Pantalones y Jeans', '28', 'Azul Oscuro', 15.00, 28.00, 7, 3, now_str),
            ('PREN-007', 'Short Denim Desflecado', 'Shorts y Faldas', 'M', 'Celeste', 9.00, 18.00, 6, 2, now_str),
            ('PREN-008', 'Falda Plisada Satinada', 'Shorts y Faldas', 'M', 'Verde Olivo', 11.00, 20.00, 4, 2, now_str),
            ('PREN-009', 'Chaqueta Biker Efecto Cuero', 'Chaquetas y Abrigos', 'L', 'Negro', 22.00, 45.00, 3, 2, now_str),
            ('PREN-010', 'Conjunto Biker + Top Deportivo', 'Ropa Deportiva', 'M', 'Gris Jaspeado', 10.00, 20.00, 9, 3, now_str),
            ('PREN-011', 'Sandalias Planas Tiras Finas', 'Calzado', '38', 'Dorado', 12.00, 24.00, 0, 2, now_str),
            ('PREN-012', 'Cinturón Hebilla Metálica', 'Accesorios', 'Única', 'Café', 4.00, 8.00, 10, 3, now_str)
        ]
        cursor.executemany('''
            INSERT INTO prendas (codigo, nombre, categoria, talla, color, precio_costo, precio_venta, stock, stock_minimo, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', prendas_muestra)

    conn.commit()
    conn.close()

# Funciones de configuración
def get_config_dict():
    conn = get_db()
    rows = conn.execute('SELECT clave, valor FROM configuracion').fetchall()
    conn.close()
    return {r['clave']: r['valor'] for r in rows}

def set_config_value(clave, valor):
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)', (clave, str(valor)))
    conn.commit()
    conn.close()

def get_tasa_dolar():
    conn = get_db()
    row = conn.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_dolar'").fetchone()
    conn.close()
    if row:
        try:
            return float(row['valor'])
        except ValueError:
            return 65.50
    return 65.50

# Funciones de prendas
def get_todas_prendas(solo_activas=True, filtro_busqueda=None, categoria=None, solo_stock_bajo=False):
    conn = get_db()
    query = '''
        SELECT p.*, prov.nombre as proveedor_nombre, prov.codigo as proveedor_codigo
        FROM prendas p
        LEFT JOIN proveedores prov ON p.proveedor_id = prov.id
        WHERE 1=1
    '''
    params = []

    if solo_activas:
        query += ' AND p.activo = 1'
    
    if categoria and categoria != 'TODAS':
        query += ' AND p.categoria = ?'
        params.append(categoria)

    if filtro_busqueda:
        query += ' AND (p.codigo LIKE ? OR p.nombre LIKE ? OR p.color LIKE ? OR prov.nombre LIKE ?)'
        like_term = f"%{filtro_busqueda}%"
        params.extend([like_term, like_term, like_term, like_term])

    if solo_stock_bajo:
        query += ' AND p.stock <= p.stock_minimo'

    query += ' ORDER BY p.stock ASC, p.id DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_prenda_por_id(prenda_id):
    conn = get_db()
    row = conn.execute('''
        SELECT p.*, prov.nombre as proveedor_nombre, prov.codigo as proveedor_codigo
        FROM prendas p
        LEFT JOIN proveedores prov ON p.proveedor_id = prov.id
        WHERE p.id = ?
    ''', (prenda_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_prenda_por_codigo(codigo):
    conn = get_db()
    row = conn.execute('SELECT * FROM prendas WHERE codigo = ? AND activo = 1', (codigo.strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None

def sincronizar_tasa_bcv():
    """Consulta la API pública del BCV y actualiza la tasa oficial"""
    import urllib.request
    import json
    url = 'https://ve.dolarapi.com/v1/dolares/oficial'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=6) as response:
        data = json.loads(response.read().decode())
        promedio = float(data.get('promedio', 0))
        if promedio > 0:
            set_config_value('tasa_dolar', f"{promedio:.2f}")
            ahora = datetime.now().strftime('%d/%m/%Y %I:%M %p')
            set_config_value('ultima_actualizacion_bcv', ahora)
            return promedio, ahora
        raise ValueError("La tasa promedio obtenida no es válida")

def crear_prenda(datos):
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    proveedor_id = datos.get('proveedor_id')
    if proveedor_id and str(proveedor_id).strip() not in ('', '0', 'None'):
        proveedor_id = int(proveedor_id)
    else:
        proveedor_id = None

    cursor.execute('''
        INSERT INTO prendas (codigo, nombre, categoria, talla, color, precio_costo, precio_venta, stock, stock_minimo, fecha_creacion, imagen, proveedor_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datos['codigo'].strip().upper(),
        datos['nombre'].strip(),
        datos['categoria'].strip(),
        datos['talla'].strip().upper(),
        datos['color'].strip(),
        float(datos.get('precio_costo', 0)),
        float(datos.get('precio_venta', 0)),
        int(datos.get('stock', 0)),
        int(datos.get('stock_minimo', 2)),
        now_str,
        datos.get('imagen', '').strip(),
        proveedor_id
    ))
    nuevo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id

def actualizar_prenda(prenda_id, datos):
    conn = get_db()
    
    proveedor_id = datos.get('proveedor_id')
    if proveedor_id and str(proveedor_id).strip() not in ('', '0', 'None'):
        proveedor_id = int(proveedor_id)
    else:
        proveedor_id = None

    # Si no se envía nueva imagen, preservar la actual
    if 'imagen' in datos and datos['imagen']:
        conn.execute('''
            UPDATE prendas SET
                codigo = ?,
                nombre = ?,
                categoria = ?,
                talla = ?,
                color = ?,
                precio_costo = ?,
                precio_venta = ?,
                stock = ?,
                stock_minimo = ?,
                imagen = ?,
                proveedor_id = ?
            WHERE id = ?
        ''', (
            datos['codigo'].strip().upper(),
            datos['nombre'].strip(),
            datos['categoria'].strip(),
            datos['talla'].strip().upper(),
            datos['color'].strip(),
            float(datos.get('precio_costo', 0)),
            float(datos.get('precio_venta', 0)),
            int(datos.get('stock', 0)),
            int(datos.get('stock_minimo', 2)),
            datos['imagen'].strip(),
            proveedor_id,
            prenda_id
        ))
    else:
        conn.execute('''
            UPDATE prendas SET
                codigo = ?,
                nombre = ?,
                categoria = ?,
                talla = ?,
                color = ?,
                precio_costo = ?,
                precio_venta = ?,
                stock = ?,
                stock_minimo = ?,
                proveedor_id = ?
            WHERE id = ?
        ''', (
            datos['codigo'].strip().upper(),
            datos['nombre'].strip(),
            datos['categoria'].strip(),
            datos['talla'].strip().upper(),
            datos['color'].strip(),
            float(datos.get('precio_costo', 0)),
            float(datos.get('precio_venta', 0)),
            int(datos.get('stock', 0)),
            int(datos.get('stock_minimo', 2)),
            proveedor_id,
            prenda_id
        ))
    conn.commit()
    conn.close()

def ajustar_stock(prenda_id, delta):
    conn = get_db()
    conn.execute('UPDATE prendas SET stock = MAX(0, stock + ?) WHERE id = ?', (delta, prenda_id))
    conn.commit()
    row = conn.execute('SELECT stock FROM prendas WHERE id = ?', (prenda_id,)).fetchone()
    conn.close()
    return row['stock'] if row else 0

def eliminar_o_desactivar_prenda(prenda_id):
    conn = get_db()
    # Si tiene ventas asociadas, se desactiva para preservar la integridad histórica
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM venta_detalles WHERE prenda_id = ?', (prenda_id,))
    tiene_ventas = cursor.fetchone()[0] > 0
    if tiene_ventas:
        cursor.execute('UPDATE prendas SET activo = 0 WHERE id = ?', (prenda_id,))
    else:
        cursor.execute('DELETE FROM prendas WHERE id = ?', (prenda_id,))
    conn.commit()
    conn.close()
    return 'desactivada' if tiene_ventas else 'eliminada'

# Categorías
def get_categorias():
    conn = get_db()
    rows = conn.execute('SELECT nombre FROM categorias ORDER BY nombre ASC').fetchall()
    conn.close()
    return [r['nombre'] for r in rows]

def agregar_categoria(nombre):
    nombre_limpio = nombre.strip()
    if not nombre_limpio:
        return
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO categorias (nombre) VALUES (?)', (nombre_limpio,))
    conn.commit()
    conn.close()

# Ventas
def registrar_venta(datos_venta, items):
    """
    Registra una venta y descuenta inventario de forma atómica.
    """
    conn = get_db()
    cursor = conn.cursor()
    tasa = get_tasa_dolar()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Generar correlativo de recibo
    fecha_prefix = datetime.now().strftime('%y%m%d')
    cursor.execute("SELECT COUNT(*) FROM ventas WHERE numero_recibo LIKE ?", (f"REC-{fecha_prefix}-%",))
    correlativo = cursor.fetchone()[0] + 1
    numero_recibo = f"REC-{fecha_prefix}-{correlativo:04d}"

    total_usd = float(datos_venta.get('total_usd', 0))
    total_bs = round(total_usd * tasa, 2)

    try:
        cursor.execute('''
            INSERT INTO ventas (numero_recibo, fecha, cliente_nombre, cliente_telefono, metodo_pago, tasa_momento, total_usd, total_bs, estado, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETADA', ?)
        ''', (
            numero_recibo,
            now_str,
            datos_venta.get('cliente_nombre', 'Cliente General') or 'Cliente General',
            datos_venta.get('cliente_telefono', '') or '',
            datos_venta.get('metodo_pago', 'Efectivo Divisas ($)'),
            tasa,
            total_usd,
            total_bs,
            datos_venta.get('notas', '') or ''
        ))
        venta_id = cursor.lastrowid

        # Insertar detalles y descontar stock
        for item in items:
            prenda_id = item['prenda_id']
            cant = int(item['cantidad'])
            p_usd = float(item['precio_usd'])
            p_bs = round(p_usd * tasa, 2)
            sub_usd = round(p_usd * cant, 2)
            sub_bs = round(p_bs * cant, 2)

            # Verificar stock suficiente
            cursor.execute('SELECT stock, nombre, codigo, talla, color FROM prendas WHERE id = ?', (prenda_id,))
            prenda = cursor.fetchone()
            if not prenda or prenda['stock'] < cant:
                raise ValueError(f"Stock insuficiente para '{prenda['nombre'] if prenda else 'Item'}' (Disponible: {prenda['stock'] if prenda else 0})")

            cursor.execute('''
                INSERT INTO venta_detalles (venta_id, prenda_id, codigo, nombre, talla, color, cantidad, precio_unitario_usd, precio_unitario_bs, subtotal_usd, subtotal_bs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                venta_id,
                prenda_id,
                prenda['codigo'],
                prenda['nombre'],
                prenda['talla'],
                prenda['color'],
                cant,
                p_usd,
                p_bs,
                sub_usd,
                sub_bs
            ))

            # Descontar stock
            cursor.execute('UPDATE prendas SET stock = stock - ? WHERE id = ?', (cant, prenda_id))

        conn.commit()
        return {
            'success': True,
            'venta_id': venta_id,
            'numero_recibo': numero_recibo,
            'fecha': now_str,
            'total_usd': total_usd,
            'total_bs': total_bs,
            'tasa': tasa
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def anular_venta(venta_id):
    """
    Anula la venta y restituye las unidades al inventario.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT estado FROM ventas WHERE id = ?', (venta_id,))
        venta = cursor.fetchone()
        if not venta:
            raise ValueError("Venta no encontrada")
        if venta['estado'] == 'ANULADA':
            raise ValueError("La venta ya está anulada")

        # Recuperar items para devolver el stock
        cursor.execute('SELECT prenda_id, cantidad FROM venta_detalles WHERE venta_id = ?', (venta_id,))
        detalles = cursor.fetchall()
        for d in detalles:
            cursor.execute('UPDATE prendas SET stock = stock + ? WHERE id = ?', (d['cantidad'], d['prenda_id']))

        cursor.execute("UPDATE ventas SET estado = 'ANULADA' WHERE id = ?", (venta_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def eliminar_venta_definitiva(venta_id):
    """
    Elimina físicamente una venta anulada de la base de datos (y sus detalles en cascada)
    para que no quede rastro en el historial.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM venta_detalles WHERE venta_id = ?', (venta_id,))
        cursor.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def purgar_ventas_anuladas():
    """
    Elimina todas las ventas con estado ANULADA de la base de datos.
    Deja únicamente las ventas reales.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM ventas WHERE estado = 'ANULADA'")
        ids = [row[0] for row in cursor.fetchall()]
        if ids:
            cursor.execute("DELETE FROM venta_detalles WHERE venta_id IN (SELECT id FROM ventas WHERE estado = 'ANULADA')")
            cursor.execute("DELETE FROM ventas WHERE estado = 'ANULADA'")
            conn.commit()
        return len(ids)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_ventas_recientes(limite=200, incluir_anuladas=False):
    """
    Por defecto devuelve ÚNICAMENTE ventas reales (COMPLETADAS).
    Si incluir_anuladas=True devuelve también las anuladas.
    """
    conn = get_db()
    condicion_estado = "" if incluir_anuladas else "WHERE v.estado = 'COMPLETADA'"
    rows = conn.execute(f'''
        SELECT v.*, COUNT(vd.id) as total_items, COALESCE(SUM(vd.cantidad), 0) as total_piezas
        FROM ventas v
        LEFT JOIN venta_detalles vd ON v.id = vd.venta_id
        {condicion_estado}
        GROUP BY v.id
        ORDER BY v.id DESC
        LIMIT ?
    ''', (limite,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_venta_completa(venta_id):
    conn = get_db()
    v_row = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()
    if not v_row:
        conn.close()
        return None
    d_rows = conn.execute('SELECT * FROM venta_detalles WHERE venta_id = ?', (venta_id,)).fetchall()
    conn.close()
    return {
        'venta': dict(v_row),
        'detalles': [dict(d) for d in d_rows]
    }

# ================= MÓDULO DE PROVEEDORES =================

def get_todos_proveedores(solo_activos=True):
    conn = get_db()
    query = '''
        SELECT p.*,
            COALESCE((SELECT SUM(c.monto_total_usd) FROM compras_proveedor c WHERE c.proveedor_id = p.id), 0.0) as total_facturado_usd,
            COALESCE((SELECT SUM(c.saldo_pendiente_usd) FROM compras_proveedor c WHERE c.proveedor_id = p.id), 0.0) as saldo_deuda_usd,
            COALESCE((SELECT COUNT(*) FROM compras_proveedor c WHERE c.proveedor_id = p.id), 0) as total_facturas
        FROM proveedores p
    '''
    if solo_activos:
        query += ' WHERE p.activo = 1'
    query += ' ORDER BY p.nombre ASC'
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_proveedor_por_id(proveedor_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM proveedores WHERE id = ?', (proveedor_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_proveedor_por_codigo(codigo):
    conn = get_db()
    row = conn.execute('SELECT * FROM proveedores WHERE codigo = ?', (codigo.strip().upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None

def crear_proveedor(datos):
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    codigo = datos.get('codigo', '').strip().upper()
    if not codigo:
        # Generar código automático si viene vacío
        cursor.execute("SELECT COUNT(*) FROM proveedores")
        correlativo = cursor.fetchone()[0] + 1
        codigo = f"PROV-{correlativo:03d}"

    cursor.execute('''
        INSERT INTO proveedores (codigo, nombre, contacto, telefono, direccion, notas, activo, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    ''', (
        codigo,
        datos['nombre'].strip(),
        datos.get('contacto', '').strip(),
        datos.get('telefono', '').strip(),
        datos.get('direccion', '').strip(),
        datos.get('notas', '').strip(),
        now_str
    ))
    nuevo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id

def actualizar_proveedor(proveedor_id, datos):
    conn = get_db()
    conn.execute('''
        UPDATE proveedores SET
            codigo = ?,
            nombre = ?,
            contacto = ?,
            telefono = ?,
            direccion = ?,
            notas = ?
        WHERE id = ?
    ''', (
        datos.get('codigo', '').strip().upper(),
        datos['nombre'].strip(),
        datos.get('contacto', '').strip(),
        datos.get('telefono', '').strip(),
        datos.get('direccion', '').strip(),
        datos.get('notas', '').strip(),
        proveedor_id
    ))
    conn.commit()
    conn.close()

def eliminar_o_desactivar_proveedor(proveedor_id, forzar_completo=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM compras_proveedor WHERE proveedor_id = ?', (proveedor_id,))
    tiene_compras = cursor.fetchone()[0] > 0

    if forzar_completo or not tiene_compras:
        # Eliminar abonos y compras asociadas al proveedor para limpiar toda deuda
        cursor.execute('DELETE FROM abonos_proveedor WHERE proveedor_id = ?', (proveedor_id,))
        cursor.execute('DELETE FROM compras_proveedor WHERE proveedor_id = ?', (proveedor_id,))
        # Desvincular prendas
        cursor.execute('UPDATE prendas SET proveedor_id = NULL, compra_proveedor_id = NULL WHERE proveedor_id = ?', (proveedor_id,))
        cursor.execute('DELETE FROM proveedores WHERE id = ?', (proveedor_id,))
        accion = 'eliminado'
    else:
        cursor.execute('UPDATE proveedores SET activo = 0 WHERE id = ?', (proveedor_id,))
        accion = 'desactivado'
    conn.commit()
    conn.close()
    return accion

def eliminar_compra_proveedor(compra_id):
    """
    Elimina una factura/compra específica a proveedor y sus abonos directos,
    desvinculando las prendas asociadas para evitar saldos pendientes huérfanos.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM abonos_proveedor WHERE compra_id = ?', (compra_id,))
        cursor.execute('UPDATE prendas SET compra_proveedor_id = NULL WHERE compra_proveedor_id = ?', (compra_id,))
        cursor.execute('DELETE FROM compras_proveedor WHERE id = ?', (compra_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ================= COMPRAS Y FACTURAS DE PROVEEDORES =================

def registrar_compra_proveedor(datos, prendas_ingresadas=None):
    """
    Registra una factura/compra de mercancía de proveedor en divisas USD,
    y opcionalmente da entrada de inventario a las prendas asociadas.
    """
    conn = get_db()
    cursor = conn.cursor()
    tasa = get_tasa_dolar()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        proveedor_id = int(datos['proveedor_id'])
        monto_total_usd = float(datos['monto_total_usd'])
        monto_pagado_usd = float(datos.get('monto_pagado_usd', 0.0))
        saldo_pendiente_usd = max(0.0, monto_total_usd - monto_pagado_usd)
        estado = 'PAGADA' if saldo_pendiente_usd <= 0.01 else ('PARCIAL' if monto_pagado_usd > 0 else 'PENDIENTE')
        numero_factura = datos.get('numero_factura', '').strip() or f"FACT-{datetime.now().strftime('%y%m%d%H%M')}"

        cursor.execute('''
            INSERT INTO compras_proveedor (
                proveedor_id, numero_factura, fecha, monto_total_usd,
                monto_pagado_usd, saldo_pendiente_usd, tasa_cambio, estado, notas
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proveedor_id,
            numero_factura,
            datos.get('fecha', now_str),
            monto_total_usd,
            monto_pagado_usd,
            saldo_pendiente_usd,
            tasa,
            estado,
            datos.get('notas', '')
        ))
        compra_id = cursor.lastrowid

        # Si hubo un abono inicial inmediato
        if monto_pagado_usd > 0:
            cursor.execute('''
                INSERT INTO abonos_proveedor (
                    proveedor_id, compra_id, fecha, monto_usd, monto_bs,
                    tasa_cambio, metodo_pago, referencia, notas
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                proveedor_id,
                compra_id,
                now_str,
                monto_pagado_usd,
                round(monto_pagado_usd * tasa, 2),
                tasa,
                datos.get('metodo_pago_inicial', 'Efectivo Divisas ($)'),
                datos.get('referencia_inicial', 'Pago inicial al recibir factura'),
                f"Abono inicial Factura #{numero_factura}"
            ))

        # Si se especificaron prendas para ingresar al inventario
        if prendas_ingresadas:
            for p in prendas_ingresadas:
                codigo = p.get('codigo', '').strip().upper()
                if not codigo:
                    continue
                # Revisar si la prenda ya existe para sumar stock o actualizar costo
                cursor.execute('SELECT id, stock FROM prendas WHERE codigo = ?', (codigo,))
                existente = cursor.fetchone()
                cant = int(p.get('cantidad', 1))
                costo = float(p.get('precio_costo', 0.0))
                venta = float(p.get('precio_venta', 0.0))

                if existente:
                    cursor.execute('''
                        UPDATE prendas SET
                            stock = stock + ?,
                            precio_costo = CASE WHEN ? > 0 THEN ? ELSE precio_costo END,
                            precio_venta = CASE WHEN ? > 0 THEN ? ELSE precio_venta END,
                            proveedor_id = ?,
                            compra_proveedor_id = ?
                        WHERE id = ?
                    ''', (cant, costo, costo, venta, venta, proveedor_id, compra_id, existente['id']))
                else:
                    cursor.execute('''
                        INSERT INTO prendas (
                            codigo, nombre, categoria, talla, color,
                            precio_costo, precio_venta, stock, stock_minimo,
                            fecha_creacion, imagen, proveedor_id, compra_proveedor_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        codigo,
                        p.get('nombre', 'Prenda S/N').strip(),
                        p.get('categoria', 'Vestidos').strip(),
                        p.get('talla', 'M').strip().upper(),
                        p.get('color', 'Varios').strip(),
                        costo,
                        venta,
                        cant,
                        int(p.get('stock_minimo', 2)),
                        now_str,
                        p.get('imagen', ''),
                        proveedor_id,
                        compra_id
                    ))

        conn.commit()
        return compra_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def registrar_abono_proveedor(datos):
    """
    Registra un abono a la cuenta de un proveedor y amortiza facturas pendientes.
    """
    conn = get_db()
    cursor = conn.cursor()
    tasa = get_tasa_dolar()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        proveedor_id = int(datos['proveedor_id'])
        compra_id = int(datos['compra_id']) if datos.get('compra_id') else None
        monto_usd = float(datos['monto_usd'])
        monto_bs = round(monto_usd * tasa, 2)

        cursor.execute('''
            INSERT INTO abonos_proveedor (
                proveedor_id, compra_id, fecha, monto_usd, monto_bs,
                tasa_cambio, metodo_pago, referencia, notas
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proveedor_id,
            compra_id,
            now_str,
            monto_usd,
            monto_bs,
            tasa,
            datos.get('metodo_pago', 'Efectivo Divisas ($)'),
            datos.get('referencia', '').strip(),
            datos.get('notas', '').strip()
        ))
        abono_id = cursor.lastrowid

        # Amortizar factura específica o las más antiguas del proveedor
        monto_restante_aplicar = monto_usd
        if compra_id:
            cursor.execute('SELECT id, saldo_pendiente_usd, monto_pagado_usd FROM compras_proveedor WHERE id = ?', (compra_id,))
            compras_a_pagar = [cursor.fetchone()]
        else:
            cursor.execute('''
                SELECT id, saldo_pendiente_usd, monto_pagado_usd
                FROM compras_proveedor
                WHERE proveedor_id = ? AND saldo_pendiente_usd > 0
                ORDER BY id ASC
            ''', (proveedor_id,))
            compras_a_pagar = cursor.fetchall()

        for c in compras_a_pagar:
            if not c or monto_restante_aplicar <= 0:
                break
            saldo = c['saldo_pendiente_usd']
            pago = min(saldo, monto_restante_aplicar)
            nuevo_saldo = round(saldo - pago, 2)
            nuevo_pagado = round(c['monto_pagado_usd'] + pago, 2)
            nuevo_estado = 'PAGADA' if nuevo_saldo <= 0.01 else 'PARCIAL'

            cursor.execute('''
                UPDATE compras_proveedor
                SET saldo_pendiente_usd = ?, monto_pagado_usd = ?, estado = ?
                WHERE id = ?
            ''', (nuevo_saldo, nuevo_pagado, nuevo_estado, c['id']))

            monto_restante_aplicar -= pago

        conn.commit()
        return abono_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_compras_proveedores(proveedor_id=None, limite=100):
    conn = get_db()
    query = '''
        SELECT c.*, p.nombre as proveedor_nombre, p.codigo as proveedor_codigo
        FROM compras_proveedor c
        JOIN proveedores p ON c.proveedor_id = p.id
    '''
    params = []
    if proveedor_id:
        query += ' WHERE c.proveedor_id = ?'
        params.append(proveedor_id)
    query += ' ORDER BY c.id DESC LIMIT ?'
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_abonos_proveedores(proveedor_id=None, limite=100):
    conn = get_db()
    query = '''
        SELECT a.*, p.nombre as proveedor_nombre, p.codigo as proveedor_codigo, c.numero_factura
        FROM abonos_proveedor a
        JOIN proveedores p ON a.proveedor_id = p.id
        LEFT JOIN compras_proveedor c ON a.compra_id = c.id
    '''
    params = []
    if proveedor_id:
        query += ' WHERE a.proveedor_id = ?'
        params.append(proveedor_id)
    query += ' ORDER BY a.id DESC LIMIT ?'
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ================= REPORTE DE ESTADÍSTICAS Y FINANZAS =================

def get_estadisticas_completas():
    conn = get_db()
    cursor = conn.cursor()
    tasa = get_tasa_dolar()
    hoy_str = datetime.now().strftime('%Y-%m-%d')
    mes_actual_str = datetime.now().strftime('%Y-%m')

    # 1. Total Ventas Reales (Solo COMPLETADAS)
    cursor.execute('''
        SELECT COALESCE(SUM(total_usd), 0), COALESCE(SUM(total_bs), 0), COUNT(*)
        FROM ventas
        WHERE estado = 'COMPLETADA'
    ''')
    r_ventas_total = cursor.fetchone()
    total_ventas_usd = r_ventas_total[0]
    total_ventas_bs = r_ventas_total[1]
    cant_ventas_reales = r_ventas_total[2]

    # 2. Ventas del mes actual
    cursor.execute('''
        SELECT COALESCE(SUM(total_usd), 0), COALESCE(SUM(total_bs), 0), COUNT(*)
        FROM ventas
        WHERE estado = 'COMPLETADA' AND fecha LIKE ?
    ''', (f"{mes_actual_str}%",))
    r_ventas_mes = cursor.fetchone()
    ventas_mes_usd = r_ventas_mes[0]
    ventas_mes_bs = r_ventas_mes[1]
    cant_ventas_mes = r_ventas_mes[2]

    # 3. Costo Total de Mercancía Vendida (COGS) en Ventas Reales
    # Calculado con el precio_costo que tenía la prenda vendida
    cursor.execute('''
        SELECT COALESCE(SUM(vd.cantidad * p.precio_costo), 0)
        FROM venta_detalles vd
        JOIN ventas v ON vd.venta_id = v.id
        JOIN prendas p ON vd.prenda_id = p.id
        WHERE v.estado = 'COMPLETADA'
    ''')
    costo_mercancia_vendida_usd = cursor.fetchone()[0]

    # 4. Ganancia Bruta Real
    ganancia_neta_usd = round(total_ventas_usd - costo_mercancia_vendida_usd, 2)
    ganancia_neta_bs = round(ganancia_neta_usd * tasa, 2)
    margen_ganancia_pct = round((ganancia_neta_usd / total_ventas_usd * 100), 1) if total_ventas_usd > 0 else 0.0

    # 5. Ventas Anuladas / Pérdidas potenciales registradas
    cursor.execute('''
        SELECT COALESCE(SUM(total_usd), 0), COUNT(*)
        FROM ventas
        WHERE estado = 'ANULADA'
    ''')
    r_anuladas = cursor.fetchone()
    ventas_anuladas_usd = r_anuladas[0]
    cant_ventas_anuladas = r_anuladas[1]

    # 6. Cuentas por Pagar a Proveedores
    cursor.execute('''
        SELECT 
            COALESCE(SUM(monto_total_usd), 0),
            COALESCE(SUM(monto_pagado_usd), 0),
            COALESCE(SUM(saldo_pendiente_usd), 0)
        FROM compras_proveedor
    ''')
    r_compras = cursor.fetchone()
    total_compras_usd = r_compras[0]
    total_abonos_usd = r_compras[1]
    deuda_proveedores_usd = r_compras[2]
    deuda_proveedores_bs = round(deuda_proveedores_usd * tasa, 2)

    # 7. Inventario actual valorizado a costo y a venta
    cursor.execute('''
        SELECT 
            COALESCE(SUM(stock), 0),
            COALESCE(SUM(stock * precio_costo), 0),
            COALESCE(SUM(stock * precio_venta), 0)
        FROM prendas
        WHERE activo = 1
    ''')
    r_inv = cursor.fetchone()
    total_piezas_stock = r_inv[0]
    costo_inventario_usd = r_inv[1]
    valor_venta_inventario_usd = r_inv[2]
    ganancia_potencial_inventario_usd = round(valor_venta_inventario_usd - costo_inventario_usd, 2)

    # 8. Ventas agrupadas por Categoría
    cursor.execute('''
        SELECT p.categoria, SUM(vd.cantidad) as piezas, SUM(vd.subtotal_usd) as total_usd
        FROM venta_detalles vd
        JOIN ventas v ON vd.venta_id = v.id
        JOIN prendas p ON vd.prenda_id = p.id
        WHERE v.estado = 'COMPLETADA'
        GROUP BY p.categoria
        ORDER BY total_usd DESC
    ''')
    ventas_por_categoria = [dict(r) for r in cursor.fetchall()]

    # 9. Ventas por Método de Pago
    cursor.execute('''
        SELECT metodo_pago, COUNT(*) as cantidad, SUM(total_usd) as total_usd, SUM(total_bs) as total_bs
        FROM ventas
        WHERE estado = 'COMPLETADA'
        GROUP BY metodo_pago
        ORDER BY total_usd DESC
    ''')
    ventas_por_metodo = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        'tasa_dolar': tasa,
        'total_ventas_usd': total_ventas_usd,
        'total_ventas_bs': total_ventas_bs,
        'cant_ventas_reales': cant_ventas_reales,
        'ventas_mes_usd': ventas_mes_usd,
        'ventas_mes_bs': ventas_mes_bs,
        'cant_ventas_mes': cant_ventas_mes,
        'costo_mercancia_vendida_usd': costo_mercancia_vendida_usd,
        'ganancia_neta_usd': ganancia_neta_usd,
        'ganancia_neta_bs': ganancia_neta_bs,
        'margen_ganancia_pct': margen_ganancia_pct,
        'ventas_anuladas_usd': ventas_anuladas_usd,
        'cant_ventas_anuladas': cant_ventas_anuladas,
        'total_compras_usd': total_compras_usd,
        'total_abonos_usd': total_abonos_usd,
        'deuda_proveedores_usd': deuda_proveedores_usd,
        'deuda_proveedores_bs': deuda_proveedores_bs,
        'total_piezas_stock': total_piezas_stock,
        'costo_inventario_usd': costo_inventario_usd,
        'valor_venta_inventario_usd': valor_venta_inventario_usd,
        'ganancia_potencial_inventario_usd': ganancia_potencial_inventario_usd,
        'ventas_por_categoria': ventas_por_categoria,
        'ventas_por_metodo': ventas_por_metodo
    }

# Métricas para el Dashboard
def get_dashboard_kpis():
    conn = get_db()
    cursor = conn.cursor()
    tasa = get_tasa_dolar()
    hoy_str = datetime.now().strftime('%Y-%m-%d')

    # Total de prendas activas y stock
    cursor.execute('SELECT COUNT(*), COALESCE(SUM(stock), 0), COALESCE(SUM(stock * precio_venta), 0) FROM prendas WHERE activo = 1')
    r_prendas = cursor.fetchone()
    total_modelos = r_prendas[0]
    total_unidades = r_prendas[1]
    valor_inventario_usd = r_prendas[2]
    valor_inventario_bs = round(valor_inventario_usd * tasa, 2)

    # Prendas en stock crítico o agotadas
    cursor.execute('SELECT COUNT(*) FROM prendas WHERE activo = 1 AND stock <= stock_minimo')
    total_stock_bajo = cursor.fetchone()[0]

    # Ventas de hoy (reales)
    cursor.execute('''
        SELECT COALESCE(SUM(total_usd), 0), COALESCE(SUM(total_bs), 0), COUNT(*)
        FROM ventas
        WHERE estado = 'COMPLETADA' AND fecha LIKE ?
    ''', (f"{hoy_str}%",))
    r_ventas_hoy = cursor.fetchone()
    ventas_hoy_usd = r_ventas_hoy[0]
    ventas_hoy_bs = r_ventas_hoy[1]
    total_ventas_hoy = r_ventas_hoy[2]

    # Prenda más vendida (top 5 histórico)
    cursor.execute('''
        SELECT vd.nombre, vd.talla, vd.color, SUM(vd.cantidad) as total_vendido
        FROM venta_detalles vd
        JOIN ventas v ON vd.venta_id = v.id
        WHERE v.estado = 'COMPLETADA'
        GROUP BY vd.prenda_id
        ORDER BY total_vendido DESC
        LIMIT 5
    ''')
    top_prendas = [dict(r) for r in cursor.fetchall()]

    # Prendas en alerta de stock bajo
    cursor.execute('''
        SELECT id, codigo, nombre, categoria, talla, color, stock, stock_minimo, precio_venta
        FROM prendas
        WHERE activo = 1 AND stock <= stock_minimo
        ORDER BY stock ASC
        LIMIT 8
    ''')
    alertas_stock = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        'tasa_dolar': tasa,
        'total_modelos': total_modelos,
        'total_unidades': total_unidades,
        'valor_inventario_usd': valor_inventario_usd,
        'valor_inventario_bs': valor_inventario_bs,
        'total_stock_bajo': total_stock_bajo,
        'ventas_hoy_usd': ventas_hoy_usd,
        'ventas_hoy_bs': ventas_hoy_bs,
        'total_ventas_hoy': total_ventas_hoy,
        'top_prendas': top_prendas,
        'alertas_stock': alertas_stock
    }

# Funciones de Autenticación y Usuarios
def verificar_usuario(username, password):
    """
    Verifica credenciales de usuario con contraseña obligatoria.
    """
    if not username or not password:
        return None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE LOWER(username) = ?', (username.strip().lower(),))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def verificar_admin_password(password):
    """
    Verifica si una contraseña corresponde a un usuario con rol 'admin'.
    Permite autorizar acciones críticas (anular ventas, purgar registros, etc.).
    """
    if not password:
        return False

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM usuarios WHERE rol = 'admin'")
    admins = cursor.fetchall()
    conn.close()

    for adm in admins:
        if check_password_hash(adm['password_hash'], password):
            return True
    return False

def get_todos_usuarios():
    conn = get_db()
    rows = conn.execute('SELECT id, username, nombre, rol FROM usuarios ORDER BY id ASC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def crear_usuario(username, password, nombre, rol='cajero'):
    conn = get_db()
    cursor = conn.cursor()
    p_hash = generate_password_hash(password)
    cursor.execute(
        'INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?, ?, ?, ?)',
        (username.strip().lower(), p_hash, nombre.strip(), rol)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def cambiar_password(usuario_id, nueva_password):
    conn = get_db()
    p_hash = generate_password_hash(nueva_password)
    conn.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (p_hash, usuario_id))
    conn.commit()
    conn.close()

