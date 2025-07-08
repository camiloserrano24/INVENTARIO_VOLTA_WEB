from flask import Flask, render_template, request, redirect, url_for
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

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
# INICIO
# ------------------------

@app.route('/')
def index():
    return render_template("index.html")

# ------------------------
# PRODUCTOS
# ------------------------

@app.route('/productos')
def productos():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sku, nombre, descripcion, categoria, unidad_medida, stock_actual FROM Productos ORDER BY sku;")
            productos = cur.fetchall()
    return render_template("productos.html", productos=productos)

@app.route('/crear_producto', methods=["POST"])
def crear_producto():
    data = request.form
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO Productos (sku, nombre, descripcion, categoria, unidad_medida, stock_actual, fecha_actualizado)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (sku) DO UPDATE 
                SET nombre=EXCLUDED.nombre,
                    descripcion=EXCLUDED.descripcion,
                    categoria=EXCLUDED.categoria,
                    unidad_medida=EXCLUDED.unidad_medida,
                    stock_actual=EXCLUDED.stock_actual,
                    fecha_actualizado=CURRENT_TIMESTAMP;
            """, (data["sku"], data["nombre"], data["descripcion"], data["categoria"], data["unidad"], int(data["stock"])))
    return redirect(url_for("productos"))

@app.route('/eliminar_producto/<sku>')
def eliminar_producto(sku):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Movimientos WHERE sku=%s;", (sku,))
            cur.execute("DELETE FROM Productos WHERE sku=%s;", (sku,))
    return redirect(url_for("productos"))

# ------------------------
# MOVIMIENTOS
# ------------------------

@app.route('/movimientos')
def movimientos():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, sku, cantidad, tipo_movimiento, fecha_movimiento FROM Movimientos ORDER BY fecha_movimiento DESC;")
            movimientos = cur.fetchall()
    return render_template("movimientos.html", movimientos=movimientos)

@app.route('/registrar_movimiento', methods=["POST"])
def registrar_movimiento():
    data = request.form
    tipo = data["tipo"]
    cantidad = int(data["cantidad"])
    sku = data["sku"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Actualizar stock
            signo = 1 if tipo == "entrada" else -1
            cur.execute("UPDATE Productos SET stock_actual = stock_actual + %s, fecha_actualizado=CURRENT_TIMESTAMP WHERE sku=%s;", (cantidad*signo, sku))
            # Registrar movimiento
            cur.execute("INSERT INTO Movimientos (sku, cantidad, tipo_movimiento, fecha_movimiento) VALUES (%s, %s, %s, CURRENT_TIMESTAMP);", (sku, cantidad, tipo))
    return redirect(url_for("movimientos"))

@app.route('/eliminar_movimiento/<int:id>')
def eliminar_movimiento(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Revertir stock
            cur.execute("SELECT sku, cantidad, tipo_movimiento FROM Movimientos WHERE id=%s;", (id,))
            row = cur.fetchone()
            if row:
                sku, cantidad, tipo = row
                revert = -cantidad if tipo == "entrada" else cantidad
                cur.execute("UPDATE Productos SET stock_actual = stock_actual + %s, fecha_actualizado=CURRENT_TIMESTAMP WHERE sku=%s;", (revert, sku))
            # Borrar movimiento
            cur.execute("DELETE FROM Movimientos WHERE id=%s;", (id,))
    return redirect(url_for("movimientos"))

# ------------------------
# PROVEEDORES
# ------------------------

@app.route('/proveedores')
def proveedores():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, contacto, telefono, email FROM Proveedores ORDER BY id;")
            proveedores = cur.fetchall()
    return render_template("proveedores.html", proveedores=proveedores)

@app.route('/crear_proveedor', methods=["POST"])
def crear_proveedor():
    data = request.form
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO Proveedores (nombre, contacto, telefono, email) VALUES (%s, %s, %s, %s);",
                        (data["nombre"], data["contacto"], data["telefono"], data["email"]))
    return redirect(url_for("proveedores"))

@app.route('/eliminar_proveedor/<int:id>')
def eliminar_proveedor(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Proveedores WHERE id=%s;", (id,))
    return redirect(url_for("proveedores"))

# ------------------------
# REPORTES
# ------------------------

@app.route('/reportes')
def reportes():
    # Ejemplo simple de pandas + matplotlib
    with get_connection() as conn:
        df = pd.read_sql("SELECT sku, nombre, stock_actual FROM Productos", conn)
    if not df.empty:
        plt.figure(figsize=(8,4))
        plt.bar(df["sku"], df["stock_actual"])
        plt.title("Stock actual por SKU")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("static/reporte_stock.png")
    return render_template("reportes.html")

# ------------------------

if __name__ == "__main__":
    app.run(debug=True)
