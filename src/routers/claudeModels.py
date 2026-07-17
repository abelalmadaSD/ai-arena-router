import asyncio
import time
import re
from fastapi import APIRouter, HTTPException, status, Depends
from src.models.claudeModels import PromptRequest
from src.servicios import claudeModels
from src.security import verificar_token_jwt

router = APIRouter(prefix="/v1", tags=["Enrutamiento IA"])

@router.post("/ConsultarIA", summary="Consulta múltiples LLMs concurrentemente y evalúa con un Juez")
async def evaluar_prompt(request: PromptRequest, token_payload: dict = Depends(verificar_token_jwt)):
    # Autenticación verificada con JWT
    usuario = token_payload.get("sub", "desconocido")
    
    # Sanitización manual de espacios en blanco redundantes
    prompt_usuario = request.prompt.strip()

    # rechazar URLs (evita que se intente inyectar URIs hacia servicios externos)
    if re.search(r"https?://", prompt_usuario, re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompts que contienen URLs no están permitidos por razones de seguridad."
        )

    # rechazar etiquetas <script> y HTML/JS obvio
    if re.search(r"<script\b", prompt_usuario, re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompts que contienen HTML/JS no están permitidos."
        )

    # Limitar número de líneas para evitar prompts con bloques enormes
    if prompt_usuario.count("\n") > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompts demasiado largos (demasiadas líneas)."
        )

    # Evitar exceso de bloques de código (```), heurística simple
    if prompt_usuario.count("```") > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompts con múltiples bloques de código no están permitidos."
        )
    tiempo_inicio_global = time.perf_counter()

    try:
        # Optimizar prompt y definir expertos
        optimizar_prompt = await claudeModels.optimizar_prompt(prompt_usuario)
        promp_mejorado = optimizar_prompt['texto']
        
        roles = await claudeModels.definir_roles(promp_mejorado)
        expertos = roles["datos"]  # Extraemos la lista de expertos del diccionario devuelto

        # Arquitectura de mensajería asíncrona por colas
        cola_tareas = asyncio.Queue()
        cola_resultados = asyncio.Queue()

        for rol in expertos:
            await cola_tareas.put(rol)

        # Lanzamiento de trabajadores concurrentes
        trabajadores = [
            asyncio.create_task(claudeModels.trabajador_experto(cola_tareas, cola_resultados, promp_mejorado))
            for _ in range(len(expertos))
        ]

        await asyncio.gather(*trabajadores)

        # Consolidación de resultados
        respuestas_consolidadas = []
        while not cola_resultados.empty():
            msg = await cola_resultados.get()
            respuestas_consolidadas.append(msg)
            cola_resultados.task_done()

        # Juicio analítico final
        juez = await claudeModels.juez_final(promp_mejorado, respuestas_consolidadas)

        veredicto = juez["texto_final"]

        # Consolidación de métricas y costos de tokens
        tiempo_total_global = round(time.perf_counter() - tiempo_inicio_global, 2)

        metricas_expertos = {}
        tokens_entrada_total = optimizar_prompt["metricas"]["input_tokens"] + roles["metricas"]["input_tokens"] + juez["metricas"]["input_tokens"]
        tokens_salida_total = optimizar_prompt["metricas"]["output_tokens"] + roles["metricas"]["output_tokens"] + juez["metricas"]["output_tokens"]
        costo_total_usd = optimizar_prompt["metricas"]["costo_usd"] + roles["metricas"]["costo_usd"] + juez["metricas"]["costo_usd"]

        for exp in respuestas_consolidadas:
            rol = exp["rol"]
            m = exp["metricas"]
            metricas_expertos[rol] = {
                "tokens_entrada": m["input_tokens"],
                "tokens_salida": m["output_tokens"],
                "costo_estimado_usd": m["costo_usd"]
            }
            tokens_entrada_total += m["input_tokens"]
            tokens_salida_total += m["output_tokens"]
            costo_total_usd += m["costo_usd"]

        return {
            "resultado": {
                "prompt_original": prompt_usuario,
                "prompt_optimizado": promp_mejorado,
                "expertos_seleccionados": expertos,
                "evaluacion_juez": veredicto
            },
            "auditoria_consumo": {
                "tiempo_total_ejecucion_segundos": tiempo_total_global,
                "total_tokens_consumidos": tokens_entrada_total + tokens_salida_total,
                "total_tokens_entrada": tokens_entrada_total,
                "total_tokens_salida": tokens_salida_total,
                "costo_total_creditos_usd": round(costo_total_usd, 5),
                "desglose_por_paso": {
                    "1_optimizacion_prompt": optimizar_prompt["metricas"],
                    "2_seleccion_expertos": roles["metricas"],
                    "3_panel_expertos_concurrentes": metricas_expertos,
                    "4_evaluacion_juez": juez["metricas"]
                }
            }
        }

    except Exception as e:
        print(f"[ERROR INTERNO SISTEMA]: {str(e)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del sistema de inteligencia artificial al procesar los agentes."
        )