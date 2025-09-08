"""
Legal Case File Manager Flask Application

A comprehensive web application for managing legal case files and client information.
"""

from flask import Flask
from app.config.settings import Config
from app.services.database import DatabaseConnection, LegalFileManagerDB

# Global database connection
db_connection = None
db_manager = None


def create_app(config_class=Config):
    """Application factory pattern for creating Flask app instances"""
    # Get the project root directory (parent of app directory)
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    
    # Load configuration
    try:
        config_class.validate_config()
        app.config.from_object(config_class)
        app.secret_key = config_class.SECRET_KEY
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your environment variables or .env file")
        raise
    
    # Initialize database connection
    global db_connection, db_manager
    try:
        db_connection = DatabaseConnection(**config_class.get_database_config())
        db_manager = LegalFileManagerDB(db_connection)
        print("Database connection established successfully")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        print("Please ensure PostgreSQL is running and credentials are correct")
        raise
    
    # Register blueprints
    from app.views.main import main_bp
    from app.views.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register migration blueprint if available
    try:
        from app.views.migration import migration_bp
        app.register_blueprint(migration_bp)
        print("Migration blueprint registered successfully")
    except ImportError:
        print("Migration blueprint not available - continuing without it")
    
    # Register error handlers
    from app.views.errors import register_error_handlers
    register_error_handlers(app)
    
    return app


def get_db_manager():
    """Get the global database manager instance"""
    return db_manager
