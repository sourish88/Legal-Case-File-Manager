"""
Error handlers for the Legal Case File Manager.

This module contains error handling routes and functions.
"""

from flask import render_template


def register_error_handlers(app):
    """Register error handlers with the Flask app"""

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("500.html"), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle unexpected exceptions"""
        print(f"Unexpected error: {e}")
        return render_template("500.html"), 500
