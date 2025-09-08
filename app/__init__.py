"""
Legal Case File Manager Flask Application

A comprehensive web application for managing legal case files and client information.
"""

from flask import Flask

from app.config.settings import Config
from app.services.database import DatabaseConnection, LegalFileManagerDB
from app.utils.logging_config import get_logger, setup_flask_logging

# Global database connection
db_connection = None
db_manager = None


def create_app(config_class=Config):
    """Application factory pattern for creating Flask app instances"""
    # Get the project root directory (parent of app directory)
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )

    # Load configuration
    try:
        config_class.validate_config()
        app.config.from_object(config_class)
        app.secret_key = config_class.SECRET_KEY
    except ValueError as e:
        # Set up basic logging first for error reporting
        setup_flask_logging(app)
        logger = get_logger("app.config")
        logger.error("Configuration validation failed", extra={"error": str(e), "config_class": config_class.__name__})
        raise

    # Set up structured logging
    setup_flask_logging(app)
    logger = get_logger("app.init")

    # Initialize database connection
    global db_connection, db_manager
    try:
        db_config = config_class.get_database_config()
        db_connection = DatabaseConnection(**db_config)
        db_manager = LegalFileManagerDB(db_connection)
        logger.info(
            "Database connection established successfully",
            extra={
                "event": "database_init_success",
                "host": db_config.get("host"),
                "database": db_config.get("database"),
                "port": db_config.get("port"),
            },
        )
    except Exception as e:
        logger.error(
            "Failed to connect to database",
            extra={
                "event": "database_init_failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "db_config": {k: v for k, v in config_class.get_database_config().items() if k != "password"},
            },
            exc_info=True,
        )
        raise

    # Register blueprints
    from app.views.api import api_bp
    from app.views.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Register migration blueprint if available
    try:
        from app.views.migration import migration_bp

        app.register_blueprint(migration_bp)
        logger.info(
            "Migration blueprint registered successfully",
            extra={"event": "blueprint_registered", "blueprint": "migration"},
        )
    except ImportError:
        logger.info(
            "Migration blueprint not available - continuing without it",
            extra={"event": "blueprint_skip", "blueprint": "migration", "reason": "not_found"},
        )

    # Register error handlers
    from app.views.errors import register_error_handlers

    register_error_handlers(app)

    return app


def get_db_manager():
    """Get the global database manager instance"""
    return db_manager
