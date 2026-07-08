import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
import config
import json
from anthropic import AsyncAnthropic

# Inicializamos el cliente de Anthropic con la clave de API desde el archivo de configuración
client = AsyncAnthropic()

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="AI Arena Router API",
    description="API para evaluar y comparar respuestas de múltiples LLMs usando un Juez de IA."
)

# Definimos los modelos de lenguaje que se utilizarán
MODELO_ECONOMICO = "claude-haiku-4-5-20251001"
MODELO_INTELIGENTE = "claude-sonnet-5"

class PromptRequest(BaseModel):
    prompt: str

async def optimizar_prompt(mensaje_usuario: str) -> str:
    """
    Convierte un mensaje de usuario en un prompt de ingeniería de prompts
    claro, estructurado y listo para enviarse a un LLM.

    La función delega la generación al cliente asíncrono `AsyncAnthropic`, pasando
    un `system_prompt` que instruye al modelo a actuar como un "Ingeniero de Prompts".
    Devuelve exclusivamente el texto del prompt mejorado tal como lo entrega el modelo.

    Parámetros
    ----------
    mensaje_usuario : str
        Texto original proporcionado por el usuario. Se espera una cadena no vacía;
        la validación de entrada debe realizarse por el llamador.

    Devuelve
    -------
    str
        Prompt mejorado generado por el LLM (sin metatexto ni explicaciones).

    Excepciones
    ----------
    Propaga excepciones relacionadas con la red o la API (p. ej. errores del cliente
    `AsyncAnthropic`). El llamador debe capturar y manejar `HTTPError`, timeouts u
    otras excepciones según corresponda.

    Consideraciones
    -------------
    - Esta función es asíncrona y debe invocarse con `await`.
    - El modelo y `max_tokens` están definidos por las constantes del módulo.
    - Para entradas sensibles aplique sanitización y políticas de privacidad antes de
      enviar el texto a servicios externos.
    - No realiza reintentos ni timeouts por sí misma; envolver en lógica de resiliencia
      cuando sea necesario.

    Ejemplo
    -------
    await optimizar_prompt("Explícame cómo funciona la retropropagación en redes neuronales")
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

async def trabajador_experto(cola_entrada: asyncio.Queue, cola_salida: asyncio.Queue, prompt_optimizado: str):
    """Consumidor Asíncrono (Worker): Escucha la cola de tareas, procesa el mensaje y envía el resultado a la cola de salida."""
    while not cola_entrada.empty():
        # Extraemos el mensaje (el rol del experto asignado) de la cola
        rol_experto = await cola_entrada.get()
        
        try:
            print(f"📡 [Cola] Mensaje recibido: Despertando al experto -> {rol_experto}")
            # Ejecutamos la consulta real al experto
            resultado = await consultar_experto(rol_experto, prompt_optimizado)
            # Colocamos el resultado procesado en la cola de salida para el Juez
            await cola_salida.put(resultado)
        finally:
            # Le avisamos a la cola que el mensaje actual ya fue procesado con éxito
            cola_entrada.task_done()

@app.post("/ConsultarIA", summary="Consulta múltiples LLMs y evalúa con un Juez de IA")
async def evaluar_prompt(request: PromptRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="El prompt no puede estar vacío.")
        
    async with httpx.AsyncClient() as client:
        
        try:
            prompMejorado = await optimizar_prompt(request.prompt)
            print(f"Prompt mejorado: {prompMejorado}")  # Log del prompt mejorado

            expertos = await definir_roles(prompMejorado)
            print(f"✨ Expertos seleccionados: {expertos}\n")


            # === ARQUITECTURA BASADA EN MENSAJES (PASO 3 DE TU CURSO) ===
            # Creamos las dos colas necesarias para desacoplar el sistema
            cola_tareas = asyncio.Queue()
            cola_resultados = asyncio.Queue()

            # Productor: Insertamos los roles elegidos como mensajes dentro de la cola de tareas
            for rol in expertos:
                await cola_tareas.put(rol)

            print(f"📥 [Cola] Se han encolado {cola_tareas.qsize()} mensajes de tareas para los expertos.")

            # Consumidores: Lanzamos trabajadores concurrentes para que escuchen y vacíen la cola de tareas
            print("👥 Paso 3: Trabajadores independientes procesando la cola de mensajes...")
            trabajadores = [
                asyncio.create_task(trabajador_experto(cola_tareas, cola_resultados, prompMejorado))
                for _ in range(len(expertos)) # Creamos un hilo de trabajo por cada experto elegido
            ]
            
            # Esperamos a que la cola de entrada se vacíe por completo
            await asyncio.gather(*trabajadores)

            # Recolectamos todas las respuestas que los trabajadores dejaron en la cola de resultados
            respuestas_consolidadas = []
            while not cola_resultados.empty():
                respuesta_mensaje = await cola_resultados.get()
                respuestas_consolidadas.append(respuesta_mensaje)
                cola_resultados.task_done()

            # tareas = [consultar_experto(rol, prompMejorado) for rol in expertos]
            # respuestas = await asyncio.gather(*tareas)

            # veredicto_final = await juez_final(prompMejorado, respuestas)
            veredicto_final = await juez_final(prompMejorado, respuestas_consolidadas)
    
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