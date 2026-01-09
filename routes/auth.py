from fastapi import APIRouter, HTTPException, status
from database import supabase
from models import RegisterDetails, LoginDetails, LoginResponse
from passlib.context import CryptContext
from argon2 import PasswordHasher
import os
import jwt
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ph = PasswordHasher()
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"


# -- functions --
def encode_token(payload: dict, secret_key: str, algorithm: str = ALGORITHM) -> str:
    encoded_jwt = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded_jwt

def decode_token(token: str, secret_key: str, algorithms: str = ALGORITHM) -> dict:
    decoded_token = jwt.decode(token, secret_key, algorithms=algorithms)
    return decoded_token
    

# --- Routes ---
@router.post("/register")
def register(data: RegisterDetails):
    user_dict = data.model_dump()
    user_dict["password"] = ph.hash(user_dict["password"])
    response = supabase.table("users").insert(user_dict).execute()
    return {"message": "User registered successfully", "data": response.data}

@router.post("/login", response_model=LoginResponse)
def login(data: LoginDetails):
    # 1. Fetch only the necessary fields (username and hashed password)
    try:
        response = supabase.table("users") \
            .select("username, password") \
            .eq("username", data.username) \
            .single() \
            .execute()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )

    user = response.data
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid username or password"
        )

    if not ph.verify(user["password"], data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid username or password"
        )
    token = encode_token({"username": user["username"]}, SECRET_KEY)

    return {"message": "Login successful", "username": token}