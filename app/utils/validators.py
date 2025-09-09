"""
Input validation and sanitization utilities for the Legal Case File Manager.

This module provides comprehensive validation for all user inputs including
search queries, file IDs, pagination parameters, and form data.
Includes protection against SQL injection, XSS attacks, and other security threats.
"""

import html
import re
import uuid
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import unquote

from flask import abort, jsonify, request

# Import constants from entities for validation
from app.models.entities import (
    ACCESS_TYPES,
    CASE_STATUSES,
    CASE_TYPES,
    CLIENT_STATUSES,
    CLIENT_TYPES,
    COMMENT_TYPES,
    CONFIDENTIALITY_LEVELS,
    FILE_TYPES,
    PAYMENT_METHODS,
    PAYMENT_STATUSES,
    PRIORITY_LEVELS,
    STORAGE_STATUSES,
)


class ValidationError(Exception):
    """Custom exception for validation errors"""

    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code or "VALIDATION_ERROR"
        super().__init__(self.message)


class InputValidator:
    """Comprehensive input validation and sanitization class"""

    # Security patterns for detection
    SQL_INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|sp_|xp_)\b)",
        r"(--|\/\*|\*\/|;)",
        r"(\b(or|and)\s+\d+\s*=\s*\d+)",
        r"(\'\s*(or|and|union|select|insert|update|delete))",
        r"(\bwhere\s+\d+\s*=\s*\d+)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
    ]

    # Valid characters for different input types
    ALPHANUMERIC_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_\.]+$")
    UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    PHONE_PATTERN = re.compile(r"^[\+]?[1-9]?[\d\s\-\(\)\.]{7,15}$")

    def __init__(self):
        self.errors = []

    def reset_errors(self):
        """Reset validation errors"""
        self.errors = []

    def add_error(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation error"""
        self.errors.append({"message": message, "field": field, "code": code or "VALIDATION_ERROR"})

    def has_errors(self) -> bool:
        """Check if there are validation errors"""
        return len(self.errors) > 0

    def get_errors(self) -> List[Dict[str, str]]:
        """Get all validation errors"""
        return self.errors.copy()

    def sanitize_string(
        self,
        value: Optional[str],
        max_length: Optional[int] = None,
        allow_html: bool = False,
        strip_whitespace: bool = True,
    ) -> str:
        """
        Sanitize string input with various options

        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML (default: False, will escape HTML)
            strip_whitespace: Whether to strip leading/trailing whitespace

        Returns:
            Sanitized string
        """
        if value is None:
            return ""

        # Ensure we have a string to work with
        if not isinstance(value, str):
            value = str(value)  # type: ignore

        # URL decode if needed
        if "%" in value:
            try:
                value = unquote(value)
            except Exception:
                pass  # Keep original if decoding fails

        # Strip whitespace if requested
        if strip_whitespace:
            value = value.strip()

        # HTML escape if not allowing HTML
        if not allow_html:
            value = html.escape(value, quote=True)

        # Truncate if max_length specified
        if max_length and len(value) > max_length:
            value = value[:max_length]

        return value

    def detect_sql_injection(self, value: Any) -> bool:
        """Detect potential SQL injection attempts"""
        if not isinstance(value, str):
            return False

        value_lower = value.lower()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False

    def detect_xss(self, value: Any) -> bool:
        """Detect potential XSS attempts"""
        if not isinstance(value, str):
            return False

        value_lower = value.lower()
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False

    def validate_search_query(self, query: str, field_name: str = "query") -> str:
        """
        Validate and sanitize search query

        Args:
            query: Search query string
            field_name: Name of the field for error reporting

        Returns:
            Sanitized query string

        Raises:
            ValidationError: If query is invalid
        """
        if not query:
            return ""

        if not isinstance(query, str):
            raise ValidationError("Search query must be a string", field_name, "INVALID_TYPE")

        # Check for security threats
        if self.detect_sql_injection(query):
            raise ValidationError("Invalid characters detected in search query", field_name, "SECURITY_THREAT")

        if self.detect_xss(query):
            raise ValidationError("Invalid characters detected in search query", field_name, "SECURITY_THREAT")

        # Additional validation for search queries
        if len(query) > 500:
            raise ValidationError("Search query too long (max 500 characters)", field_name, "TOO_LONG")

        # Sanitize the query
        sanitized = self.sanitize_string(query, max_length=500)

        # Check for excessive special characters (potential attack)
        special_char_count = sum(1 for c in sanitized if not c.isalnum() and c not in " -_.")
        if special_char_count > len(sanitized) * 0.3:  # More than 30% special chars
            raise ValidationError("Search query contains too many special characters", field_name, "INVALID_FORMAT")

        return sanitized

    def validate_file_id(self, file_id: str, field_name: str = "file_id") -> str:
        """
        Validate file ID (should be UUID format)

        Args:
            file_id: File ID to validate
            field_name: Name of the field for error reporting

        Returns:
            Validated file ID

        Raises:
            ValidationError: If file ID is invalid
        """
        if not file_id:
            raise ValidationError("File ID is required", field_name, "REQUIRED")

        if not isinstance(file_id, str):
            raise ValidationError("File ID must be a string", field_name, "INVALID_TYPE")

        # Sanitize first
        sanitized = self.sanitize_string(file_id.strip())

        # Check if it's a valid UUID
        if not self.UUID_PATTERN.match(sanitized):
            raise ValidationError("Invalid file ID format", field_name, "INVALID_FORMAT")

        return sanitized

    def validate_pagination(
        self, limit: Optional[Union[str, int]] = None, offset: Optional[Union[str, int]] = None, max_limit: int = 1000
    ) -> Dict[str, int]:
        """
        Validate pagination parameters

        Args:
            limit: Limit parameter
            offset: Offset parameter
            max_limit: Maximum allowed limit

        Returns:
            Dictionary with validated limit and offset

        Raises:
            ValidationError: If parameters are invalid
        """
        result = {}

        # Validate limit
        if limit is not None:
            try:
                limit_int = int(limit)
                if limit_int < 1:
                    raise ValidationError("Limit must be positive", "limit", "INVALID_VALUE")
                if limit_int > max_limit:
                    raise ValidationError(f"Limit cannot exceed {max_limit}", "limit", "TOO_LARGE")
                result["limit"] = limit_int
            except (ValueError, TypeError):
                raise ValidationError("Limit must be a valid integer", "limit", "INVALID_TYPE")
        else:
            result["limit"] = 20  # Default limit

        # Validate offset
        if offset is not None:
            try:
                offset_int = int(offset)
                if offset_int < 0:
                    raise ValidationError("Offset cannot be negative", "offset", "INVALID_VALUE")
                result["offset"] = offset_int
            except (ValueError, TypeError):
                raise ValidationError("Offset must be a valid integer", "offset", "INVALID_TYPE")
        else:
            result["offset"] = 0  # Default offset

        return result

    def validate_filter_value(self, value: str, filter_name: str, allowed_values: Optional[List[str]] = None) -> str:
        """
        Validate filter values

        Args:
            value: Filter value to validate
            filter_name: Name of the filter
            allowed_values: List of allowed values (optional)

        Returns:
            Validated filter value

        Raises:
            ValidationError: If filter value is invalid
        """
        if not value:
            return ""

        if not isinstance(value, str):
            raise ValidationError(f"{filter_name} must be a string", filter_name, "INVALID_TYPE")

        # Sanitize
        sanitized = self.sanitize_string(value, max_length=100)

        # Check against allowed values if provided
        if allowed_values and sanitized not in allowed_values:
            raise ValidationError(
                f"Invalid {filter_name} value. Allowed values: {', '.join(allowed_values)}",
                filter_name,
                "INVALID_VALUE",
            )

        return sanitized

    def validate_filters(self, filters: Dict[str, str]) -> Dict[str, str]:
        """
        Validate all filter parameters

        Args:
            filters: Dictionary of filter parameters

        Returns:
            Dictionary of validated filters

        Raises:
            ValidationError: If any filter is invalid
        """
        validated = {}

        filter_mappings = {
            "case_type": CASE_TYPES,
            "file_type": FILE_TYPES,
            "confidentiality": CONFIDENTIALITY_LEVELS,
            "confidentiality_level": CONFIDENTIALITY_LEVELS,
            "warehouse": None,  # Dynamic values from database
            "warehouse_location": None,  # Dynamic values from database
            "storage_status": STORAGE_STATUSES,
            "payment_method": PAYMENT_METHODS,
            "payment_status": PAYMENT_STATUSES,
            "access_type": ACCESS_TYPES,
            "comment_type": COMMENT_TYPES,
            "client_type": CLIENT_TYPES,
            "client_status": CLIENT_STATUSES,
            "case_status": CASE_STATUSES,
            "priority": PRIORITY_LEVELS,
        }

        for key, value in filters.items():
            if key in filter_mappings:
                allowed_values = filter_mappings[key]
                validated[key] = self.validate_filter_value(value, key, allowed_values)
            else:
                # For unknown filters, just sanitize
                validated[key] = self.sanitize_string(str(value), max_length=100)

        return validated

    def validate_boolean_param(self, value: Optional[Union[str, bool]], field_name: str, default: bool = False) -> bool:
        """
        Validate boolean parameters

        Args:
            value: Value to validate
            field_name: Name of the field
            default: Default value if None

        Returns:
            Boolean value

        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ("true", "1", "yes", "on"):
                return True
            elif value_lower in ("false", "0", "no", "off"):
                return False

        raise ValidationError(f"{field_name} must be a boolean value", field_name, "INVALID_TYPE")

    def validate_email(self, email: str, field_name: str = "email", required: bool = True) -> Optional[str]:
        """
        Validate email address

        Args:
            email: Email to validate
            field_name: Name of the field
            required: Whether email is required

        Returns:
            Validated email or None

        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            if required:
                raise ValidationError("Email is required", field_name, "REQUIRED")
            return None

        if not isinstance(email, str):
            raise ValidationError("Email must be a string", field_name, "INVALID_TYPE")

        sanitized = self.sanitize_string(email, max_length=254).lower()

        if not self.EMAIL_PATTERN.match(sanitized):
            raise ValidationError("Invalid email format", field_name, "INVALID_FORMAT")

        return sanitized

    def validate_phone(self, phone: str, field_name: str = "phone", required: bool = False) -> Optional[str]:
        """
        Validate phone number

        Args:
            phone: Phone number to validate
            field_name: Name of the field
            required: Whether phone is required

        Returns:
            Validated phone number or None

        Raises:
            ValidationError: If phone number is invalid
        """
        if not phone:
            if required:
                raise ValidationError("Phone number is required", field_name, "REQUIRED")
            return None

        if not isinstance(phone, str):
            raise ValidationError("Phone number must be a string", field_name, "INVALID_TYPE")

        sanitized = self.sanitize_string(phone, max_length=20)

        if not self.PHONE_PATTERN.match(sanitized):
            raise ValidationError("Invalid phone number format", field_name, "INVALID_FORMAT")

        return sanitized

    def _validate_string_field(self, value: Any, field: str, max_length: Optional[int] = None) -> str:
        """Validate and sanitize a string field."""
        if not isinstance(value, str):
            raise ValidationError(f"{field} must be a string", field, "INVALID_TYPE")
        return self.sanitize_string(value, max_length=max_length)

    def _validate_email_field(self, value: Any, field: str) -> str:
        """Validate an email field."""
        email_result = self.validate_email(value, field, True)
        if email_result is None:
            raise ValidationError(f"{field} validation failed", field, "VALIDATION_ERROR")
        return email_result

    def _validate_phone_field(self, value: Any, field: str) -> str:
        """Validate a phone field."""
        phone_result = self.validate_phone(value, field, True)
        if phone_result is None:
            raise ValidationError(f"{field} validation failed", field, "VALIDATION_ERROR")
        return phone_result

    def _validate_uuid_field(self, value: Any, field: str) -> str:
        """Validate a UUID field."""
        return self.validate_file_id(value, field)

    def _validate_integer_field(self, value: Any, field: str) -> int:
        """Validate an integer field."""
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field} must be an integer", field, "INVALID_TYPE")

    def _validate_float_field(self, value: Any, field: str) -> float:
        """Validate a float field."""
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field} must be a number", field, "INVALID_TYPE")

    def _validate_boolean_field(self, value: Any, field: str) -> bool:
        """Validate a boolean field."""
        return self.validate_boolean_param(value, field)

    def _validate_field_by_type(self, value: Any, field: str, field_type: str, max_length: Optional[int] = None) -> Any:
        """Validate a field based on its type."""
        if field_type == "string":
            return self._validate_string_field(value, field, max_length)
        elif field_type == "email":
            return self._validate_email_field(value, field)
        elif field_type == "phone":
            return self._validate_phone_field(value, field)
        elif field_type == "uuid":
            return self._validate_uuid_field(value, field)
        elif field_type == "integer":
            return self._validate_integer_field(value, field)
        elif field_type == "float":
            return self._validate_float_field(value, field)
        elif field_type == "boolean":
            return self._validate_boolean_field(value, field)
        else:
            # Default string handling
            return self.sanitize_string(str(value), max_length=max_length)

    def _check_required_field(self, value: Any, field: str, required: bool) -> bool:
        """Check if a required field is present and valid."""
        if required and (value is None or value == ""):
            raise ValidationError(f"{field} is required", field, "REQUIRED")
        return value is None or value == ""

    def _check_allowed_values(self, value: Any, field: str, allowed_values: Optional[List[str]]) -> None:
        """Check if field value is in allowed values."""
        if allowed_values and value not in allowed_values:
            raise ValidationError(
                f"Invalid {field} value. Allowed values: {', '.join(map(str, allowed_values))}",
                field,
                "INVALID_VALUE",
            )

    def validate_request_data(self, data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate request data against a schema

        Args:
            data: Request data to validate
            schema: Validation schema

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
        """
        validated: Dict[str, Any] = {}

        for field, rules in schema.items():
            value = data.get(field)
            field_type = rules.get("type", "string")
            required = rules.get("required", False)
            max_length = rules.get("max_length")
            allowed_values = rules.get("allowed_values")

            # Check if required and handle empty values
            if self._check_required_field(value, field, required):
                validated[field] = None
                continue

            # Validate field by type
            validated[field] = self._validate_field_by_type(value, field, field_type, max_length)

            # Check allowed values
            self._check_allowed_values(validated[field], field, allowed_values)

        return validated


# Global validator instance
validator = InputValidator()


def validate_api_request(validation_rules: Optional[Dict[str, Dict[str, Any]]] = None):
    """
    Decorator for validating API requests

    Args:
        validation_rules: Dictionary of validation rules for request parameters
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                validator.reset_errors()

                # Get request parameters
                if request.method == "GET":
                    params = dict(request.args)
                elif request.method in ["POST", "PUT", "PATCH"]:
                    params = dict(request.get_json() or {})
                    params.update(dict(request.args))  # Include query params
                else:
                    params = {}

                # Add URL parameters
                params.update(kwargs)

                # Apply validation rules if provided
                if validation_rules:
                    validated_params = validator.validate_request_data(params, validation_rules)
                    kwargs.update(validated_params)

                return func(*args, **kwargs)

            except ValidationError as e:
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
            except Exception as e:
                return (
                    jsonify({"success": False, "error": "Internal server error", "details": {"message": str(e)}}),
                    500,
                )

        return wrapper

    return decorator


def validate_search_params():
    """Decorator specifically for search API endpoints"""
    search_rules = {
        "q": {"type": "string", "max_length": 500},
        "query": {"type": "string", "max_length": 500},
        "limit": {"type": "integer"},
        "offset": {"type": "integer"},
        "include_private": {"type": "boolean"},
        "case_type": {"type": "string", "allowed_values": CASE_TYPES},
        "file_type": {"type": "string", "allowed_values": FILE_TYPES},
        "confidentiality": {"type": "string", "allowed_values": CONFIDENTIALITY_LEVELS},
        "warehouse": {"type": "string", "max_length": 100},
        "storage_status": {"type": "string", "allowed_values": STORAGE_STATUSES},
    }

    return validate_api_request(cast(Optional[Dict[str, Dict[str, Any]]], search_rules))


def validate_file_id_param():
    """Decorator for endpoints that require file_id parameter"""
    file_id_rules = {"file_id": {"type": "uuid", "required": True}}

    return validate_api_request(file_id_rules)
