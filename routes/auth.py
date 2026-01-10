from fastapi import APIRouter, HTTPException, status, Depends
from database import supabase # Assuming this is your supabase client
from models import RegisterDetails, LoginDetails, LoginResponse
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import os
import jwt
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
ph = PasswordHasher()

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

# --- Utilities ---

def encode_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Query Supabase for the user record
        response = supabase.table("users").select("*").eq("username", username).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        return response.data
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# --- Routes ---

@router.post("/register")
def register(data: RegisterDetails):
    hashed_password = ph.hash(data.password)
    user_data = {
        "username": data.username,
        "email": data.email,
        "password": hashed_password
    }
    
    response = supabase.table("users").insert(user_data).execute()
    return {"message": "User registered successfully"}

@router.post("/token")
def login(data: LoginDetails):
    # Fetch user from Supabase
    response = supabase.table("users").select("*").eq("username", data.username).execute()
    
    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user = response.data[0]

    # Verify Argon2 Hash
    try:
        ph.verify(user["password"], data.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = encode_token({"username": user["username"]})
    return {"access_token": token, "token_type": "bearer"}