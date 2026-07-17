import os
from dotenv import load_dotenv
from datetime import timedelta

# Carga las variables desde el archivo .env local
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Validación estricta en el arranque del sistema
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY no configurada")

if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "CRÍTICO DE SEGURIDAD (OWASP): La variable de entorno 'ANTHROPIC_API_KEY' "
        "no está configurada. El sistema no iniciará para proteger la infraestructura."
    )

# Constantes globales de modelos
MODELO_ECONOMICO = "claude-haiku-4-5-20251001"
MODELO_INTELIGENTE = "claude-sonnet-5"

# Precios por cada 1,000,000 de tokens
PRECIOS_MODELOS = {
    "claude-haiku-4-5-20251001": {
        "input": 0.25,
        "output": 1.25
    },
    "claude-sonnet-5": {
        "input": 3.00,
        "output": 15.00 
    }
}