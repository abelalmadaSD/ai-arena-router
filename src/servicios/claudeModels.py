import asyncio
import json
from anthropic import AsyncAnthropic
from src.config import ANTHROPIC_API_KEY, MODELO_ECONOMICO, MODELO_INTELIGENTE, PRECIOS_MODELOS
# Inicialización segura
client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

def calcular_costo(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calcula el costo estimado en USD para una llamada al modelo basada en tokens consumidos.

    Parámetros
    ----------
    model : str
        Clave del modelo utilizada para buscar precios en PRECIOS_MODELOS.
    input_tokens : int
        Número de tokens de entrada (prompt).
    output_tokens : int
        Número de tokens de salida (respuesta del modelo).

    Devuelve
    -------
    float
        Costo estimado en dólares americanos (USD), redondeado a 6 decimales.

    Notas
    -----
    - Los precios en PRECIOS_MODELOS se esperan en USD por 1,000,000 tokens.
    - La función maneja valores negativos de tokens convirtiéndolos a cero.
    """
    # Validación básica y normalización
    if input_tokens is None:
        input_tokens = 0
    if output_tokens is None:
        output_tokens = 0

    input_tokens = max(0, int(input_tokens))
    output_tokens = max(0, int(output_tokens))

    precios = PRECIOS_MODELOS.get(model, {"input": 0.0, "output": 0.0})
    costo_in = (input_tokens / 1_000_000) * precios.get("input", 0.0)
    costo_out = (output_tokens / 1_000_000) * precios.get("output", 0.0)
    return round(costo_in + costo_out, 6)

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

    # Extraemos el uso real de tokens reportado por Anthropic
    in_tokens = response.usage.input_tokens
    out_tokens = response.usage.output_tokens

    return {
        "texto": texto_respuesta,
        "metricas": {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "costo_usd": calcular_costo(MODELO_ECONOMICO, in_tokens, out_tokens)
        }
    }

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
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": mensaje_usuario}]
    )
    
    texto_respuesta = "".join([block.text for block in response.content if hasattr(block, 'text')])

    # Extraemos el uso real de tokens reportado por Anthropic
    in_tokens = response.usage.input_tokens
    out_tokens = response.usage.output_tokens

    # LIMPIEZA DE SEGURIDAD CONTRA BLOQUES MARKDOWN
    if texto_respuesta.startswith("```"):
        # Removemos la línea inicial de apertura (```json o ```)
        lineas = texto_respuesta.splitlines()
        if len(lineas) >= 2:
            lineas_limpias = [l for l in lineas if not l.strip().startswith("```")]
            texto_respuesta = "".join(lineas_limpias).strip()

    try:
        # Parseamos el JSON devuelto por Claude
        datos = json.loads(texto_respuesta)
        expertos = datos["expertos"]
        # return datos["expertos"]
    except (json.JSONDecodeError, KeyError):
        # Respaldo en caso de que ocurra algún error inesperado de formateo
        expertos = ["Científico", "Filósofo", "Matemático"]
    
    return {
        "datos": expertos,
        "metricas": {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "costo_usd": calcular_costo(MODELO_ECONOMICO, in_tokens, out_tokens)
        }
    }
    
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
    
    in_tokens = response.usage.input_tokens
    out_tokens = response.usage.output_tokens

    # return {"rol": rol, "respuesta": texto_respuesta}
    
    return {
        "rol": rol,
        "respuesta": texto_respuesta,
        "metricas": {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "costo_usd": calcular_costo(MODELO_ECONOMICO, in_tokens, out_tokens)
        }
    }

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
    
    in_tokens = response.usage.input_tokens
    out_tokens = response.usage.output_tokens

    # return texto_final

    return {
        "texto_final": texto_final,
        "metricas": {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "costo_usd": calcular_costo(MODELO_INTELIGENTE, in_tokens, out_tokens)
        }
    }

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
