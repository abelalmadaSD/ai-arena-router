import asyncio
import os
from github import Github
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "abelalmadaSD/AI-ARENA-ROUTER"

# 1. HERRAMIENTA LOCA: El agente lee tu propio código de la API para analizarlo
@function_tool
def leer_codigo_api_local() -> str:
    """Lee el archivo principal de la API local para su análisis."""
    ruta = "main.py" # Cambia esto por la ruta de tu archivo de rutas/endpoints si es otra
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    return "# Código base de la API no encontrado."

@function_tool
def obtener_ultimo_issue_github() -> str:
    """Se conecta al repositorio de GitHub y extrae el issue abierto más reciente."""
    if not GITHUB_TOKEN:
        return "ERROR: No se encontró el GITHUB_TOKEN en las variables de entorno."
    
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Obtener los issues abiertos, ordenados por fecha de creación
        issues = repo.get_issues(state='open', sort='created', direction='desc')
        
        if issues.totalCount == 0:
            return "No hay issues abiertos en el repositorio en este momento."
            
        ultimo_issue = issues[0]
        
        # Formatear la información para que la entienda el LLM
        datos_issue = (
            f"ID del Issue: #{ultimo_issue.number}\n"
            f"Título: {ultimo_issue.title}\n"
            f"Descripción: {ultimo_issue.body}\n"
        )
        return datos_issue
        
    except Exception as e:
        return f"ERROR al conectar con la API de GitHub: {str(e)}"


# 2. CONFIGURACIÓN DEL AGENTE
agente_validador = Agent(
    name="Agente Lector de Issues",
    instructions="""
    Eres un ingeniero de software asistido por IA. Tu flujo de trabajo estricto es:
    1. Utilizar la herramienta para obtener el último issue de GitHub.
    2. Utilizar la herramienta para leer el código de la API local y entender el contexto.
    3. Analizar el problema reportado en el issue.
    
    Tu respuesta debe estructurarse en español con el siguiente formato Markdown:
    ### 1. Análisis del Fallo
    (Explica brevemente por qué ocurre el problema basándote en el código actual).
    
    ### 2. Propuesta de Código
    (Proporciona el bloque de código corregido).
    
    ### 3. Prueba Unitaria
    (Proporciona una prueba unitaria usando `unittest` o `pytest` para validar la corrección).
    """,
    tools=[obtener_ultimo_issue_github, leer_codigo_api_local]
)

async def main():
    print("-> Iniciando el agente de desarrollo...")
    
    # El prompt ahora le ordena explícitamente usar la herramienta de conexión
    prompt = "Por favor, revisa el último issue reportado en nuestro repositorio de GitHub, analiza cómo afecta a nuestro código actual y genera una propuesta de solución completa."
    
    print("-> El agente está consultando GitHub y analizando el código local...")
    result = await Runner.run(agente_validador, prompt)
    
    # Guardar el resultado
    archivo_salida = "propuesta_agente.md"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(result.final_output)
        
    print(f"-> ¡Análisis completado! La propuesta se ha guardado en '{archivo_salida}'.")

if __name__ == "__main__":
    asyncio.run(main())