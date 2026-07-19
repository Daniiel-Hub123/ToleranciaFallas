from fastapi import FastAPI
app = FastAPI(title="Servicio de Inventario")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/verificar")
async def verificar(payload: dict):
    return {"disponible": True}