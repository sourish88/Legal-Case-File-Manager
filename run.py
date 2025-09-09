"""
Entry point for the Legal Case File Manager application.

This script creates and runs the Flask application using the application factory pattern.
"""

import os

from app import create_app
from app.config.settings import config

# Get configuration from environment or default to development
config_name = os.getenv("FLASK_ENV", "development")
app = create_app(config[config_name])

if __name__ == "__main__":
    print("Starting Legal Case File Manager with PostgreSQL backend")
    print(f"Environment: {config_name}")
    db_host = app.config["DB_HOST"]
    db_port = app.config["DB_PORT"]
    print(f"Database: {app.config['DB_NAME']} on {db_host}:{db_port}")  # noqa: E231
    app_host = app.config["APP_HOST"]
    app_port = app.config["APP_PORT"]
    print(f"Server: http://{app_host}:{app_port}")  # noqa: E231

    app.run(debug=app.config["DEBUG"], host=app.config["APP_HOST"], port=app.config["APP_PORT"])
