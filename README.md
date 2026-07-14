# AI Arena Router API

## Descripción general

AI Arena Router es una API REST construida con FastAPI para enrutar una sola consulta de usuario a múltiples modelos de lenguaje y evaluar sus respuestas mediante un juez final. La aplicación optimiza el prompt, selecciona expertos especializados de forma dinámica, ejecuta consultas concurrentes y devuelve una respuesta consolidada junto con métricas de consumo y estimaciones de costo.

El objetivo principal es permitir comparativas de LLMs y generar una evaluación de alta calidad basada en varias respuestas especializadas.

## Requisitos previos

Antes de ejecutar la API, debes contar con:

- Python 3.11 o superior.
- Un entorno virtual de Python (recomendado).
- Una clave de API válida de Anthropic.
- `pip` instalado y actualizado.

## Instalación y ejecución en local

1. Clona o descarga el repositorio:

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

5. Inicia la API localmente:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. Abre la documentación interactiva:

   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

## Uso de la API

### Endpoint principal

`POST /v1/ConsultarIA`

Descripción: envía un prompt de usuario, genera un prompt optimizado, consulta múltiples expertos y devuelve una evaluación final junto con métricas de consumo.

#### Request

- Ruta: `/v1/ConsultarIA`
- Método: `POST`
- `Content-Type`: `application/json`
- Body:
  - `prompt` (string): Consulta del usuario.

Ejemplo con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/v1/ConsultarIA" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explícame cómo se calcula el gradiente descendente en redes neuronales."}'
```

Ejemplo en Python:

```python
import requests

url = "http://127.0.0.1:8000/v1/ConsultarIA"
payload = {
    "prompt": "Explícame cómo se calcula el gradiente descendente en redes neuronales."
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

#### Ejemplo de response exitoso

```json
{
  "resultado": {
    "prompt_original": "Explícame cómo se calcula el gradiente descendente en redes neuronales.",
    "prompt_optimizado": "Explica de forma clara y técnica cómo funciona el algoritmo de gradiente descendente en redes neuronales, incluyendo fórmulas, pasos y consideraciones prácticas.",
    "expertos_seleccionados": [
      "Matemático",
      "Programador",
      "Científico"
    ],
    "evaluacion_juez": "El mejor enfoque combina la explicación matemática del matemático con la implementación práctica del programador. \n...respuesta final sintetizada y justificada..."
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

> Nota: los valores de `tokens` y `costo_total_creditos_usd` en el ejemplo son estimaciones de demostración y pueden variar según la respuesta real del modelo.

## Notas adicionales

- Esta API usa FastAPI y genera documentación automática en `/docs` y `/redoc`.
- No compartas tu clave `ANTHROPIC_API_KEY` en repositorios públicos.
- Si deseas modificar los modelos o las tarifas de tokens, revisa `src/config.py`.
- Para uso en producción, despliega con un servidor ASGI adecuado y deshabilita `--reload`.

