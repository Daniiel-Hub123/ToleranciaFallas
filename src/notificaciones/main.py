from fastapi import FastAPI, HTTPException
import asyncio
import random

app = FastAPI(title="Servicio de Notificaciones")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/enviar")
async def enviar(payload: dict):
    # Simulación de comportamiento realista autónomo (latencia y fallos aleatorios)
    prob = random.random()
    
    if prob < 0.10:
        # 10% de probabilidad de fallo de entrega de correo
        raise HTTPException(status_code=502, detail="Error de conexión SMTP / Gateway de correo no responde (Fallo aleatorio).")
        
    elif prob < 0.20:
        # 10% de probabilidad de latencia de red alta (entre 2.0 y 3.0 segundos)
        # Esto superará el timeout de 1.5s de Reservas, forzando la lógica de degradación elegante.
        delay = random.uniform(2.0, 3.0)
        await asyncio.sleep(delay)
        
    else:
        # 80% de casos exitosos con latencia normal (entre 0.05 y 0.3 segundos)
        delay = random.uniform(0.05, 0.3)
        await asyncio.sleep(delay)
        
    return {"status": "Correo enviado con éxito"}