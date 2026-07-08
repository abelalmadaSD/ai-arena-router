from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
import config
import json
from anthropic import AsyncAnthropic

app = FastAPI(
    title="AI Arena Router API",
    description="API para evaluar y comparar respuestas de múltiples LLMs usando un Juez de IA."
)

client = AsyncAnthropic()

MODELO_ECONOMICO = "claude-haiku-4-5-20251001"
MODELO_INTELIGENTE = "claude-sonnet-5"

class PromptRequest(BaseModel):
    prompt: str

async def optimizar_prompt(mensaje_usuario: str) -> str:
    """
    Toma la pregunta simple del usuario y la transforma en un prompt de ingeniería detallado.
    """
    system_prompt = (
        "Eres un Ingeniero de Prompts experto. Tu trabajo es reescribir la consulta del usuario "
        "para transformarla en una instrucción detallada, clara y de alta calidad técnica. "
        "Agrega estructura, solicita que se exploren subtemas importantes, pero mantén la esencia "
        "original de la pregunta. Devuelve ÚNICAMENTE el prompt mejorado sin introducciones."
    )

    response = await client.messages.create(
        model=MODELO_ECONOMICO, # Haiku es ideal y barato para expandir texto
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": mensaje_usuario}]
    )
    texto_respuesta = "".join([block.text for block in response.content if hasattr(block, 'text')])
    return texto_respuesta

async def definir_roles(mensaje_usuario: str) -> list:
    """
        Analiza el mensaje del usuario y selecciona dinámicamente los 3 mejores roles especializados.
    """
    system_prompt = (
        "Eres un enrutador de inteligencia artificial de alta precisión.\n"
        "Tu única tarea es leer el mensaje del usuario y elegir exactamente 3 roles especializados "
        "de la siguiente lista que sean los mejores y más variados para responderla:\n"
        "[Programador, Historiador, Poeta, Matemático, Abogado, Economista, Médico, Filósofo, Científico, Crítico de Cine]\n\n"
        "Debes responder ESTRICTAMENTE con un objeto JSON válido con el siguiente formato:\n"
        '{"expertos": ["Rol1", "Rol2", "Rol3"]}\n'
        "No agregues texto extra, ni saludos, ni explicaciones, solo el JSON puro."
    )

    response = await client.messages.create(
        model=MODELO_ECONOMICO,
        max_tokens=150,
        system=system_prompt,
        messages=[{"role": "user", "content": mensaje_usuario}]
    )
    
    texto_respuesta = "".join([block.text for block in response.content if hasattr(block, 'text')])
    
    try:
        # Parseamos el JSON devuelto por Claude
        datos = json.loads(texto_respuesta)
        return datos["expertos"]
    except (json.JSONDecodeError, KeyError):
        # Respaldo en caso de que ocurra algún error inesperado de formateo
        return ["Científico", "Filósofo", "Programador"]
    
async def consultar_experto(rol: str, mensaje_usuario: str) -> dict:
    """
    Llamada individual para un experto específico.
    """
    system_prompt = f"Responde a la siguiente consulta actuando estrictamente bajo el rol de un {rol} experto."
    
    response = await client.messages.create(
        model=MODELO_ECONOMICO,
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": mensaje_usuario}]
    )
    
    texto_respuesta = "".join([block.text for block in response.content if hasattr(block, 'text')])
    return {"rol": rol, "respuesta": texto_respuesta}

async def juez_final(mensaje_original: str, respuestas_expertos: list) -> str:
    """
    El modelo inteligente (Sonnet) evalúa las 3 respuestas generadas y elige la mejor.
    """
    bloque_respuestas = ""
    for exp in respuestas_expertos:
        bloque_respuestas += f"\n--- RESPUESTA DEL {exp['rol'].upper()} ---\n{exp['respuesta']}\n"

    system_prompt = (
        "Eres el Juez Final en un panel de expertos de IA. Tu trabajo es analizar la pregunta original "
        "del usuario y evaluar críticamente las respuestas proporcionadas por 3 expertos especializados.\n"
        "Debes elegir cuál de las respuestas es la mejor o crear una síntesis perfecta basada en los mejores puntos. "
        "Justifica brevemente tu decisión al inicio y entrega la respuesta final ganadora de manera limpia."
    )

    consulta_juez = (
        f"Pregunta original del usuario: '{mensaje_original}'\n\n"
        f"Aquí tienes las respuestas de los tres expertos:{bloque_respuestas}"
    )

    response = await client.messages.create(
        model=MODELO_INTELIGENTE, # Sonnet para máxima calidad analítica
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": consulta_juez}]
    )
    
    texto_final = "".join([block.text for block in response.content if hasattr(block, 'text')])
    return texto_final

@app.post("/ConsultarIA", summary="Consulta múltiples LLMs y evalúa con un Juez de IA")
async def evaluar_prompt(request: PromptRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="El prompt no puede estar vacío.")
        
    async with httpx.AsyncClient() as client:
        # Consultas concurrentes en paralelo

        # url_modelos = "https://openrouter.ai/api/v1/models"
    
        try:
            prompMejorado = await optimizar_prompt(request.prompt)
            print(f"Prompt mejorado: {prompMejorado}")  # Log del prompt mejorado

            expertos = await definir_roles(prompMejorado)
            print(f"✨ Expertos seleccionados: {expertos}\n")

            tareas = [consultar_experto(rol, prompMejorado) for rol in expertos]
            respuestas = await asyncio.gather(*tareas)

            veredicto_final = await juez_final(prompMejorado, respuestas)
    
            print("\n================ VEREDICTO FINAL DEL JUEZ ================")
            print(veredicto_final)
            print("==========================================================")

            return {
                "prompt": prompMejorado,
                "expertos": expertos,
                "evaluacion_juez": veredicto_final
            }
                        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al obtener modelos: {str(e)}")  

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)