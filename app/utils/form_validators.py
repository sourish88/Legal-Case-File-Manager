"""
Form validation utilities for web forms and POST requests.

This module provides validation for form data submitted through web interfaces.
"""

from typing import Any, Dict, List, Optional

from flask import request

from app.models.entities import (
    CASE_STATUSES,
    CASE_TYPES,
    CLIENT_STATUSES,
    CLIENT_TYPES,
    CONFIDENTIALITY_LEVELS,
    FILE_TYPES,
    PAYMENT_METHODS,
    PAYMENT_STATUSES,
    PRIORITY_LEVELS,
    STORAGE_STATUSES,
)
from app.utils.validators import InputValidator, ValidationError


class FormValidator(InputValidator):
    """Extended validator for web forms"""

    def __init__(self):
        super().__init__()

    def validate_client_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate client creation/update form

        Args:
            form_data: Form data dictionary

        Returns:
            Validated form data

        Raises:
            ValidationError: If validation fails
        """
        schema = {
            "first_name": {"type": "string", "required": True, "max_length": 100},
            "last_name": {"type": "string", "required": True, "max_length": 100},
            "email": {"type": "email", "required": True},
            "phone": {"type": "phone", "required": False},
            "address": {"type": "string", "required": False, "max_length": 500},
            "client_type": {"type": "string", "required": False, "allowed_values": CLIENT_TYPES},
            "status": {"type": "string", "required": False, "allowed_values": CLIENT_STATUSES},
            "notes": {"type": "string", "required": False, "max_length": 1000},
        }

        return self.validate_request_data(form_data, schema)

    def validate_case_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate case creation/update form

        Args:
            form_data: Form data dictionary

        Returns:
            Validated form data

        Raises:
            ValidationError: If validation fails
        """
        schema = {
            "client_id": {"type": "uuid", "required": True},
            "reference_number": {"type": "string", "required": True, "max_length": 100},
            "case_type": {"type": "string", "required": True, "allowed_values": CASE_TYPES},
            "description": {"type": "string", "required": False, "max_length": 2000},
            "assigned_lawyer": {"type": "string", "required": False, "max_length": 200},
            "case_status": {"type": "string", "required": False, "allowed_values": CASE_STATUSES},
            "priority": {"type": "string", "required": False, "allowed_values": PRIORITY_LEVELS},
            "estimated_value": {"type": "float", "required": False},
            "notes": {"type": "string", "required": False, "max_length": 1000},
        }

        return self.validate_request_data(form_data, schema)

    def validate_file_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate file creation/update form

        Args:
            form_data: Form data dictionary

        Returns:
            Validated form data

        Raises:
            ValidationError: If validation fails
        """
        schema = {
            "client_id": {"type": "uuid", "required": True},
            "case_id": {"type": "uuid", "required": False},
            "reference_number": {"type": "string", "required": True, "max_length": 100},
            "file_description": {"type": "string", "required": False, "max_length": 1000},
            "document_category": {"type": "string", "required": False, "max_length": 100},
            "file_type": {"type": "string", "required": False, "allowed_values": FILE_TYPES},
            "warehouse_location": {"type": "string", "required": False, "max_length": 100},
            "shelf_number": {"type": "string", "required": False, "max_length": 50},
            "box_number": {"type": "string", "required": False, "max_length": 50},
            "storage_status": {"type": "string", "required": False, "allowed_values": STORAGE_STATUSES},
            "confidentiality_level": {"type": "string", "required": False, "allowed_values": CONFIDENTIALITY_LEVELS},
            "keywords": {"type": "string", "required": False, "max_length": 500},
            "notes": {"type": "string", "required": False, "max_length": 1000},
        }

        validated = self.validate_request_data(form_data, schema)

        # Process keywords if provided
        if validated.get("keywords"):
            keywords_str = validated["keywords"]
            # Split by comma and clean up
            keywords_list = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
            validated["keywords"] = keywords_list

        return validated

    def validate_payment_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate payment creation/update form

        Args:
            form_data: Form data dictionary

        Returns:
            Validated form data

        Raises:
            ValidationError: If validation fails
        """
        schema = {
            "client_id": {"type": "uuid", "required": True},
            "case_id": {"type": "uuid", "required": False},
            "amount": {"type": "float", "required": True},
            "payment_method": {"type": "string", "required": False, "allowed_values": PAYMENT_METHODS},
            "status": {"type": "string", "required": False, "allowed_values": PAYMENT_STATUSES},
            "description": {"type": "string", "required": False, "max_length": 500},
            "invoice_number": {"type": "string", "required": False, "max_length": 100},
            "notes": {"type": "string", "required": False, "max_length": 1000},
        }

        validated = self.validate_request_data(form_data, schema)

        # Additional validation for amount
        if validated.get("amount") is not None:
            if validated["amount"] < 0:
                raise ValidationError("Amount cannot be negative", "amount", "INVALID_VALUE")

        return validated

    def validate_search_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate search form data

        Args:
            form_data: Form data dictionary

        Returns:
            Validated form data

        Raises:
            ValidationError: If validation fails
        """
        # Validate search query
        query = form_data.get("query", "").strip()
        validated_query = self.validate_search_query(query)

        # Validate filters
        filters = {}
        filter_fields = ["case_type", "file_type", "confidentiality_level", "warehouse_location", "storage_status"]

        for field in filter_fields:
            value = form_data.get(field, "").strip()
            if value:
                filters[field] = value

        validated_filters = self.validate_filters(filters)

        return {"query": validated_query, "filters": validated_filters}

    def validate_file_upload(self, file_data: Any, max_size: int = 16 * 1024 * 1024) -> Dict[str, Any]:
        """
        Validate file upload

        Args:
            file_data: File data from request
            max_size: Maximum file size in bytes

        Returns:
            Validated file information

        Raises:
            ValidationError: If file is invalid
        """
        if not file_data:
            raise ValidationError("No file provided", "file", "REQUIRED")

        # Check if file has a filename
        if not hasattr(file_data, "filename") or not file_data.filename:
            raise ValidationError("File must have a filename", "file", "INVALID_FILE")

        filename = file_data.filename

        # Validate filename
        if len(filename) > 255:
            raise ValidationError("Filename too long", "filename", "TOO_LONG")

        # Check file extension (basic validation)
        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".rtf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".xls",
            ".xlsx",
            ".csv",
            ".zip",
            ".rar",
            ".7z",
        }

        file_ext = filename.lower().split(".")[-1] if "." in filename else ""
        if file_ext and f".{file_ext}" not in allowed_extensions:
            raise ValidationError(f"File type '.{file_ext}' not allowed", "file", "INVALID_TYPE")

        # Check file size if available
        if hasattr(file_data, "content_length") and file_data.content_length:
            if file_data.content_length > max_size:
                raise ValidationError(f"File size exceeds maximum allowed size ({max_size} bytes)", "file", "TOO_LARGE")

        # Sanitize filename
        from app.utils.security import sanitize_filename

        safe_filename = sanitize_filename(filename)

        return {
            "original_filename": filename,
            "safe_filename": safe_filename,
            "file_extension": file_ext,
            "file_data": file_data,
        }

    def validate_bulk_operation(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate bulk operation form data

        Args:
            form_data: Form data dictionary

        Returns:
            Validated form data

        Raises:
            ValidationError: If validation fails
        """
        # Validate selected items
        selected_items = form_data.get("selected_items", [])
        if not selected_items:
            raise ValidationError("No items selected", "selected_items", "REQUIRED")

        # Validate each selected item ID
        validated_items = []
        for item_id in selected_items:
            if isinstance(item_id, str):
                validated_id = self.validate_file_id(item_id.strip())
                validated_items.append(validated_id)
            else:
                raise ValidationError("Invalid item ID format", "selected_items", "INVALID_FORMAT")

        # Validate operation type
        operation = form_data.get("operation", "").strip().lower()
        allowed_operations = ["delete", "archive", "restore", "update_status", "move"]

        if operation not in allowed_operations:
            raise ValidationError(
                f"Invalid operation. Allowed: {', '.join(allowed_operations)}", "operation", "INVALID_VALUE"
            )

        validated = {"selected_items": validated_items, "operation": operation}

        # Validate additional parameters based on operation
        if operation == "update_status":
            new_status = form_data.get("new_status", "").strip()
            if new_status not in STORAGE_STATUSES:
                raise ValidationError(
                    f"Invalid status. Allowed: {', '.join(STORAGE_STATUSES)}", "new_status", "INVALID_VALUE"
                )
            validated["new_status"] = new_status

        elif operation == "move":
            new_location = form_data.get("new_location", "").strip()
            if not new_location:
                raise ValidationError("New location is required for move operation", "new_location", "REQUIRED")
            validated["new_location"] = self.sanitize_string(new_location, max_length=100)

        return validated


