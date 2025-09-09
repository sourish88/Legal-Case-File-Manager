"""
Example implementations showing how to use the validation system.

This module provides examples of integrating validation with various endpoints
and demonstrates best practices for input validation and security.
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.utils.form_validators import form_validator, validate_form_data
from app.utils.security import log_security_event, require_api_key, secure_headers
from app.utils.validators import ValidationError, validate_api_request, validator

# Example blueprint
examples_bp = Blueprint("examples", __name__, url_prefix="/examples")


# Example 1: API endpoint with comprehensive validation
@examples_bp.route("/api/advanced-search", methods=["GET"])
@validate_api_request(
    {
        "q": {"type": "string", "max_length": 500, "required": False},
        "category": {"type": "string", "allowed_values": ["files", "clients", "cases"], "required": False},
        "limit": {"type": "integer", "required": False},
        "offset": {"type": "integer", "required": False},
        "include_archived": {"type": "boolean", "required": False},
        "date_from": {"type": "string", "required": False},
        "date_to": {"type": "string", "required": False},
    }
)
@secure_headers
def advanced_search():
    """Example of advanced search with comprehensive validation"""
    try:
        # All parameters are already validated by the decorator
        query = request.args.get("q", "")
        category = request.args.get("category", "files")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        # include_archived = request.args.get("include_archived", "false").lower() == "true"

        # Additional custom validation if needed
        if query and len(query) < 2:
            raise ValidationError("Query must be at least 2 characters", "q", "TOO_SHORT")

        # Your search logic here
        results = {
            "query": query,
            "category": category,
            "results": [],  # Your actual search results
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

        return jsonify({"success": True, "data": results})

    except ValidationError as e:
        log_security_event(
            "validation_error", {"endpoint": "/examples/api/advanced-search", "error": e.message, "field": e.field}
        )
        return jsonify({"success": False, "error": e.message, "field": e.field, "code": e.code}), 400


# Example 2: Protected API endpoint with API key requirement
@examples_bp.route("/api/admin/bulk-delete", methods=["POST"])
@require_api_key
@validate_api_request(
    {
        "file_ids": {"type": "string", "required": True},  # JSON array as string
        "confirm": {"type": "boolean", "required": True},
        "reason": {"type": "string", "max_length": 500, "required": False},
    }
)
@secure_headers
def bulk_delete():
    """Example of protected bulk operation with validation"""
    try:
        # Parse file IDs
        import json

        file_ids_str = request.json.get("file_ids", "[]")
        file_ids = json.loads(file_ids_str) if isinstance(file_ids_str, str) else file_ids_str

        # Validate each file ID
        validated_ids = []
        for file_id in file_ids:
            validated_id = validator.validate_file_id(file_id)
            validated_ids.append(validated_id)

        if not validated_ids:
            raise ValidationError("At least one file ID is required", "file_ids", "REQUIRED")

        confirm = request.json.get("confirm", False)
        if not confirm:
            raise ValidationError("Confirmation is required for bulk delete", "confirm", "REQUIRED")

        reason = request.json.get("reason", "")
        if reason:
            reason = validator.sanitize_string(reason, max_length=500)

        # Log the operation
        log_security_event(
            "bulk_delete_attempt", {"file_count": len(validated_ids), "reason": reason, "ip": request.remote_addr}
        )

        # Your bulk delete logic here
        # deleted_count = perform_bulk_delete(validated_ids, reason)
        deleted_count = len(validated_ids)  # Placeholder

        return jsonify(
            {"success": True, "deleted_count": deleted_count, "message": f"Successfully deleted {deleted_count} files"}
        )

    except ValidationError as e:
        return jsonify({"success": False, "error": e.message, "field": e.field, "code": e.code}), 400
    except json.JSONDecodeError:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid JSON in file_ids parameter",
                    "field": "file_ids",
                    "code": "INVALID_JSON",
                }
            ),
            400,
        )


# Example 3: Web form with validation
@examples_bp.route("/create-client", methods=["GET", "POST"])
@validate_form_data(form_validator.validate_client_form)
@secure_headers
def create_client(validated_data=None):
    """Example of web form with validation"""
    if request.method == "GET":
        return render_template("examples/create_client.html")

    try:
        # validated_data is provided by the decorator
        # Your client creation logic here
        # client_id = create_new_client(validated_data)
        client_id = "example-client-id"  # Placeholder

        flash(f"Client created successfully! ID: {client_id}", "success")
        return redirect(url_for("examples.create_client"))

    except Exception as e:
        flash(f"Error creating client: {str(e)}", "error")
        return redirect(url_for("examples.create_client"))


# Example 4: File upload with validation
@examples_bp.route("/upload-file", methods=["POST"])
@secure_headers
def upload_file():
    """Example of file upload with validation"""
    try:
        # Check if file is present
        if "file" not in request.files:
            raise ValidationError("No file provided", "file", "REQUIRED")

        file_data = request.files["file"]

        # Validate file upload
        file_info = form_validator.validate_file_upload(file_data, max_size=10 * 1024 * 1024)  # 10MB

        # Validate additional form data
        form_data = {
            "client_id": request.form.get("client_id", ""),
            "description": request.form.get("description", ""),
            "confidentiality_level": request.form.get("confidentiality_level", "Internal"),
        }

        # Validate client_id
        if form_data["client_id"]:
            form_data["client_id"] = validator.validate_file_id(form_data["client_id"])

        # Validate description
        if form_data["description"]:
            form_data["description"] = validator.sanitize_string(form_data["description"], max_length=1000)

        # Validate confidentiality level
        from app.models.entities import CONFIDENTIALITY_LEVELS

        if form_data["confidentiality_level"] not in CONFIDENTIALITY_LEVELS:
            raise ValidationError("Invalid confidentiality level", "confidentiality_level", "INVALID_VALUE")

        # Your file processing logic here
        # file_id = save_uploaded_file(file_info, form_data)
        file_id = "example-file-id"  # Placeholder

        return jsonify(
            {
                "success": True,
                "file_id": file_id,
                "filename": file_info["safe_filename"],
                "message": "File uploaded successfully",
            }
        )

    except ValidationError as e:
        log_security_event(
            "file_upload_validation_error", {"error": e.message, "field": e.field, "ip": request.remote_addr}
        )
        return jsonify({"success": False, "error": e.message, "field": e.field, "code": e.code}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Example 5: Custom validation decorator
def validate_user_permissions(required_role="user"):
    """Custom decorator for validating user permissions"""

    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Your authentication/authorization logic here
            # For this example, we'll just check a header
            user_role = request.headers.get("X-User-Role", "guest")

            role_hierarchy = {"guest": 0, "user": 1, "admin": 2, "superuser": 3}

            required_level = role_hierarchy.get(required_role, 1)
            user_level = role_hierarchy.get(user_role, 0)

            if user_level < required_level:
                log_security_event(
                    "unauthorized_access",
                    {
                        "endpoint": request.endpoint,
                        "required_role": required_role,
                        "user_role": user_role,
                        "ip": request.remote_addr,
                    },
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Insufficient permissions",
                            "required_role": required_role,
                            "user_role": user_role,
                        }
                    ),
                    403,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


@examples_bp.route("/api/admin-only", methods=["GET"])
@validate_user_permissions("admin")
@secure_headers
def admin_only_endpoint():
    """Example of role-protected endpoint"""
    return jsonify(
        {"success": True, "message": "This is an admin-only endpoint", "data": {"admin_info": "sensitive data"}}
    )


# Example 6: Rate-limited endpoint
@examples_bp.route("/api/public-search", methods=["GET"])
@validate_api_request(
    {"q": {"type": "string", "max_length": 200, "required": True}, "limit": {"type": "integer", "required": False}}
)
@secure_headers
def public_search():
    """Example of public endpoint with rate limiting (handled by middleware)"""
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 10))

    # Ensure reasonable limits for public endpoint
    if limit > 50:
        limit = 50

    # Your search logic here
    results = {"query": query, "results": [], "count": 0, "limit": limit}  # Your search results

    return jsonify({"success": True, "data": results})


# Example 7: Comprehensive error handling
@examples_bp.route("/api/complex-operation", methods=["POST"])
@validate_api_request(
    {
        "operation_type": {"type": "string", "required": True, "allowed_values": ["create", "update", "delete"]},
        "target_id": {"type": "uuid", "required": False},
        "data": {"type": "string", "required": False},  # JSON string
    }
)
@secure_headers
def complex_operation():
    """Example of complex operation with comprehensive error handling"""
    try:
        operation_type = request.json.get("operation_type")
        target_id = request.json.get("target_id")
        data_str = request.json.get("data", "{}")

        # Parse and validate data
        import json

        try:
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in data field: {str(e)}", "data", "INVALID_JSON")

        # Operation-specific validation
        if operation_type in ["update", "delete"] and not target_id:
            raise ValidationError("target_id is required for update and delete operations", "target_id", "REQUIRED")

        if operation_type == "create" and not data:
            raise ValidationError("data is required for create operation", "data", "REQUIRED")

        # Log the operation attempt
        log_security_event(
            "complex_operation",
            {
                "operation_type": operation_type,
                "target_id": target_id,
                "has_data": bool(data),
                "ip": request.remote_addr,
            },
        )

        # Your operation logic here
        result = {
            "operation_type": operation_type,
            "target_id": target_id,
            "success": True,
            "message": f"{operation_type.capitalize()} operation completed successfully",
        }

        return jsonify({"success": True, "data": result})

    except ValidationError as e:
        return jsonify({"success": False, "error": e.message, "field": e.field, "code": e.code}), 400
    except Exception as e:
        log_security_event(
            "operation_error",
            {
                "operation_type": request.json.get("operation_type", "unknown"),
                "error": str(e),
                "ip": request.remote_addr,
            },
        )
        return jsonify({"success": False, "error": "Internal server error", "message": str(e)}), 500


# Example template for create_client.html (you would put this in templates/examples/)
CREATE_CLIENT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Create Client - Example</title>
    <style>
        .form-group { margin: 10px 0; }
        .form-control { width: 300px; padding: 5px; }
        .btn { padding: 8px 16px; background: #007bff; color: white; border: none; cursor: pointer; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>Create New Client</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="{{ 'success' if category == 'success' else 'error' }}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label>First Name*:</label>
            <input type="text" name="first_name" class="form-control" required>
        </div>

        <div class="form-group">
            <label>Last Name*:</label>
            <input type="text" name="last_name" class="form-control" required>
        </div>

        <div class="form-group">
            <label>Email*:</label>
            <input type="email" name="email" class="form-control" required>
        </div>

        <div class="form-group">
            <label>Phone:</label>
            <input type="tel" name="phone" class="form-control">
        </div>

        <div class="form-group">
            <label>Address:</label>
            <textarea name="address" class="form-control" rows="3"></textarea>
        </div>

        <div class="form-group">
            <label>Client Type:</label>
            <select name="client_type" class="form-control">
                <option value="Individual">Individual</option>
                <option value="Corporation">Corporation</option>
                <option value="Non-Profit">Non-Profit</option>
                <option value="Government">Government</option>
                <option value="Other">Other</option>
            </select>
        </div>

        <div class="form-group">
            <label>Notes:</label>
            <textarea name="notes" class="form-control" rows="3"></textarea>
        </div>

        <button type="submit" class="btn">Create Client</button>
    </form>
</body>
</html>
"""
