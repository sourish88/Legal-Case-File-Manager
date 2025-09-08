"""
Entry point for the Legal Case File Manager application.

This script creates and runs the Flask application using the application factory pattern.
"""

import os
from app import create_app
from app.config.settings import config

# Get configuration from environment or default to development
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config[config_name])

if __name__ == '__main__':
    print("Starting Legal Case File Manager with PostgreSQL backend")
    print(f"Environment: {config_name}")
    print(f"Database: {app.config['DB_NAME']} on {app.config['DB_HOST']}:{app.config['DB_PORT']}")
    print(f"Server: http://{app.config['APP_HOST']}:{app.config['APP_PORT']}")
    
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['APP_HOST'],
        port=app.config['APP_PORT']
    )
