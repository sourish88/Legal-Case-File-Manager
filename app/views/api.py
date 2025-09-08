"""
API routes for the Legal Case File Manager.

This module contains all JSON API endpoints for the application.
"""

from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request, session

from app.services.search_service import api_intelligent_suggestions_data, unified_search_data
from app.utils.logging_config import get_logger, log_business_event, log_performance_metric
from app.utils.security import log_security_event, secure_headers
from app.utils.validators import (
    ValidationError,
    validate_api_request,
    validate_file_id_param,
    validate_search_params,
    validator,
)

api_bp = Blueprint("api", __name__)


def get_db_manager():
    """Get the database manager from the current app context"""
    from app import get_db_manager as _get_db_manager

    return _get_db_manager()


@api_bp.route("/search")
@validate_search_params()
@secure_headers
def search(**kwargs):
    """JSON API for search functionality"""
    logger = get_logger("api.search")
    start_time = datetime.utcnow()
    db_manager = get_db_manager()

    try:
        # Get validated parameters from decorator
        query = kwargs.get("q", request.args.get("q", "").strip())

        # Ensure query is validated (decorator should have done this)
        if not query:
            query = validator.validate_search_query(request.args.get("q", "").strip())

        # Validate filters
        raw_filters = {
            "case_type": request.args.get("case_type", ""),
            "file_type": request.args.get("file_type", ""),
            "confidentiality": request.args.get("confidentiality", ""),
            "warehouse": request.args.get("warehouse", ""),
            "storage_status": request.args.get("storage_status", ""),
        }

        # Remove empty filters and validate
        filters = {k: v for k, v in raw_filters.items() if v}
        validated_filters = validator.validate_filters(filters)

        # Map filter keys to database column names
        db_filters = {}
        if "case_type" in validated_filters:
            db_filters["case_type"] = validated_filters["case_type"]
        if "file_type" in validated_filters:
            db_filters["file_type"] = validated_filters["file_type"]
        if "confidentiality" in validated_filters:
            db_filters["confidentiality_level"] = validated_filters["confidentiality"]
        if "warehouse" in validated_filters:
            db_filters["warehouse_location"] = validated_filters["warehouse"]
        if "storage_status" in validated_filters:
            db_filters["storage_status"] = validated_filters["storage_status"]

        # Validate pagination
        pagination = validator.validate_pagination(limit=request.args.get("limit", 100), max_limit=1000)

        results = db_manager.search_files(query, db_filters, limit=pagination["limit"])

        # Convert datetime objects to strings for JSON serialization
        for result in results:
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif hasattr(value, "isoformat"):  # Handle date objects
                    result[key] = value.isoformat()

        # Track search analytics
        if query:
            session_id = session.get("session_id", "anonymous")
            db_manager.add_recent_search(query, session_id)
            db_manager.update_popular_search(query)

            # Log API search event
            log_business_event(
                "api_search_performed",
                query=query,
                results_count=len(results),
                filters=db_filters,
                session_id=session_id,
            )

        # Log performance
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_performance_metric("api_search_duration", duration, query=query)

        return jsonify(
            {"success": True, "results": results, "count": len(results), "query": query, "filters": db_filters}
        )

    except ValidationError as e:
        log_security_event(
            "validation_error",
            {"endpoint": "/api/search", "error": e.message, "field": e.field, "query_params": dict(request.args)},
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid input",
                    "details": {"message": e.message, "field": e.field, "code": e.code},
                    "results": [],
                    "count": 0,
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(
            "API search error",
            extra={
                "event": "api_search_error",
                "query": request.args.get("q", ""),
                "filters": request.args.to_dict(),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return jsonify({"success": False, "error": str(e), "results": [], "count": 0}), 500


@api_bp.route("/stats")
def stats():
    """JSON API for dashboard statistics"""
    logger = get_logger("api.stats")
    start_time = datetime.utcnow()
    db_manager = get_db_manager()

    try:
        stats = db_manager.get_dashboard_stats()

        # Convert Decimal to float for JSON serialization
        for key, value in stats.items():
            if hasattr(value, "__float__"):
                stats[key] = float(value)

        # Log performance
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_performance_metric("api_stats_duration", duration)

        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(
            "API stats error",
            extra={"event": "api_stats_error", "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        return jsonify({"success": False, "error": str(e), "stats": {}}), 500


@api_bp.route("/filters")
def filters():
    """JSON API for filter options"""
    db_manager = get_db_manager()

    try:
        filter_options = db_manager.get_filter_options()
        return jsonify({"success": True, "filters": filter_options})
    except Exception as e:
        logger = get_logger("api.filters")
        logger.error(
            "API filters error",
            extra={"event": "api_filters_error", "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        return jsonify({"success": False, "error": str(e), "filters": {}}), 500


@api_bp.route("/unified-search")
@validate_search_params()
@secure_headers
def unified_search(**kwargs):
    """API endpoint for unified search across all data types"""
    try:
        # Get validated parameters from decorator
        query = kwargs.get("q", request.args.get("q", ""))
        include_private = kwargs.get("include_private", request.args.get("include_private", "false"))
        limit = kwargs.get("limit", request.args.get("limit", 10))

        # Ensure query is validated (decorator should have done this)
        if not query:
            query = validator.validate_search_query(request.args.get("q", ""))

        # Handle include_private parameter
        if isinstance(include_private, str):
            include_private = validator.validate_boolean_param(include_private, "include_private", default=False)

        # Validate pagination for limit
        if isinstance(limit, str):
            limit = int(limit) if limit.isdigit() else 10
        pagination = validator.validate_pagination(limit=limit, max_limit=100)
        limit_per_category = pagination["limit"]

        # Get unified search results
        results = unified_search_data(query, {}, include_private)

        # Limit results per category to prevent overwhelming the UI
        for category in ["files", "clients", "cases", "payments", "access_history", "comments"]:
            if len(results[category]) > limit_per_category:
                results[category] = results[category][:limit_per_category]
                results[f"{category}_truncated"] = True
            else:
                results[f"{category}_truncated"] = False

        # Add category counts for summary
        results["category_counts"] = {
            "files": len(results["files"]),
            "clients": len(results["clients"]),
            "cases": len(results["cases"]),
            "payments": len(results["payments"]),
            "access_history": len(results["access_history"]),
            "comments": len(results["comments"]),
        }

        return jsonify(results)

    except ValidationError as e:
        log_security_event(
            "validation_error",
            {
                "endpoint": "/api/unified-search",
                "error": e.message,
                "field": e.field,
                "query_params": dict(request.args),
            },
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid input",
                    "details": {"message": e.message, "field": e.field, "code": e.code},
                    "files": [],
                    "clients": [],
                    "cases": [],
                    "payments": [],
                    "access_history": [],
                    "comments": [],
                    "total_results": 0,
                    "query": request.args.get("q", ""),
                }
            ),
            400,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "files": [],
                    "clients": [],
                    "cases": [],
                    "payments": [],
                    "access_history": [],
                    "comments": [],
                    "total_results": 0,
                    "query": request.args.get("q", ""),
                }
            ),
            500,
        )


@api_bp.route("/suggestions")
@validate_search_params()
@secure_headers
def suggestions(**kwargs):
    """API endpoint for intelligent search suggestions (backward compatibility)"""
    try:
        # Get validated parameters from decorator
        query = kwargs.get("q", request.args.get("q", ""))
        limit = kwargs.get("limit", request.args.get("limit", 10))

        # Ensure query is validated (decorator should have done this)
        if not query:
            query = validator.validate_search_query(request.args.get("q", ""))

        # Validate pagination for limit
        if isinstance(limit, str):
            limit = int(limit) if limit.isdigit() else 10
        pagination = validator.validate_pagination(limit=limit, max_limit=50)
        limit = pagination["limit"]

        # Get intelligent suggestions
        intelligent_suggestions = api_intelligent_suggestions_data(query, limit)

        # Format for backward compatibility - extract just the text
        simple_suggestions = [s["text"] for s in intelligent_suggestions.get("suggestions", [])]

        return jsonify({"suggestions": simple_suggestions, "intelligent": intelligent_suggestions, "query": query})

    except ValidationError as e:
        log_security_event(
            "validation_error",
            {"endpoint": "/api/suggestions", "error": e.message, "field": e.field, "query_params": dict(request.args)},
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid input",
                    "details": {"message": e.message, "field": e.field, "code": e.code},
                    "suggestions": [],
                    "intelligent": {"suggestions": []},
                    "query": request.args.get("q", ""),
                }
            ),
            400,
        )
    except Exception as e:
        return jsonify({"suggestions": [], "intelligent": {"suggestions": []}, "query": request.args.get("q", "")})


@api_bp.route("/intelligent-suggestions")
@validate_search_params()
@secure_headers
def intelligent_suggestions(**kwargs):
    """API endpoint for intelligent search suggestions"""
    try:
        # Get validated parameters from decorator
        query = kwargs.get("q", request.args.get("q", ""))
        limit = kwargs.get("limit", request.args.get("limit", 8))

        # Ensure query is validated (decorator should have done this)
        if not query:
            query = validator.validate_search_query(request.args.get("q", ""))

        # Validate pagination for limit
        if isinstance(limit, str):
            limit = int(limit) if limit.isdigit() else 8
        pagination = validator.validate_pagination(limit=limit, max_limit=50)
        limit = pagination["limit"]

        suggestions_data = api_intelligent_suggestions_data(query, limit)
        return jsonify(suggestions_data)

    except ValidationError as e:
        log_security_event(
            "validation_error",
            {
                "endpoint": "/api/intelligent-suggestions",
                "error": e.message,
                "field": e.field,
                "query_params": dict(request.args),
            },
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid input",
                    "details": {"message": e.message, "field": e.field, "code": e.code},
                    "suggestions": [],
                }
            ),
            400,
        )
    except Exception as e:
        return jsonify({"suggestions": []})


