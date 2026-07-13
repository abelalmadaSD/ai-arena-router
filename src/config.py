import os
from dotenv import load_dotenv

# Carga las variables desde el archivo .env local
load_dotenv()

# OWASP: Validación estricta en el arranque del sistema
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "CRÍTICO DE SEGURIDAD (OWASP): La variable de entorno 'ANTHROPIC_API_KEY' "
        "no está configurada. El sistema no iniciará para proteger la infraestructura."
    )

# Constantes globales de modelos
MODELO_ECONOMICO = "claude-haiku-4-5-20251001"
MODELO_INTELIGENTE = "claude-sonnet-5"

# Precios por cada 1,000,000 de tokens (Valores de referencia para Anthropic)
PRECIOS_MODELOS = {
    "claude-haiku-4-5-20251001": {
        "input": 0.25,   # USD por millón de tokens de entrada
        "output": 1.25   # USD por millón de tokens de salida
    },
    "claude-sonnet-5": {
        "input": 3.00,   # USD por millón de tokens de entrada
        "output": 15.00  # USD por millón de tokens de salida
    }
}