### 1. Análisis del Fallo

El `main.py` actual solo inicializa FastAPI e incluye el router `router_ia`, pero no impone ninguna validación global sobre el tamaño del payload.  
Según el issue, el endpoint `/ConsultarIA` recibe textos demasiado grandes y termina provocando un error interno 500. Esto sugiere que la validación se está haciendo tarde o no existe, y el error emerge dentro del procesamiento de la ruta o al invocar el modelo.

La solución correcta es validar **antes** de procesar la petición y devolver un **HTTP 400** cuando el texto supere un límite razonable, evitando así fallos internos y reduciendo el riesgo de DoS.

---

### 2. Propuesta de Código

```python
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, field_validator
from anthropic import AsyncAnthropic
from src.routers.claudeModels import router as router_ia

MAX_TEXT_LENGTH = 5000

class ConsultarIARequest(BaseModel):
    texto: str

    @field_validator("texto")
    @classmethod
    def validar_tamano_texto(cls, v: str) -> str:
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(
                f"El texto excede el límite permitido de {MAX_TEXT_LENGTH} caracteres."
            )
        return v

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="AI Arena Router API",
    description="API para evaluar y comparar respuestas de múltiples LLMs usando un Juez de IA."
)

# Inyección de las rutas modulares de IA
app.include_router(router_ia)

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    raise HTTPException(status_code=400, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

> Nota: si `/ConsultarIA` usa otro modelo de entrada, la validación debe aplicarse en ese esquema específico dentro del router `src/routers/claudeModels.py`. Ahí es donde realmente debe bloquearse el texto excesivo.

---

### 3. Prueba Unitaria

```python
import pytest
from pydantic import BaseModel, ValidationError, field_validator

MAX_TEXT_LENGTH = 5000

class ConsultarIARequest(BaseModel):
    texto: str

    @field_validator("texto")
    @classmethod
    def validar_tamano_texto(cls, v: str) -> str:
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(
                f"El texto excede el límite permitido de {MAX_TEXT_LENGTH} caracteres."
            )
        return v

def test_texto_valido_no_falla():
    data = ConsultarIARequest(texto="hola" * 100)
    assert data.texto == "hola" * 100

def test_texto_excesivamente_largo_falla():
    texto_largo = "a" * (MAX_TEXT_LENGTH + 1)

    with pytest.raises(ValidationError) as exc_info:
        ConsultarIARequest(texto=texto_largo)

    assert "excede el límite permitido" in str(exc_info.value)
```

Si quieres, puedo proponerte también el **cambio exacto dentro de `src/routers/claudeModels.py`** para que la validación quede aplicada en el endpoint real.