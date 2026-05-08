import bcrypt
import logging

logger = logging.getLogger(__name__)


class PasswordHandler:
    
    @staticmethod
    def hash_password(password: str) -> str:
        try:
            password_bytes = password.encode('utf-8')[:72]
            
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            hashed_str = hashed.decode('utf-8')
            logger.debug("Password hashed successfully")
            return hashed_str
            
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            raise ValueError(f"Error hashing password: {str(e)}")
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            password_bytes = plain_password.encode('utf-8')[:72]
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Verify
            result = bcrypt.checkpw(password_bytes, hashed_bytes)
            logger.debug(f"Password verification: {'success' if result else 'failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False