@api_bp.route("/recent-activity")
@secure_headers
def recent_activity():
    """API endpoint to get recent file access activity"""
    db_manager = get_db_manager()

    try:
        # Validate pagination
        pagination = validator.validate_pagination(limit=request.args.get("limit", 20), max_limit=200)
        limit = pagination["limit"]

        recent_accesses = db_manager.get_recent_file_accesses(limit)

        # Convert datetime objects to strings
        formatted_accesses = []
        for access in recent_accesses:
            access_dict = dict(access)
            for key, value in access_dict.items():
                if hasattr(value, "isoformat"):
                    access_dict[key] = value.isoformat() if value else None
            formatted_accesses.append(access_dict)

        return jsonify({"recent_accesses": formatted_accesses, "count": len(recent_accesses)})

    except ValidationError as e:
        log_security_event(
            "validation_error",
            {
                "endpoint": "/api/recent-activity",
                "error": e.message,
                "field": e.field,
                "query_params": dict(request.args),
            },
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid input",
                    "details": {"message": e.message, "field": e.field, "code": e.code},
                    "recent_accesses": [],
                    "count": 0,
                }
            ),
            400,
        )
    except Exception as e:
        return jsonify({"recent_accesses": [], "count": 0, "error": str(e)})


@api_bp.route("/filter-options")
def filter_options():
    """API endpoint to get available filter options"""
    db_manager = get_db_manager()

    try:
        filter_options = db_manager.get_filter_options()
        return jsonify(filter_options)
    except Exception as e:
        return jsonify(
            {
                "case_types": [],
                "file_types": [],
                "confidentiality_levels": [],
                "warehouse_locations": [],
                "storage_statuses": [],
                "error": str(e),
            }
        )


