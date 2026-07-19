from fastapi import FastAPI, HTTPException
import httpx
import time
import asyncio
import sqlite3

app = FastAPI(title="Servicio de Reservas")

INVENTARIO_URL = "http://inventario-service:8000"
PAGOS_URL = "http://pagos-service:8000"
NOTIFICACIONES_URL = "http://notificaciones-service:8000"

# Inicializar Base de Datos SQLite (Persistencia de Datos por Servicio)
conn = sqlite3.connect("reservas.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservas (
        id TEXT PRIMARY KEY,
        asiento_id TEXT,
        estado TEXT
    )
""")
conn.commit()
conn.close()

# Estado básico para Circuit Breaker manual (Fallo 2: Pasarela Lenta)
circuit_breaker = {
    "state": "CLOSED",
    "failures": 0,
    "last_failure_time": 0,
    "failure_threshold": 3,
    "recovery_time": 30
}

def check_circuit():
    now = time.time()
    if circuit_breaker["state"] == "OPEN":
        if now - circuit_breaker["last_failure_time"] > circuit_breaker["recovery_time"]:
            circuit_breaker["state"] = "HALF-OPEN"
        else:
            raise HTTPException(status_code=503, detail="Circuit Breaker is OPEN. Payment gateway temporarily disabled.")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reservar")
async def crear_reserva(payload: dict):
    asiento_id = payload.get("asiento_id")
    
    # 1. VERIFICAR INVENTARIO (Con mecanismo de Reintentos - Fallo 1)
    inventario_ok = False
    for intento in range(3):
        try:
            async with httpx.AsyncClient() as client:
                res_inv = await client.post(f"{INVENTARIO_URL}/verificar", json={"asiento_id": asiento_id}, timeout=2.0)
                if res_inv.status_code == 200 and res_inv.json().get("disponible"):
                    inventario_ok = True
                    break
        except httpx.RequestError:
            await asyncio.sleep(1) # Delay de reintento simple asíncrono
            
    if not inventario_ok:
        raise HTTPException(status_code=500, detail="No se pudo contactar al inventario después de varios intentos.")

    # 2. PROCESAR PAGO (Con Circuit Breaker y Timeout corto - Fallo 2)
    check_circuit()
    async with httpx.AsyncClient() as client:
        try:
            # Timeout corto de 3 segundos para evitar colgar conexiones ante una pasarela lenta
            res_pago = await client.post(f"{PAGOS_URL}/pagar", json={"monto": 100}, timeout=3.0)
            res_pago.raise_for_status()
            
            if res_pago.status_code == 200:
                if circuit_breaker["state"] == "HALF-OPEN":
                    circuit_breaker["state"] = "CLOSED"
                    circuit_breaker["failures"] = 0
                
        except httpx.HTTPError:
            circuit_breaker["failures"] += 1
            circuit_breaker["last_failure_time"] = time.time()
            if circuit_breaker["failures"] >= circuit_breaker["failure_threshold"]:
                circuit_breaker["state"] = "OPEN"
            raise HTTPException(status_code=504, detail="La pasarela de pagos tarda demasiado. Operación cancelada para proteger el sistema (Circuit Breaker).")

    # Guardar en Base de Datos (Persistencia)
    reserva_id = f"RES-{int(time.time() * 1000)}"
    try:
        conn = sqlite3.connect("reservas.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reservas (id, asiento_id, estado) VALUES (?, ?, ?)", 
                       (reserva_id, asiento_id, "CONFIRMADA"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR]: No se pudo persistir la reserva en SQLite: {e}")

    # 3. NOTIFICACIÓN (Tratado como fallo no crítico - Fallo 5)
    notificacion_enviada = True
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{NOTIFICACIONES_URL}/enviar", json={"mensaje": f"Reserva {reserva_id} confirmada"}, timeout=1.5)
    except Exception as e:
        print(f"[FALLBACK LOG]: No se pudo enviar el correo de confirmación. Detalle: {e}")
        notificacion_enviada = False

    return {
        "status": "Reserva Completada",
        "reserva_id": reserva_id,
        "asiento_id": asiento_id,
        "notificacion_estado": "Enviada" if notificacion_enviada else "Pendiente de reenvío en background"
    }