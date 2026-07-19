from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import time

app = FastAPI(title="Servicio de Inventario")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@database:5432/inventario_db")

# Inicializar Base de Datos PostgreSQL de forma tolerante a fallos
def init_db():
    base_url, db_name = DATABASE_URL.rsplit("/", 1)
    default_url = f"{base_url}/postgres"
    
    # 1. Asegurar existencia de 'inventario_db'
    conn = None
    for attempt in range(10):
        try:
            conn = psycopg2.connect(default_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(f"CREATE DATABASE {db_name}")
            cursor.close()
            conn.close()
            break
        except Exception as e:
            print(f"[DB STARTUP] Esperando a PostgreSQL (Intento {attempt+1}/10)... Error: {e}")
            time.sleep(3)
            
    # 2. Conectar a 'inventario_db' y crear tablas/semillas
    for attempt in range(5):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asientos (
                    id VARCHAR(50) PRIMARY KEY,
                    disponible BOOLEAN DEFAULT TRUE
                )
            """)
            conn.commit()
            
            # Verificar si está vacío y precargar datos semilla (Asientos 1 al 10)
            cursor.execute("SELECT COUNT(*) FROM asientos")
            count = cursor.fetchone()[0]
            if count == 0:
                print("[DB STARTUP] Insertando asientos semilla...")
                for i in range(1, 11):
                    cursor.execute(
                        "INSERT INTO asientos (id, disponible) VALUES (%s, %s)",
                        (f"asiento_{i}", True)
                    )
                conn.commit()
                
            cursor.close()
            conn.close()
            print("[DB STARTUP] Base de datos de Inventario inicializada con éxito.")
            break
        except Exception as e:
            print(f"[DB STARTUP] Error al inicializar esquema (Intento {attempt+1}/5): {e}")
            time.sleep(3)

init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/verificar")
async def verificar(payload: dict):
    asiento_id = payload.get("asiento_id")
    if not asiento_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'asiento_id' en la petición.")
        
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT disponible FROM asientos WHERE id = %s", (asiento_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            # Asiento no existe
            return {"disponible": False, "message": "El asiento solicitado no existe."}
            
        disponible = row[0]
        return {"asiento_id": asiento_id, "disponible": disponible}
        
    except Exception as e:
        print(f"[DB ERROR] Error al verificar stock de asiento: {e}")
        raise HTTPException(status_code=500, detail="Error interno al conectar a la base de datos de inventario.")