# Global form validator instance
form_validator = FormValidator()


def validate_form_data(validation_func):
    """
    Decorator for validating form data

    Args:
        validation_func: Function to validate form data
    """

    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Get form data
                if request.method == "POST":
                    form_data = dict(request.form)
                    # Also include JSON data if present
                    json_data = request.get_json(silent=True)
                    if json_data:
                        form_data.update(json_data)
                else:
                    form_data = dict(request.args)

                # Validate form data
                validated_data = validation_func(form_data)

                # Add validated data to kwargs
                kwargs["validated_data"] = validated_data

                return func(*args, **kwargs)

            except ValidationError as e:
                from flask import jsonify, render_template

                if request.is_json or request.headers.get("Accept") == "application/json":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Validation failed",
                                "details": {"message": e.message, "field": e.field, "code": e.code},
                            }
                        ),
                        400,
                    )
                else:
                    # For web forms, render error page or redirect with flash message
                    from flask import flash, redirect, url_for

                    flash(f"Validation Error: {e.message}", "error")
                    return redirect(request.referrer or url_for("main.dashboard"))

            except Exception as e:
                from flask import jsonify

                return (
                    jsonify({"success": False, "error": "Internal server error", "details": {"message": str(e)}}),
                    500,
                )

        return wrapper

    return decorator
