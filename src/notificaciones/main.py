from fastapi import FastAPI

app = FastAPI(title="Servicio de Notificaciones")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/enviar")
async def enviar(payload: dict):
    return {"status": "Correo enviado con éxito"}