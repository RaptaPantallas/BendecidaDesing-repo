import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventario.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

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

    # Configuraciones iniciales por defecto si no existen
    config_defaults = {
        'nombre_tienda': 'Euler Moda & Estilo',
        'telefono': '+58 412 1234567',
        'direccion': 'Centro Comercial Galería, Nivel 1, Local 14',
        'tasa_dolar': '65.50',
        'moneda_principal': 'USD',
        'moneda_secundaria': 'VES',
        'simbolo_principal': '$',
        'simbolo_secundaria': 'Bs.',
        'mensaje_recibo': '¡Gracias por apoyar el talento y la moda! Cambios dentro de los 3 días hábiles.'
    }

    for k, v in config_defaults.items():
        cursor.execute('INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)', (k, v))

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
    query = 'SELECT * FROM prendas WHERE 1=1'
    params = []

    if solo_activas:
        query += ' AND activo = 1'
    
    if categoria and categoria != 'TODAS':
        query += ' AND categoria = ?'
        params.append(categoria)

    if filtro_busqueda:
        query += ' AND (codigo LIKE ? OR nombre LIKE ? OR color LIKE ?)'
        like_term = f"%{filtro_busqueda}%"
        params.extend([like_term, like_term, like_term])

    if solo_stock_bajo:
        query += ' AND stock <= stock_minimo'

    query += ' ORDER BY stock ASC, id DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_prenda_por_id(prenda_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM prendas WHERE id = ?', (prenda_id,)).fetchone()
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
    cursor.execute('''
        INSERT INTO prendas (codigo, nombre, categoria, talla, color, precio_costo, precio_venta, stock, stock_minimo, fecha_creacion, imagen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        datos.get('imagen', '').strip()
    ))
    nuevo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id

def actualizar_prenda(prenda_id, datos):
    conn = get_db()
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
                imagen = ?
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
                stock_minimo = ?
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

def get_ventas_recientes(limite=100):
    conn = get_db()
    rows = conn.execute('''
        SELECT v.*, COUNT(vd.id) as total_items, SUM(vd.cantidad) as total_piezas
        FROM ventas v
        LEFT JOIN venta_detalles vd ON v.id = vd.venta_id
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

    # Ventas de hoy
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
