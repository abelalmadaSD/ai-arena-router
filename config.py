import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Modelos gratuitos líderes en 2026 para la comparativa
MODELO = "cohere/north-mini-code:free"