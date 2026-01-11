from fastapi import APIRouter, HTTPException, status, Depends
from database import supabase # Assuming this is your supabase client
from models import RegisterDetails, LoginDetails, LoginResponse
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import os
import jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter()
ph = PasswordHasher()

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='/auth/token')

# --- Utilities ---

def encode_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_bearer)):
    try:
        # 1. Decode the JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # 2. Query Supabase
        response = supabase.table("users").select("*").eq("username", username).execute()
        
        # 3. Check if user exists
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="User not found")
            
        # 4. FIX: Return the first object in the list, not the entire list
        return response.data[0] 
        
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
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Fetch user from Supabase using form_data.username
    response = supabase.table("users").select("*").eq("username", form_data.username).execute()
    
    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user = response.data[0]

    # 2. Verify password using form_data.password
    try:
        ph.verify(user["password"], form_data.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # 3. Generate token
    token = encode_token({"username": user["username"]})
    
    # 4. Return standard OAuth2 response
    return {"access_token": token, "token_type": "bearer"}