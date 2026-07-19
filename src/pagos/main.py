from fastapi import FastAPI
import asyncio

app = FastAPI(title="Servicio de Pagos")

# Estado global para activar caos
caos_activo = False

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/config")
def configurar_caos(payload: dict):
    global caos_activo
    caos_activo = payload.get("latencia", False)
    return {"caos_activo": caos_activo}

@app.post("/pagar")
async def pagar(payload: dict):
    if caos_activo:
        await asyncio.sleep(20)  # Simula colgado de 20 segundos
    return {"transaccion_id": "TX-998877", "estado": "aprobado"}