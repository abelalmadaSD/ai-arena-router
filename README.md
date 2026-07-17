# AI Arena Router API

## Descripción general

AI Arena Router es una API REST construida con FastAPI para enrutar consultas de usuario hacia múltiples agentes de lenguaje y generar una evaluación final mediante un juez analítico.

La aplicación realiza los siguientes pasos:
- Recibe un `prompt` de usuario.
- Optimiza el prompt usando un modelo económico.
- Selecciona dinámicamente roles expertos especializados.
- Ejecuta consultas concurrentes por cada experto.
- Evalúa y sintetiza todas las respuestas con un juez final.
- Devuelve la respuesta final junto con métricas de consumo de tokens y estimaciones de costo.

## Requisitos previos

- Python 3.11 o superior.
- `pip` instalado.
- Entorno virtual recomendado.
- Clave de API de Anthropic.

## Instalación y ejecución en local

1. Clona el repositorio:

   ```bash
   git clone https://github.com/<tu-usuario>/ai-arena-router.git
   cd ai-arena-router
   ```

2. Crea y activa un entorno virtual:

   Windows PowerShell:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   Windows CMD:
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```

   macOS / Linux:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crea un archivo `.env` en la raíz del proyecto con la clave de Anthropic:

   ```env
   ANTHROPIC_API_KEY=tu_clave_de_anthropic
   ```

   Opcionalmente, si tu proyecto usa OpenAI en alguna extensión futura:

   ```env
   OPENAI_API_KEY=tu_clave_de_openai
   ```

5. Inicia la API localmente:

   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. Abre la documentación interactiva:

   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

## Uso de la API

### Endpoint disponible

`POST /v1/ConsultarIA`

#### Descripción

Consulta un único endpoint que desencadena el flujo completo de optimización, enrutamiento y evaluación.

#### Request

- Ruta: `/v1/ConsultarIA`
- Método: `POST`
- Encabezado: `Content-Type: application/json`
- Cuerpo:
  - `prompt` (string): texto de la consulta del usuario.

Ejemplo con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/v1/ConsultarIA" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explícame cómo funciona el algoritmo de gradiente descendente."}'
```

Ejemplo en Python:

```python
import requests

url = "http://127.0.0.1:8000/v1/ConsultarIA"
payload = {"prompt": "Explícame cómo funciona el algoritmo de gradiente descendente."}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

#### Ejemplo de response

```json
{
  "resultado": {
    "prompt_original": "Explícame cómo funciona el algoritmo de gradiente descendente.",
    "prompt_optimizado": "Explica de modo claro y técnico el algoritmo de gradiente descendente, sus fórmulas, pasos clave y recomendaciones para su aplicación en redes neuronales.",
    "expertos_seleccionados": [
      "Matemático",
      "Programador",
      "Científico"
    ],
    "evaluacion_juez": "...respuesta final sintetizada y justificada..."
  },
  "auditoria_consumo": {
    "tiempo_total_ejecucion_segundos": 3.42,
    "total_tokens_consumidos": 1245,
    "total_tokens_entrada": 420,
    "total_tokens_salida": 825,
    "costo_total_creditos_usd": 0.02435,
    "desglose_por_paso": {
      "1_optimizacion_prompt": {
        "input_tokens": 55,
        "output_tokens": 120,
        "costo_usd": 0.000095
      },
      "2_seleccion_expertos": {
        "input_tokens": 45,
        "output_tokens": 70,
        "costo_usd": 0.00009
      },
      "3_panel_expertos_concurrentes": {
        "Matemático": {
          "tokens_entrada": 80,
          "tokens_salida": 150,
          "costo_estimado_usd": 0.00028
        },
        "Programador": {
          "tokens_entrada": 75,
          "tokens_salida": 140,
          "costo_estimado_usd": 0.00026
        },
        "Científico": {
          "tokens_entrada": 70,
          "tokens_salida": 145,
          "costo_estimado_usd": 0.00025
        }
      },
      "4_evaluacion_juez": {
        "input_tokens": 95,
        "output_tokens": 220,
        "costo_usd": 0.00078
      }
    }
  }
}
```

> Nota: los valores del ejemplo son ilustrativos. Los totales reales dependen de la respuesta de los modelos y de la configuración de tokens.

## Detalles del proyecto

- `main.py`: arranca la aplicación FastAPI y registra el router de IA.
- `src/routers/claudeModels.py`: define el endpoint `/v1/ConsultarIA` y orquesta el flujo de consulta.
- `src/models/claudeModels.py`: define el esquema Pydantic `PromptRequest`.
- `src/servicios/claudeModels.py`: implementa la lógica de optimización de prompt, selección de roles, consultas a expertos y evaluación del juez.
- `src/config.py`: carga variables de entorno y define modelos y precios de tokens.

## Notas adicionales

- La aplicación exige `ANTHROPIC_API_KEY` en `.env` para arrancar.
- El endpoint único devuelve JSON con `resultado` y `auditoria_consumo`.
- Si cambias modelos o precios, actualiza `src/config.py`.
- Para un entorno de producción, utiliza un servidor ASGI adecuado y no utilices `--reload`.

## Automatización: workflow para leer Issues

Se ha añadido un workflow de GitHub Actions en `.github/workflows/read-issues.yml` que ejecuta `agent_issues.py` en los siguientes casos:

- Cuando se abre, edita o reabre un `issue` en el repositorio.
- Ejecuta también de forma programada (cron diaria) para revisar issues abiertos.

El workflow instala dependencias y ejecuta el script con la variable de entorno `GITHUB_TOKEN` disponible automáticamente desde `secrets.GITHUB_TOKEN`.

