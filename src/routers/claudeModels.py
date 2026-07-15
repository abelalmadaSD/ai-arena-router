import asyncio
import time
from fastapi import APIRouter, HTTPException, status, Depends
from src.models.claudeModels import PromptRequest
from src.servicios import claudeModels
from src.security import verificar_token_jwt

router = APIRouter(prefix="/v1", tags=["Enrutamiento IA"])

@router.post("/ConsultarIA", summary="Consulta múltiples LLMs concurrentemente y evalúa con un Juez")
async def evaluar_prompt(request: PromptRequest, token_payload: dict = Depends(verificar_token_jwt)):
    # OWASP: Autenticación verificada con JWT
    usuario = token_payload.get("sub", "desconocido")
    
    # OWASP: Sanitización manual de espacios en blanco redundantes
    prompt_usuario = request.prompt.strip()
    tiempo_inicio_global = time.perf_counter()

    try:
        # 1. Optimizar prompt y definir expertos
        optimizar_prompt = await claudeModels.optimizar_prompt(prompt_usuario)
        promp_mejorado = optimizar_prompt['texto']
        
        roles = await claudeModels.definir_roles(promp_mejorado)
        expertos = roles["datos"]  # Extraemos la lista de expertos del diccionario devuelto

        # 2. Arquitectura de mensajería asíncrona por colas
        cola_tareas = asyncio.Queue()
        cola_resultados = asyncio.Queue()

        for rol in expertos:
            await cola_tareas.put(rol)

        # 3. Lanzamiento de trabajadores concurrentes
        trabajadores = [
            asyncio.create_task(claudeModels.trabajador_experto(cola_tareas, cola_resultados, promp_mejorado))
            for _ in range(len(expertos))
        ]

        await asyncio.gather(*trabajadores)

        # 4. Consolidación de resultados
        respuestas_consolidadas = []
        while not cola_resultados.empty():
            msg = await cola_resultados.get()
            respuestas_consolidadas.append(msg)
            cola_resultados.task_done()

        # 5. Juicio analítico final
        juez = await claudeModels.juez_final(promp_mejorado, respuestas_consolidadas)

        veredicto = juez["texto_final"]

        # =====================================================================
        # 📈 CONSOLIDACIÓN DE MÉTRICAS Y CRÉDITOS (AUDITORÍA OWASP/COSTOS)
        # =====================================================================
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

        # return {
        #     "prompt": promp_mejorado,
        #     "expertos": expertos,
        #     "evaluacion_juez": veredicto
        # }
        
    except Exception as e:
        # OWASP: Guardar trazas reales de error internamente (Logs corporativos)
        print(f"[ERROR INTERNO SISTEMA]: {str(e)}")
        # Ofrecer respuesta genérica y opaca al exterior para evitar ingeniería inversa
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del sistema de inteligencia artificial al procesar los agentes."
        )