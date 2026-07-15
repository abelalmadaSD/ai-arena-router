from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from src.security import crear_token_jwt
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Autenticación"])

class LoginRequest(BaseModel):
    """Modelo de solicitud para autenticación."""
    usuario: str
    contraseña: str

class TokenResponse(BaseModel):
    """Modelo de respuesta con token JWT."""
    access_token: str
    token_type: str

@router.post("/login", response_model=TokenResponse, summary="Obtener token JWT")
async def login(request: LoginRequest):
    """
    Endpoint de autenticación que genera un token JWT.
    
    Para propósitos de demostración/curso, valida credenciales simples.
    En producción, verificarías contra una base de datos de usuarios.
    
    Parámetros
    ----------
    request : LoginRequest
        Credenciales del usuario (usuario y contraseña).
    
    Retorna
    -------
    TokenResponse
        Token JWT válido por 24 horas.
    
    Levanta
    -------
    HTTPException
        Si las credenciales son inválidas (status 401).
    
    Ejemplo
    -------
    Solicitud:
    ```
    POST /auth/login
    {
        "usuario": "curso",
        "contraseña": "segura123"
    }
    ```
    
    Respuesta:
    ```
    {
        "access_token": "eyJhbGc...",
        "token_type": "bearer"
    }
    ```
    
    Luego usar el token:
    ```
    Authorization: Bearer <access_token>
    ```
    """
    # OWASP: Credenciales por defecto para curso
    USUARIO_CURSO = os.getenv("CURSO_USER", "curso")
    CONTRASEÑA_CURSO = os.getenv("CURSO_PASSWORD", "segura123")
    
    # Validar credenciales
    if request.usuario != USUARIO_CURSO or request.contraseña != CONTRASEÑA_CURSO:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generar token JWT
    payload = {
        "sub": request.usuario,
        "tipo": "acceso"
    }
    
    token_jwt = crear_token_jwt(payload)
    
    return {
        "access_token": token_jwt,
        "token_type": "bearer"  # nosec B105 - Tipo de token estándar OAuth 2.0, no una credencial
    }
