"""
Configuration settings for the Legal Case File Manager application.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class"""

    # Flask Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "legal_case_manager")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    # Application Settings
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 5000))

    # Additional settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "development")  # 'json' for production, 'development' for dev
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    LOG_ENABLE_CONSOLE = os.getenv("LOG_ENABLE_CONSOLE", "true").lower() == "true"

    @classmethod
    def get_database_config(cls):
        """Get database configuration as dictionary"""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }

    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
        missing_vars = []

        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"Missing required configuration variables: {', '.join(missing_vars)}")

        return True


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    FLASK_ENV = "production"

    # Override defaults for production
    SECRET_KEY = os.getenv("SECRET_KEY") or "MUST_BE_SET_IN_PRODUCTION"  # Must be set in production

    # Production logging defaults
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")
    LOG_ENABLE_CONSOLE = os.getenv("LOG_ENABLE_CONSOLE", "false").lower() == "true"

    @classmethod
    def validate_config(cls):
        """Additional validation for production"""
        super().validate_config()

        secret_key = getattr(cls, 'SECRET_KEY', '')
        if not secret_key or secret_key == "dev-key-change-in-production":
            raise ValueError("SECRET_KEY must be set to a secure value in production")


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    DEBUG = True
    DB_NAME = os.getenv("TEST_DB_NAME", "legal_case_manager_test")


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
