from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from anthropic import AsyncAnthropic
from src.routers.claudeModels import router as router_ia
from src.routers.auth import router as router_auth

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="AI Arena Router API",
    description="API para evaluar y comparar respuestas de múltiples LLMs usando un Juez de IA."
)

# Inyección de las rutas modulares de IA y autenticación
app.include_router(router_auth)
app.include_router(router_ia)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)