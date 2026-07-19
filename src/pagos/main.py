from fastapi import FastAPI, HTTPException
import asyncio
import random

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
    # 1. Simulación de caos forzado mediante script/configuración
    if caos_activo:
        await asyncio.sleep(20)  # Simula colgado de 20 segundos
        return {"transaccion_id": "TX-CAOS", "estado": "aprobado"}

    # 2. Simulación de comportamiento realista autónomo (latencia y fallos aleatorios)
    prob = random.random()
    
    if prob < 0.10:
        # 10% de probabilidad de fallo aleatorio (Error del servidor)
        raise HTTPException(status_code=500, detail="Error interno en la pasarela de pagos (Fallo aleatorio).")
    
    elif prob < 0.20:
        # 10% de probabilidad de latencia alta variable (entre 4.0 y 5.5 segundos)
        # Esto superará el timeout de 3.0s de Reservas, activando el Circuit Breaker.
        delay = random.uniform(4.0, 5.5)
        await asyncio.sleep(delay)
    
    else:
        # 80% de casos exitosos con latencia variable normal baja (entre 0.1 y 0.6 segundos)
        delay = random.uniform(0.1, 0.6)
        await asyncio.sleep(delay)

    return {"transaccion_id": "TX-998877", "estado": "aprobado"}