import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth.user_manager import UserManager
from auth.models import UserCreate
from utils.config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)


def initialize_admin():
    print("Initializing admin user...")

    if not all([settings.ADMIN_USERNAME, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD]):
        logger.warning("Admin credentials not set in environment variables.")
        print("Admin credentials not found in .env file")
        print("Please add ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD to your .env")
        return

    print(f"Admin Username: {settings.ADMIN_USERNAME}")
    print(f"Admin Email: {settings.ADMIN_EMAIL}")

    existing_admin = UserManager.get_user_by_username(settings.ADMIN_USERNAME)
    if existing_admin:
        logger.info(f"Admin user '{settings.ADMIN_USERNAME}' already exists.")
        print(f"Admin user '{settings.ADMIN_USERNAME}' already exists")
        print(f"Is Admin: {existing_admin.is_admin}")
        return

    try:
        admin_data = UserCreate(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password=settings.ADMIN_PASSWORD
        )

        admin_user = UserManager.create_user(admin_data, is_admin=True)

        if admin_user:
            logger.info(f"Admin user created successfully: {admin_user.username}")
            print("Admin user created successfully!")
            print(f"Username: {admin_user.username}")
            print(f"Email: {admin_user.email}")
            print(f"Is Admin: {admin_user.is_admin}")
            print("Change the admin password after first login!")
        else:
            logger.error("Failed to create admin user")
            print("Failed to create admin user")

    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    initialize_admin()
