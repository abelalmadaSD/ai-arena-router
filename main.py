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

async def consultar_modelo(client: httpx.AsyncClient, modelo: str, prompt: str, system_prompt: str = None) -> str:
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": modelo,
        "messages": messages
    }

    print(f"Consultando modelo {modelo}")  # Log del prompt truncado
    
    for intento in range(3):
        try:
            response = await client.post(config.OPENROUTER_URL, headers=headers, json=payload, timeout=30.0)
            
            # Si nos da 429 (Rate Limit), esperamos un momento y reintentamos
            if response.status_code == 429:
                print(f"⚠️ Rate limit detectado para {modelo}. Reintentando en 5 segundos... (Intento {intento + 1}/3)")
                await asyncio.sleep(5)
                continue
                
            if response.status_code != 200:
                return f"Error ({response.status_code}): {response.text}"
                
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            if intento == 2: # Si es el último intento y falla, arroja el error
                return f"Error excepcional en {modelo}: {str(e)}"
            await asyncio.sleep(2)

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
            
            response = await client.get(url_modelos, timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="No se pudo conectar con la lista de OpenRouter.")
            
            todos_los_modelos = response.json().get("data", [])
            
            # Filtramos en base al precio por token (donde entrada y salida sean 0)
            gratis = [m.get("id") for m in todos_los_modelos if m.get("pricing", {}).get("prompt") == "0"]

            prompt = (
                f"### PROMPT ORIGINAL DEL USUARIO:\n"
                f"'{request.prompt}'\n\n"
                f"### LISTA DE MODELOS DISPONIBLES (SELECCIONA SOLO DE AQUÍ):\n"
                f"{gratis}\n"
            )

            system = (
                "Eres un Agente Enrutador de Arquitectura de IA experto.\n\n"
                "TU TAREA:\n"
                "1. Analiza el 'PROMPT ORIGINAL DEL USUARIO'.\n"
                "2. De la lista proporcionada, selecciona los 3 modelos más capaces y adecuados para resolver esa tarea específica (asígnalos a 'modelo_a' y 'modelo_b').\n"
                "3. Selecciona un cuarto modelo de la lista que sea rápido y preciso para actuar como evaluador/juez (asígnalo a 'modelo_juez').\n"
                "4. Reescribe el prompt del usuario aplicando ingeniería de prompts (claridad, contexto, restricciones si aplica) para obtener el mejor resultado posible de los LLMs. Asígnalo a 'prompt_mejorado'.\n\n"
                "RESTRICCIONES ESTRICTAS:\n"
                "- Devuelve ÚNICAMENTE un objeto JSON válido.\n"
                "- NO incluyas introducciones, explicaciones, ni bloques de código de Markdown (no uses ```json).\n"
                "- Usa comillas dobles para las llaves y valores del JSON.\n"
                "- Los IDs de los modelos deben ser exactamente iguales a los de la lista provista.\n\n"
                "ESTRUCTURA DE SALIDA REQUERIDA:\n"
                "{\n"
                '  "modelo_a": "id_exacto_modelo_a",\n'
                '  "modelo_b": "id_exacto_modelo_b",\n'
                '  "modelo_c": "id_exacto_modelo_c",\n'
                '  "modelo_juez": "id_exacto_modelo_juez",\n'
                '  "prompt_mejorado": "Texto del prompt optimizado aquí"\n'
                "}"
            )

            resultado = await consultar_modelo(client, config.MODELO, prompt, system_prompt=system)
            resultado = json.loads(resultado)  # Convertimos el JSON a un diccionario de Python            

            tareas = [
                consultar_modelo(client, resultado['modelo_a'], resultado['prompt_mejorado']),
                consultar_modelo(client, resultado['modelo_b'], resultado['prompt_mejorado']),
                consultar_modelo(client, resultado['modelo_c'], resultado['prompt_mejorado']),
            ]

            respuesta_a, respuesta_b, respuesta_c = await asyncio.gather(*tareas)
        
            # Inyección al Juez
            prompt_juez = (
                f"Prompt Mejorado: '{resultado['prompt_mejorado']}'\n\n"
                f"--- RESPUESTA A ---\n{respuesta_a}\n\n"
                f"--- RESPUESTA B ---\n{respuesta_b}\n\n"
                f"--- RESPUESTA C ---\n{respuesta_c}\n\n"
                f"Evalúa estas respuestas. Califica del 1 al 10 y dictamina la ganadora."
            )
            system_juez = "Eres un juez neutral de IA. Evalúa con base en precisión y claridad. Devuelve formato Markdown."
            
            evaluacion = await consultar_modelo(client, resultado['modelo_juez'], prompt_juez, system_prompt=system_juez)

            return {
                "prompt": resultado['prompt_mejorado'],
                "resultados": [
                    {"modelo": resultado['modelo_a'], "respuesta": respuesta_a},
                    {"modelo": resultado['modelo_b'], "respuesta": respuesta_b},
                    {"modelo": resultado['modelo_c'], "respuesta": respuesta_c}
                ],
                "evaluacion_juez": evaluacion
            }

            # return {
            #     "total_gratuitos": len(gratis),
            #     "modelos": gratis
            # }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al obtener modelos: {str(e)}")


        tareas = [
            consultar_modelo(client, config.MODELO_A, request.prompt),
            consultar_modelo(client, config.MODELO_B, request.prompt)
        ]
        respuesta_a, respuesta_b = await asyncio.gather(*tareas)
        
        # Inyección al Juez
        prompt_juez = (
            f"Prompt original: '{request.prompt}'\n\n"
            f"--- RESPUESTA A ---\n{respuesta_a}\n\n"
            f"--- RESPUESTA B ---\n{respuesta_b}\n\n"
            f"Evalúa ambas respuestas. Califica del 1 al 10 y dictamina la ganadora."
        )
        system_juez = "Eres un juez neutral de IA. Evalúa con base en precisión y claridad. Devuelve formato Markdown."
        
        evaluacion = await consultar_modelo(client, config.MODELO_JUEZ, prompt_juez, system_prompt=system_juez)
        
    return {
        "prompt": request.prompt,
        "resultados": [
            {"modelo": config.MODELO_A, "respuesta": respuesta_a},
            {"modelo": config.MODELO_B, "respuesta": respuesta_b}
        ],
        "evaluacion_juez": evaluacion
    }

        

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)