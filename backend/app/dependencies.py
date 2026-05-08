from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from auth.jwt_handler import JWTHandler
from auth.user_manager import UserManager
from auth.models import User
from utils.logger import setup_logger

logger = setup_logger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    
    # Verify token
    token_data = JWTHandler.verify_token(token, token_type="access")
    
    if token_data is None:
        logger.warning("Invalid authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = UserManager.get_user_by_id(token_data.user_id)
    
    if user is None:
        logger.warning(f"User not found: {token_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[User]:
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        token_data = JWTHandler.verify_token(token, token_type="access")
        
        if token_data is None:
            return None
        
        user = UserManager.get_user_by_id(token_data.user_id)
        return user if user and user.is_active else None
        
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None