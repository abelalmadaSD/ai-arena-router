from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from src.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

security = HTTPBearer()

def crear_token_jwt(datos: dict, expiracion: Optional[timedelta] = None) -> str:
    """
    Genera un token JWT firmado con la clave secreta.
    
    """
    a_codificar = datos.copy()
    
    if expiracion:
        tiempo_expiracion = datetime.utcnow() + expiracion
    else:
        tiempo_expiracion = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    a_codificar.update({"exp": tiempo_expiracion})
    
    token_codificado = jwt.encode(a_codificar, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token_codificado

async def verificar_token_jwt(credenciales = Depends(security)) -> dict:
    """
    Verifica la validez del token JWT proporcionado en el header Authorization.
    
   
    """
    token = credenciales.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
