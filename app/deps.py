from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os


# Expect Authorization: Bearer <token>
security = HTTPBearer()

# Read JWT token from Authorization header, validate it, and return current user payload
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):

    token = credentials.credentials

    secret_key = os.getenv("JWT_SECRET_KEY", "smartmove-secret-key")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])

        user_id = payload.get("user_id")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid authentication token")

        return {
            "user_id": user_id,
            "email": email
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")