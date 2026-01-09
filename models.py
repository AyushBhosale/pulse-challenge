from enum import Enum
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserStatus(str, Enum):
    ADMIN = "Admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class RegisterDetails(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    organization: bool = False
    status: UserStatus = UserStatus.VIEWER
    password: str = Field(..., min_length=8)

class LoginDetails(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    message: str
    username: str