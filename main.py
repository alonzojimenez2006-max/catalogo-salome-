from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import json
import os

app = FastAPI(title="API Confecciones Salomé")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductoAdmin(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    precio_combo: float = 0.0
    imgs: list[str]
    colores: list[str]
    tallas: list[str]
    unidades: int = 1

class EstadoCatalogo(BaseModel):
    estado: str

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_tqQWyp0OHgd4@ep-royal-dust-ax6ybowm.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                descripcion TEXT,
                precio REAL,
                precio_combo REAL DEFAULT 0.0,
                imgs TEXT,
                colores TEXT,
                tallas TEXT,
                unidades INTEGER DEFAULT 1
            )
        ''')
        
        # --- NUEVO: TABLA DE CONFIGURACIÓN ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                estado TEXT
            )
        ''')
        cursor.execute("SELECT COUNT(*) FROM configuracion")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO configuracion (id, estado) VALUES (1, 'activo')")
        # -------------------------------------

        conn.commit()
        # Parche para actualizar tabla existente sin borrar datos
        try:
            cursor.execute("ALTER TABLE productos ADD COLUMN precio_combo REAL DEFAULT 0.0")
            conn.commit()
        except Exception:
            conn.rollback() 
        cursor.close()
        conn.close()
    except Exception as e:
        print("Esperando configuración de base de datos en la nube...")

init_db()

@app.get("/api/productos")
def obtener_catalogo():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, descripcion, precio, precio_combo, imgs, colores, tallas, unidades FROM productos ORDER BY id ASC")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()

    catalogo = []
    for fila in filas:
        catalogo.append({
            "id": fila[0],
            "nombre": fila[1],
            "descripcion": fila[2],
            "precio": fila[3],
            "precio_combo": fila[4] if fila[4] is not None else 0.0,
            "imgs": json.loads(fila[5]),
            "colores": json.loads(fila[6]),
            "tallas": json.loads(fila[7]),
            "unidades": fila[8]
        })
    return catalogo

@app.post("/api/productos")
def crear_producto(producto: ProductoAdmin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO productos (nombre, descripcion, precio, precio_combo, imgs, colores, tallas, unidades)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        producto.nombre, producto.descripcion, producto.precio, producto.precio_combo,
        json.dumps(producto.imgs), json.dumps(producto.colores), json.dumps(producto.tallas), 
        producto.unidades
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensaje": "Producto guardado exitosamente"}

@app.put("/api/productos/{producto_id}")
def actualizar_producto(producto_id: int, producto: ProductoAdmin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE productos 
        SET nombre=%s, descripcion=%s, precio=%s, precio_combo=%s, imgs=%s, colores=%s, tallas=%s, unidades=%s
        WHERE id=%s
    ''', (
        producto.nombre, producto.descripcion, producto.precio, producto.precio_combo,
        json.dumps(producto.imgs), json.dumps(producto.colores), json.dumps(producto.tallas), 
        producto.unidades, producto_id
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensaje": "Producto actualizado exitosamente"}

@app.delete("/api/productos/{producto_id}")
def eliminar_producto(producto_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM productos WHERE id=%s', (producto_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensaje": "Producto eliminado exitosamente"}

@app.get("/api/estado")
def obtener_estado():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT estado FROM configuracion WHERE id = 1")
    resultado = cursor.fetchone()
    estado = resultado[0] if resultado else 'activo'
    cursor.close()
    conn.close()
    return {"estado": estado}

@app.put("/api/estado")
def actualizar_estado(nuevo_estado: EstadoCatalogo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE configuracion SET estado = %s WHERE id = 1", (nuevo_estado.estado,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensaje": "Estado actualizado"}

@app.get("/")
def pagina_principal():
    return FileResponse("index.html")

@app.get("/admin.html")
def pagina_admin():
    return FileResponse("admin.html")

@app.get("/visor")
def pagina_visor():
    return FileResponse("visor.html")

@app.get("/logo.png")
def servir_logo():
    return FileResponse("logo.png")