@api_bp.route("/access-history/<file_id>")
@validate_file_id_param()
@secure_headers
def access_history(file_id):
    """API endpoint to get access history for a specific file"""
    db_manager = get_db_manager()

    try:
        # Validate file_id
        validated_file_id = validator.validate_file_id(file_id)

        # Validate pagination
        pagination = validator.validate_pagination(limit=request.args.get("limit", 50), max_limit=500)

        access_history = db_manager.get_file_access_history(validated_file_id)

        # Apply pagination if needed (database method might not support it)
        if len(access_history) > pagination["limit"]:
            access_history = access_history[: pagination["limit"]]

        # Convert datetime objects to strings
        formatted_history = []
        for access in access_history:
            access_dict = dict(access)
            for key, value in access_dict.items():
                if hasattr(value, "isoformat"):
                    access_dict[key] = value.isoformat() if value else None
            formatted_history.append(access_dict)

        return jsonify(
            {"access_history": formatted_history, "count": len(access_history), "file_id": validated_file_id}
        )

    except ValidationError as e:
        log_security_event(
            "validation_error",
            {
                "endpoint": "/api/access-history",
                "error": e.message,
                "field": e.field,
                "file_id": file_id,
                "query_params": dict(request.args),
            },
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid input",
                    "details": {"message": e.message, "field": e.field, "code": e.code},
                    "access_history": [],
                    "count": 0,
                }
            ),
            400,
        )
    except Exception as e:
        return jsonify({"access_history": [], "count": 0, "error": str(e)})
