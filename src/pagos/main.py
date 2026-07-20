from fastapi import FastAPI, HTTPException
import asyncio
import random

app = FastAPI(title="Servicio de Pagos")

# Modos de caos: "normal", "latencia" (20s), "aleatorio" (fallos autónomos)
modo_caos = "normal"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/config")
def configurar_caos(payload: dict):
    global modo_caos
    # Permite recibir "modo" ("normal", "latencia", "aleatorio")
    # Para mantener compatibilidad con scripts viejos, si mandan "latencia": true se activa el modo latencia.
    if payload.get("latencia") is True:
        modo_caos = "latencia"
    elif payload.get("latencia") is False:
        modo_caos = "normal"
    else:
        modo_caos = payload.get("modo", "normal")
        
    return {"modo_caos": modo_caos}

@app.post("/pagar")
async def pagar(payload: dict):
    # 1. Modo Latencia Forzada (Fallo 2 - Pasarela Lenta)
    if modo_caos == "latencia":
        await asyncio.sleep(20)  # Simula colgado de 20 segundos
        return {"transaccion_id": "TX-CAOS", "estado": "aprobado"}

    # 2. Modo Aleatorio Autónomo (Opcional)
    elif modo_caos == "aleatorio":
        prob = random.random()
        if prob < 0.10:
            raise HTTPException(status_code=500, detail="Error interno en la pasarela de pagos (Fallo aleatorio).")
        elif prob < 0.20:
            delay = random.uniform(4.0, 5.5)
            await asyncio.sleep(delay)
        else:
            delay = random.uniform(0.1, 0.6)
            await asyncio.sleep(delay)

    # 3. Modo Normal (Por defecto - Seguro para probar otros fallos)
    else:
        # Respuesta exitosa inmediata (entre 0.05 y 0.15 segundos)
        await asyncio.sleep(random.uniform(0.05, 0.15))

    return {"transaccion_id": "TX-998877", "estado": "aprobado"}