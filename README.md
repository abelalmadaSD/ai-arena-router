# AI Arena Router API

## Descripción general

AI Arena Router es una API REST construida con FastAPI para recibir consultas de usuario, autenticarlas con JWT, optimizar el prompt, enrutarlo a expertos especializados y devolver una respuesta final evaluada por un juez analítico.

El flujo del servicio incluye:
- recibir un `prompt` del usuario;
- autenticar la llamada mediante un token JWT;
- optimizar el prompt con un modelo económico;
- seleccionar roles expertos especializados;
- ejecutar consultas concurrentes por cada experto;
- evaluar y sintetizar las respuestas con un juez final;
- devolver la respuesta final junto con métricas de consumo y costo estimado.

## Requisitos previos

- Python 3.11 o superior.
- `pip` instalado.
- Entorno virtual recomendado.
- Acceso a Anthropic para el modelo utilizado por el servicio.
- Variables de entorno necesarias para la autenticación y la configuración del proyecto.

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

4. Configura las variables de entorno requeridas por la aplicación.

5. Inicia la API localmente:

   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. Abre la documentación interactiva:

   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

## Autenticación

El proyecto expone un endpoint de autenticación para obtener un token JWT.

### Endpoint: `POST /auth/login`

Este endpoint valida las credenciales del usuario y devuelve un token bearer que debe enviarse en el encabezado `Authorization` para consumir el endpoint principal.

#### Ejemplo de solicitud

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"usuario": "curso", "contraseña": "segura123"}'
```

#### Ejemplo de respuesta

```json
{
  "access_token": "<token_jwt>",
  "token_type": "bearer"
}
```

## Uso de la API

### Endpoint principal

`POST /v1/ConsultarIA`

#### Descripción

Este endpoint requiere autenticación JWT y desencadena el flujo completo de optimización, enrutamiento y evaluación.

#### Request

- Ruta: `/v1/ConsultarIA`
- Método: `POST`
- Encabezado: `Authorization: Bearer <token>`
- Encabezado: `Content-Type: application/json`
- Cuerpo:
  - `prompt` (string): texto de la consulta del usuario.

Ejemplo con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/v1/ConsultarIA" \
  -H "Authorization: Bearer <token_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explícame cómo funciona el algoritmo de gradiente descendente."}'
```

Ejemplo en Python:

```python
import requests

url = "http://127.0.0.1:8000/v1/ConsultarIA"
payload = {"prompt": "Explícame cómo funciona el algoritmo de gradiente descendente."}
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <token_jwt>"
}

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
          "input_tokens": 80,
          "output_tokens": 150,
          "costo_estimado_usd": 0.00028
        },
        "Programador": {
          "input_tokens": 75,
          "output_tokens": 140,
          "costo_estimado_usd": 0.00026
        },
        "Científico": {
          "input_tokens": 70,
          "output_tokens": 145,
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

## Estructura del proyecto

- `main.py`: arranca la aplicación FastAPI y registra los routers de autenticación y de IA.
- `src/routers/auth.py`: expone el endpoint `/auth/login` y genera el token JWT.
- `src/routers/claudeModels.py`: define el endpoint `/v1/ConsultarIA` y orquesta el flujo de consulta.
- `src/models/claudeModels.py`: define el esquema Pydantic `PromptRequest`.
- `src/servicios/claudeModels.py`: implementa la optimización de prompt, la selección de roles, las consultas a expertos y la evaluación del juez.
- `src/security.py`: maneja la creación y verificación de tokens JWT.
- `src/config.py`: carga variables de entorno y define modelos, precios y configuraciones del sistema.
- `tests/test_main.py`: pruebas básicas del flujo de optimización y selección de roles.
- `Dockerfile` y `k8s/`: recursos para ejecutar el servicio en contenedores y Kubernetes.

## Despliegue con Docker y Kubernetes

### Docker

```bash
docker build -t ai-arena-router .
docker run -p 8000:8000 ai-arena-router
```

### Kubernetes

El repositorio incluye un ejemplo de deployment y service en `k8s/` para exponer la API detrás de un balanceador de carga.

## Pruebas

Ejecuta las pruebas desde el entorno virtual del proyecto para asegurar que las dependencias estén disponibles:

```powershell
.\venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

## Notas adicionales

- El endpoint principal devuelve un JSON con `resultado` y `auditoria_consumo`.
- Si cambias modelos o precios, revisa `src/config.py`.
- Para un entorno de producción, utiliza un servidor ASGI adecuado y evita `--reload`.

