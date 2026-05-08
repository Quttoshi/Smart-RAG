from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from auth.models import (
    UserCreate, 
    UserLogin, 
    Token, 
    User, 
    RefreshTokenRequest,
    UserResponse
)
from auth.user_manager import UserManager
from auth.jwt_handler import JWTHandler
from app.dependencies import get_current_user, get_current_admin_user
from utils.config import settings
from utils.logger import setup_logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = setup_logger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    #Unique username (3-50 characters), valid email and Password (min 6 characters)
    user = UserManager.create_user(user_data, is_admin=False)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    logger.info(f"New user registered: {user.username}")
    return user

#JWT access token (30 min) and refresh token (7 days)
@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    user = UserManager.authenticate_user(credentials.username, credentials.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create tokens
    access_token = JWTHandler.create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    refresh_token = JWTHandler.create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    logger.info(f"User logged in: {user.username}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Your refresh token
    
    Returns new access and refresh tokens
    """
    token_data = JWTHandler.verify_token(request.refresh_token, token_type="refresh")
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user 
    user = UserManager.get_user_by_id(token_data.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token = JWTHandler.create_access_token(
        data={"sub": token_data.username, "user_id": token_data.user_id}
    )
    refresh_token = JWTHandler.create_refresh_token(
        data={"sub": token_data.username, "user_id": token_data.user_id}
    )
    
    logger.info(f"Token refreshed for user: {token_data.username}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out. Please delete your tokens."}


@router.get("/users", response_model=List[UserResponse])
async def list_users(current_user: User = Depends(get_current_admin_user)):
    users = UserManager.get_all_users()
    logger.info(f"Admin {current_user.username} listed all users")
    return users


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    # admin cannot delete their own account
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    success = UserManager.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"Admin {current_user.username} deleted user: {user_id}")
    return {"message": "User deleted successfully"}