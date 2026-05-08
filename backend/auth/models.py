from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Check byte length for bcrypt compatibility
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes')
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # i will add strong password checks here later

        return v


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: str
    created_at: datetime
    is_active: bool = True
    is_admin: bool = False
    
    class Config:
        from_attributes = True


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True