from pydantic import BaseModel, Field

class PromptRequest(BaseModel):
    # OWASP: Escudo de validación contra inyecciones masivas y ataques DoS de tamaño
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Consulta del usuario sanitizada y acotada por seguridad corporativa."
    )