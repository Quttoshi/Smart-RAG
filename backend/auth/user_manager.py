import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from utils.redis_client import get_redis
from utils.logger import setup_logger
from auth.models import User, UserCreate, UserInDB
from auth.password_handler import PasswordHandler

logger = setup_logger(__name__)


class UserManager:    
    USER_PREFIX = "user:"
    USERNAME_INDEX = "username_index:"
    EMAIL_INDEX = "email_index:"
    USER_LIST_KEY = "users:list"
    
    @staticmethod
    def create_user(user_data: UserCreate, is_admin: bool = False) -> Optional[User]:
        try:
            redis_client = get_redis()
            
            if UserManager.get_user_by_username(user_data.username):
                logger.warning(f"Username already exists: {user_data.username}")
                return None
            
            if UserManager.get_user_by_email(user_data.email):
                logger.warning(f"Email already exists: {user_data.email}")
                return None
            
            # Generate user ID
            user_id = str(uuid.uuid4())
            
            hashed_password = PasswordHandler.hash_password(user_data.password)
            
            user_dict = {
                "id": user_id,
                "username": user_data.username,
                "email": user_data.email,
                "hashed_password": hashed_password,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "is_admin": is_admin
            }
            
            # Store user in Redis
            redis_client.set(
                f"{UserManager.USER_PREFIX}{user_id}",
                json.dumps(user_dict)
            )
            
            # Create indexes for quick lookup
            redis_client.set(
                f"{UserManager.USERNAME_INDEX}{user_data.username}",
                user_id
            )
            redis_client.set(
                f"{UserManager.EMAIL_INDEX}{user_data.email}",
                user_id
            )
            
            redis_client.sadd(UserManager.USER_LIST_KEY, user_id)
            
            logger.info(f"User created successfully: {user_data.username} (ID: {user_id})")
            
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        try:
            redis_client = get_redis()
            user_id = redis_client.get(f"{UserManager.USERNAME_INDEX}{username}")
            
            if not user_id:
                logger.debug(f"User not found: {username}")
                return None
            
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            if not user_data:
                logger.warning(f"User data missing for ID: {user_id}")
                return None
            
            user_dict = json.loads(user_data)
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
            
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        try:
            redis_client = get_redis()
            user_id = redis_client.get(f"{UserManager.EMAIL_INDEX}{email}")
            
            if not user_id:
                logger.debug(f"User not found with email: {email}")
                return None
            
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            if not user_data:
                logger.warning(f"User data missing for ID: {user_id}")
                return None
            
            user_dict = json.loads(user_data)
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        try:
            redis_client = get_redis()
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            
            if not user_data:
                logger.debug(f"User not found: {user_id}")
                return None
            
            user_dict = json.loads(user_data)
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        try:
            redis_client = get_redis()
            user_id = redis_client.get(f"{UserManager.USERNAME_INDEX}{username}")
            
            if not user_id:
                logger.info(f"Authentication failed: User not found - {username}")
                return None
            
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            if not user_data:
                logger.warning(f"User data missing for ID: {user_id}")
                return None
            
            user_dict = json.loads(user_data)
            
            # Verify password
            if not PasswordHandler.verify_password(password, user_dict["hashed_password"]):
                logger.info(f"Authentication failed: Invalid password - {username}")
                return None
            
            logger.info(f"Authentication successful: {username}")
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    @staticmethod
    def update_user(user_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        try:
            redis_client = get_redis()
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            
            if not user_data:
                logger.warning(f"User not found for update: {user_id}")
                return None
            
            user_dict = json.loads(user_data)
            
            allowed_fields = ["email", "is_active", "is_admin"]
            for field in allowed_fields:
                if field in update_data:
                    user_dict[field] = update_data[field]
            
            redis_client.set(
                f"{UserManager.USER_PREFIX}{user_id}",
                json.dumps(user_dict)
            )
            
            logger.info(f"User updated: {user_id}")
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None
    
    @staticmethod
    def delete_user(user_id: str) -> bool:
        try:
            redis_client = get_redis()
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            
            if not user_data:
                logger.warning(f"User not found for deletion: {user_id}")
                return False
            
            user_dict = json.loads(user_data)
            
            redis_client.delete(f"{UserManager.USER_PREFIX}{user_id}")
            
            redis_client.delete(f"{UserManager.USERNAME_INDEX}{user_dict['username']}")
            redis_client.delete(f"{UserManager.EMAIL_INDEX}{user_dict['email']}")
            
            redis_client.srem(UserManager.USER_LIST_KEY, user_id)
            
            logger.info(f"User deleted: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    @staticmethod
    def get_all_users() -> List[User]:
        try:
            redis_client = get_redis()
            user_ids = redis_client.smembers(UserManager.USER_LIST_KEY)
            
            users = []
            for user_id in user_ids:
                user = UserManager.get_user_by_id(user_id)
                if user:
                    users.append(user)
            
            logger.debug(f"Retrieved {len(users)} users")
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    @staticmethod
    def change_password(user_id: str, new_password: str) -> bool:
        try:
            redis_client = get_redis()
            user_data = redis_client.get(f"{UserManager.USER_PREFIX}{user_id}")
            
            if not user_data:
                logger.warning(f"User not found: {user_id}")
                return False
            
            user_dict = json.loads(user_data)
            
            user_dict["hashed_password"] = PasswordHandler.hash_password(new_password)
            
            redis_client.set(
                f"{UserManager.USER_PREFIX}{user_id}",
                json.dumps(user_dict)
            )
            
            logger.info(f"Password changed for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False