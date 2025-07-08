from flask import Flask, render_template, request, redirect, url_for
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(
        dbname="railway",
        user="postgres",
        password="vBzfohtTpABvinuwUiSsAfGmxoaxdZQa",
        host="hopper.proxy.rlwy.net",
        port=25823,
        sslmode="require"
    )

# ------------------------
# INDEX
# ------------------------

@app.route('/')
def index():
    return render_template("index.html")

# ------------------------
# PRODUCTOS
# ------------------------

@app.route('/productos')
def productos():
    search = request.args.get('search', '').strip()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if search:
                cur.execute(
                    """
                    SELECT sku, nombre, descripcion, categoria, unidad_medida, stock_actual
                    FROM Productos
                    WHERE sku ILIKE %s OR nombre ILIKE %s
                    ORDER BY sku;
                    """,
                    (f'%{search}%', f'%{search}%')
                )
            else:
                cur.execute(
                    """
                    SELECT sku, nombre, descripcion, categoria, unidad_medida, stock_actual
                    FROM Productos ORDER BY sku;
                    """
                )
            productos = cur.fetchall()
    return render_template(
        "productos.html",
        productos=productos,
        search_query=search
    )

@app.route('/productos/create', methods=['GET', 'POST'])
def crear_producto():
    if request.method == 'POST':
        data = request.form
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO Productos
                      (sku, nombre, descripcion, categoria, unidad_medida, stock_actual, fecha_actualizado)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                    """,
                    (
                        data['sku'], data['nombre'], data['descripcion'],
                        data['categoria'], data['unidad'], int(data['stock'])
                    )
                )
                conn.commit()
        return redirect(url_for('productos'))
    # GET -> form vacío
    return render_template(
        "producto_form.html",
        action='Crear',
        producto=None
    )

@app.route('/productos/<sku>/edit', methods=['GET', 'POST'])
def editar_producto(sku):
    if request.method == 'POST':
        data = request.form
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE Productos
                    SET nombre=%s,
                        descripcion=%s,
                        categoria=%s,
                        unidad_medida=%s,
                        stock_actual=%s,
                        fecha_actualizado=CURRENT_TIMESTAMP
                    WHERE sku=%s;
                    """,
                    (
                        data['nombre'], data['descripcion'],
                        data['categoria'], data['unidad'],
                        int(data['stock']), sku
                    )
                )
                conn.commit()
        return redirect(url_for('productos'))
    # GET -> cargar datos
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sku, nombre, descripcion, categoria, unidad_medida, stock_actual
                FROM Productos WHERE sku=%s;
                """, (sku,)
            )
            producto = cur.fetchone()
    return render_template(
        "producto_form.html",
        action='Editar',
        producto=producto
    )

@app.route('/productos/delete', methods=['POST'])
def eliminar_productos():
    skus = request.form.getlist('selected_skus')
    if skus:
        placeholders = ','.join(['%s'] * len(skus))
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM Movimientos WHERE sku IN ({placeholders});",
                    skus
                )
                cur.execute(
                    f"DELETE FROM Productos WHERE sku IN ({placeholders});",
                    skus
                )
                conn.commit()
    return redirect(url_for('productos'))

# ------------------------
# MOVIMIENTOS
# ------------------------

@app.route('/movimientos')
def movimientos():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, sku, cantidad, tipo_movimiento, fecha_movimiento "
                "FROM Movimientos ORDER BY fecha_movimiento DESC;"
            )
            movimientos = cur.fetchall()
    return render_template("movimientos.html", movimientos=movimientos)

@app.route('/registrar_movimiento', methods=['POST'])
def registrar_movimiento():
    data = request.form
    tipo = data['tipo']
    cantidad = int(data['cantidad'])
    sku = data['sku']
    with get_connection() as conn:
        with conn.cursor() as cur:
            signo = 1 if tipo == 'entrada' else -1
            cur.execute(
                "UPDATE Productos SET stock_actual = stock_actual + %s, fecha_actualizado=CURRENT_TIMESTAMP WHERE sku=%s;",
                (cantidad*signo, sku)
            )
            cur.execute(
                "INSERT INTO Movimientos (sku, cantidad, tipo_movimiento, fecha_movimiento) VALUES (%s, %s, %s, CURRENT_TIMESTAMP);",
                (sku, cantidad, tipo)
            )
    return redirect(url_for('movimientos'))

@app.route('/eliminar_movimiento/<int:id>')
def eliminar_movimiento(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sku, cantidad, tipo_movimiento FROM Movimientos WHERE id=%s;",
                (id,)
            )
            row = cur.fetchone()
            if row:
                sku_db, cantidad_db, tipo_db = row
                revert = -cantidad_db if tipo_db == 'entrada' else cantidad_db
                cur.execute(
                    "UPDATE Productos SET stock_actual = stock_actual + %s, fecha_actualizado=CURRENT_TIMESTAMP WHERE sku=%s;",
                    (revert, sku_db)
                )
            cur.execute("DELETE FROM Movimientos WHERE id=%s;", (id,))
    return redirect(url_for('movimientos'))

# ------------------------
# PROVEEDORES
# ------------------------

@app.route('/proveedores')
def proveedores():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, contacto, telefono, email FROM Proveedores ORDER BY id;"
            )
            proveedores = cur.fetchall()
    return render_template("proveedores.html", proveedores=proveedores)

@app.route('/crear_proveedor', methods=['POST'])
def crear_proveedor():
    data = request.form
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO Proveedores (nombre, contacto, telefono, email) VALUES (%s, %s, %s, %s);",
                (data['nombre'], data['contacto'], data['telefono'], data['email'])
            )
            conn.commit()
    return redirect(url_for('proveedores'))

@app.route('/eliminar_proveedor/<int:id>')
def eliminar_proveedor(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Proveedores WHERE id=%s;", (id,))
            conn.commit()
    return redirect(url_for('proveedores'))

# ------------------------
# REPORTES
# ------------------------

@app.route('/reportes')
def reportes():
    with get_connection() as conn:
        df = pd.read_sql("SELECT sku, nombre, stock_actual FROM Productos", conn)
    if not df.empty:
        plt.figure(figsize=(8,4))
        plt.bar(df['sku'], df['stock_actual'])
        plt.title("Stock actual por SKU")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("static/reporte_stock.png")
    return render_template("reportes.html")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)