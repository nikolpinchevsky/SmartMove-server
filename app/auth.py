from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
import os


# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash plain password before saving it in the database
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verify login password against hashed password from database
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT access token with user data and expiration time
def create_access_token(data: dict) -> str:

    secret_key = os.getenv("JWT_SECRET_KEY", "smartmove-secret-key")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt