import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')  # Secret key for session management and CSRF protection

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )  # Database URI using environment variables for username, password, host, port, and db name

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable modification tracking to save resources
    WTF_CSRF_ENABLED = True  # Enable CSRF protection
    LOGGING_LEVEL = 'DEBUG'  # Log level (can be DEBUG, INFO, WARNING, ERROR, or CRITICAL)


class DevelopmentConfig(Config):
    DEBUG = True  # Enable debugging in the development environment


class ProductionConfig(Config):
    DEBUG = False  # Disable debugging in the production environment
