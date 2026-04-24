from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from utils.config import settings
from auth.models import TokenData
from utils.logger import setup_logger

logger = setup_logger(__name__)

class JWTHandler:    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        try:
            to_encode = data.copy()
            
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )
            
            to_encode.update({
                "exp": expire,
                "type": "access",
                "iat": datetime.utcnow()
            })
            
            encoded_jwt = jwt.encode(
                to_encode, 
                settings.SECRET_KEY, 
                algorithm=settings.ALGORITHM
            )
            
            logger.debug(f"Access token created for user: {data.get('sub')}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            
            to_encode.update({
                "exp": expire,
                "type": "refresh",
                "iat": datetime.utcnow()
            })
            
            encoded_jwt = jwt.encode(
                to_encode,
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            
            logger.debug(f"Refresh token created for user: {data.get('sub')}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            token_type_from_payload: str = payload.get("type")
            
            if username is None or user_id is None:
                logger.warning("Token missing required fields")
                return None
            
            if token_type_from_payload != token_type:
                logger.warning(
                    f"Token type mismatch. Expected: {token_type}, "
                    f"Got: {token_type_from_payload}"
                )
                return None
            
            logger.debug(f"Token verified successfully for user: {username}")
            return TokenData(username=username, user_id=user_id)
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None