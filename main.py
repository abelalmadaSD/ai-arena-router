from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from anthropic import AsyncAnthropic
from src.routers.claudeModels import router as router_ia

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="AI Arena Router API",
    description="API para evaluar y comparar respuestas de múltiples LLMs usando un Juez de IA."
)

# Inyección de las rutas modulares de IA
app.include_router(router_ia)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)