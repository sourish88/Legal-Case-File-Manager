import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'legal_case_manager')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    
    # Application Settings
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.getenv('APP_PORT', 5000))
    
    @classmethod
    def get_database_config(cls):
        """Get database configuration as dictionary"""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'database': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD
        }
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = []
        
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required configuration variables: {', '.join(missing_vars)}")
        
        return True

