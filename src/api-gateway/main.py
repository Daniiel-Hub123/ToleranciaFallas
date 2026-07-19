from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import time

app = FastAPI(title="API Gateway")
RESERVAS_SERVICE_URL = "http://reservas-service:8000"

# Rate Limiting simple en memoria (Fallo 3)
RATE_LIMIT = 10  # Máximo de peticiones por ventana
WINDOW_SIZE = 10  # Ventana en segundos
request_history = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    global request_history
    
    # Ignorar endpoints de salud para probes de Kubernetes
    if request.url.path == "/health":
        return await call_next(request)
        
    now = time.time()
    request_history = [t for t in request_history if now - t < WINDOW_SIZE]
    
    if len(request_history) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429, 
            content={"detail": "Too Many Requests - Rate Limit Exceeded"}
        )
    
    request_history.append(now)
    response = await call_next(request)
    return response

@app.post("/reservar")
async def proxy_reservar(payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{RESERVAS_SERVICE_URL}/reservar", json=payload, timeout=5.0)
            return response.json()
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=503, 
                content={"detail": f"Servicio de Reservas no disponible: {exc}"}
            )