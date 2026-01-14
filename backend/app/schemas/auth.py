from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str
