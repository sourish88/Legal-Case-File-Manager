"""
Main web routes for the Legal Case File Manager.

This module contains the primary web interface routes including dashboard,
search, file details, and client details.
"""

import hashlib
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

from flask import Blueprint, current_app, render_template, request, session, url_for

from app.utils.helpers import get_case_type, get_client_name
from app.utils.logging_config import get_logger, log_business_event, log_performance_metric

main_bp = Blueprint("main", __name__)


def get_db_manager():
    """Get the database manager from the current app context"""
    from app import get_db_manager as _get_db_manager

    return _get_db_manager()


def get_client_recommendations_simple(client_id: str):
    """Simple client recommendations for file detail page"""
    db_manager = get_db_manager()

    try:
        # Get client information
        client = db_manager.get_client_by_id(client_id)
        if not client:
            return {}

        # Get client's cases (only active ones for file detail)
        client_cases = db_manager.get_cases_by_client(client_id)
        active_cases = [c for c in client_cases if c.get("case_status") == "Open"]

        # Get client's payments (recent ones only for file detail)
        client_payments = db_manager.get_payments_by_client(client_id)

        # Calculate payment statistics
        total_paid = sum(float(p["amount"] or 0) for p in client_payments if p["status"] == "Paid")
        total_pending = sum(float(p["amount"] or 0) for p in client_payments if p["status"] == "Pending")
        total_overdue = sum(float(p["amount"] or 0) for p in client_payments if p["status"] == "Overdue")

        # Sort payments by payment_date (recent first)
        client_payments_sorted = sorted(
            client_payments, key=lambda x: x.get("payment_date") or datetime.min, reverse=True
        )

        # Convert datetime objects to strings for template compatibility
        def convert_datetime_to_string(obj):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if hasattr(v, "isoformat"):
                        result[k] = v.isoformat() if v else None
                    elif isinstance(v, (dict, list)):
                        result[k] = convert_datetime_to_string(v)
                    else:
                        result[k] = v
                return result
            elif isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif hasattr(obj, "isoformat"):
                return obj.isoformat() if obj else None
            else:
                return obj

        recommendations = {
            "client": convert_datetime_to_string(dict(client)),
            "active_cases": convert_datetime_to_string([dict(c) for c in active_cases]),
            "payment_summary": {
                "total_paid": float(total_paid),
                "total_pending": float(total_pending),
                "total_overdue": float(total_overdue),
                "recent_payments": convert_datetime_to_string([dict(p) for p in client_payments_sorted[:5]]),
            },
        }

        return recommendations

    except Exception as e:
        logger = get_logger("views.main")
        logger.error(
            "Error getting client recommendations for file",
            extra={
                "event": "client_recommendations_error",
                "client_id": client_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return {}


def get_client_recommendations_full(
    client, cases, payments, related_files, recent_accesses, total_paid, total_pending, total_overdue
):
    """Create client recommendations data structure"""

    def convert_datetime_to_string(obj):
        """Convert datetime objects to strings for template compatibility"""
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if hasattr(v, "isoformat"):  # datetime objects
                    result[k] = v.isoformat() if v else None
                elif isinstance(v, (dict, list)):
                    result[k] = convert_datetime_to_string(v)
                else:
                    result[k] = v
            return result
        elif isinstance(obj, list):
            return [convert_datetime_to_string(item) for item in obj]
        elif hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat() if obj else None
        else:
            return obj

    # Sort files by last_accessed (handling None values)
    related_files_sorted = sorted(related_files, key=lambda x: x.get("last_accessed") or datetime.min, reverse=True)

    # Sort payments by payment_date
    payments_sorted = sorted(payments, key=lambda x: x.get("payment_date") or datetime.min, reverse=True)

    recommendations = {
        "client": convert_datetime_to_string(dict(client)),
        "active_cases": convert_datetime_to_string([dict(c) for c in cases if c.get("case_status") == "Open"]),
        "all_cases": convert_datetime_to_string([dict(c) for c in cases]),
        "payment_summary": {
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "total_overdue": float(total_overdue),
            "recent_payments": convert_datetime_to_string([dict(p) for p in payments_sorted[:5]]),
        },
        "file_count": len(related_files),
        "recent_files": convert_datetime_to_string([dict(f) for f in related_files_sorted[:5]]),
        "all_files": convert_datetime_to_string([dict(f) for f in related_files_sorted]),
    }

    return recommendations


def generate_session_id():
    """Generate a unique session ID"""
    return f"session_{uuid.uuid4().hex[:8]}"


@main_bp.before_request
def before_request():
    """Initialize session if needed"""
    if "session_id" not in session:
        session["session_id"] = generate_session_id()


@main_bp.route("/")
def index():
    """Home page redirect to dashboard"""
    return dashboard()


@main_bp.route("/dashboard")
def dashboard():
    """Main dashboard with statistics and recent activity"""
    logger = get_logger("views.main")
    start_time = datetime.utcnow()
    db_manager = get_db_manager()

    try:
        # Get dashboard statistics
        stats = db_manager.get_dashboard_stats()

        # Get recent file accesses
        recent_accesses = db_manager.get_recent_file_accesses(limit=5)

        # Get popular searches
        popular_searches = db_manager.get_popular_searches(limit=5)

        # Get recent searches
        recent_searches = db_manager.get_recent_searches(limit=5)

        # Convert datetime objects to strings for template rendering and add relative time
        for access in recent_accesses:
            if "access_timestamp" in access and access["access_timestamp"]:
                timestamp = access["access_timestamp"]
                access["access_timestamp"] = timestamp.strftime("%Y-%m-%d %H:%M")
                # Add relative time formatting
                now = datetime.now()
                diff = now - timestamp
                total_seconds = int(diff.total_seconds())

                if total_seconds < 60:
                    access["relative_time"] = "Just now"
                elif total_seconds < 3600:
                    access["relative_time"] = f"{total_seconds // 60}m ago"
                elif total_seconds < 86400:
                    access["relative_time"] = f"{total_seconds // 3600}h ago"
                elif total_seconds < 604800:
                    access["relative_time"] = f"{total_seconds // 86400}d ago"
                else:
                    access["relative_time"] = timestamp.strftime("%Y-%m-%d")

        for search in recent_searches:
            if "latest_date" in search and search["latest_date"]:
                search["latest_date"] = search["latest_date"].strftime("%Y-%m-%d %H:%M")

        for search in popular_searches:
            if "last_searched" in search and search["last_searched"]:
                search["last_searched"] = search["last_searched"].strftime("%Y-%m-%d %H:%M")

        # Get recent files for dashboard
        all_files = db_manager.search_files()
        recent_files_sorted = sorted(all_files, key=lambda x: x.get("last_accessed") or datetime.min, reverse=True)[:10]

        # Convert dictionaries to namespace objects for template dot notation
        class FileNamespace:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        recent_files = [FileNamespace(**file) for file in recent_files_sorted]

        # Log successful dashboard load
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_performance_metric("dashboard_load_time", duration)
        log_business_event(
            "dashboard_viewed",
            total_clients=stats.get("total_clients", 0),
            total_cases=stats.get("total_cases", 0),
            total_files=stats.get("total_files", 0),
        )

        return render_template(
            "dashboard.html",
            total_clients=stats.get("total_clients", 0),
            total_cases=stats.get("total_cases", 0),
            total_files=stats.get("total_files", 0),
            active_cases=stats.get("active_cases", 0),
            active_clients=stats.get("active_clients", 0),
            active_files=stats.get("active_files", 0),
            total_paid=float(stats.get("total_paid", 0) or 0),
            total_pending=float(stats.get("total_pending", 0) or 0),
            total_overdue=float(stats.get("total_overdue", 0) or 0),
            recent_files=recent_files,
            recent_accesses=recent_accesses,
            popular_searches=popular_searches,
            recent_searches=recent_searches,
            get_client_name=get_client_name,
            get_case_type=get_case_type,
        )
    except Exception as e:
        logger.error(
            "Dashboard error",
            extra={"event": "dashboard_error", "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        return render_template(
            "dashboard.html",
            total_clients=0,
            total_cases=0,
            total_files=0,
            active_cases=0,
            active_clients=0,
            active_files=0,
            total_paid=0.0,
            total_pending=0.0,
            total_overdue=0.0,
            recent_accesses=[],
            popular_searches=[],
            recent_searches=[],
        )


@main_bp.route("/search")
def search():
    """Search interface and results"""
    logger = get_logger("views.main")
    start_time = datetime.utcnow()
    db_manager = get_db_manager()

    query = request.args.get("q", "").strip()
    case_type_filter = request.args.get("case_type", "")
    file_type_filter = request.args.get("file_type", "")
    confidentiality_filter = request.args.get("confidentiality", "")
    warehouse_filter = request.args.get("warehouse", "")
    storage_status_filter = request.args.get("storage_status", "")

    # Build filters dictionary
    filters = {}
    if case_type_filter:
        filters["case_type"] = case_type_filter
    if file_type_filter:
        filters["file_type"] = file_type_filter
    if confidentiality_filter:
        filters["confidentiality_level"] = confidentiality_filter
    if warehouse_filter:
        filters["warehouse_location"] = warehouse_filter
    if storage_status_filter:
        filters["storage_status"] = storage_status_filter

    results = []
    if query or filters:
        try:
            search_results = db_manager.search_files(query, filters, limit=200)

            # Convert dictionaries to namespace objects for template dot notation
            class FileNamespace:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)

            results = [FileNamespace(**file) for file in search_results]

            # Track search analytics
            if query:
                session_id = session.get("session_id", "anonymous")
                db_manager.add_recent_search(query, session_id)
                db_manager.update_popular_search(query)

                # Log search event
                log_business_event(
                    "search_performed", query=query, results_count=len(results), filters=filters, session_id=session_id
                )

        except Exception as e:
            logger.error(
                "Search error",
                extra={
                    "event": "search_error",
                    "query": query,
                    "filters": filters,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            results = []

    # Get filter options
    try:
        filter_options = db_manager.get_filter_options()
    except Exception as e:
        logger.error(
            "Filter options error",
            extra={"event": "filter_options_error", "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        filter_options = {
            "case_types": [],
            "file_types": [],
            "confidentiality_levels": [],
            "warehouse_locations": [],
            "storage_statuses": [],
        }

    # Create filters object for template
    template_filters = {
        "case_type": case_type_filter,
        "file_type": file_type_filter,
        "confidentiality_level": confidentiality_filter,
        "warehouse_location": warehouse_filter,
        "storage_status": storage_status_filter,
    }

    # Log search performance
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    log_performance_metric("search_duration", duration, query=query, results_count=len(results))

    return render_template(
        "search.html",
        results=results,
        query=query,
        filters=template_filters,
        case_type_filter=case_type_filter,
        file_type_filter=file_type_filter,
        confidentiality_filter=confidentiality_filter,
        warehouse_filter=warehouse_filter,
        storage_status_filter=storage_status_filter,
        case_types=filter_options.get("case_types", []),
        file_types=filter_options.get("file_types", []),
        confidentiality_levels=filter_options.get("confidentiality_levels", []),
        warehouse_locations=filter_options.get("warehouse_locations", []),
        storage_statuses=filter_options.get("storage_statuses", []),
        get_client_name=get_client_name,
        get_case_type=get_case_type,
    )


@main_bp.route("/file/<file_id>")
def file_detail(file_id):
    """Individual file details with related information"""
    logger = get_logger("views.main")
    start_time = datetime.utcnow()
    db_manager = get_db_manager()

    try:
        # Get file details
        file_data = db_manager.get_file_by_id(file_id)

        if not file_data:
            return render_template("404.html"), 404

        # Get client information and recommendations
        recommendations = get_client_recommendations_simple(file_data["client_id"])

        # Get file access history and statistics
        access_history = db_manager.get_file_access_history(file_id)
        access_stats = db_manager.get_file_access_stats(file_id)

        # Convert datetime objects in access_stats for template compatibility
        if access_stats.get("last_accessed") and hasattr(access_stats["last_accessed"], "get"):
            # It's a database row object, convert datetime fields
            last_accessed = dict(access_stats["last_accessed"])
            for key, value in last_accessed.items():
                if hasattr(value, "isoformat"):
                    last_accessed[key] = value.isoformat() if value else None
            access_stats["last_accessed"] = last_accessed

        # Get comments for this file
        comments = db_manager.get_comments_by_file(file_id)

        # Record file access (simulate different users)
        user_agent = request.headers.get("User-Agent", "Unknown")
        ip_address = request.remote_addr or "127.0.0.1"

        # Simulate different users based on session/time
        demo_users = [
            ("John Smith", "Partner"),
            ("Sarah Johnson", "Associate"),
            ("Michael Brown", "Paralegal"),
            ("Current User", "Demo User"),
        ]
        user_hash = int(hashlib.md5(f"{ip_address}{user_agent}".encode()).hexdigest()[:8], 16)
        current_user_name, current_user_role = demo_users[user_hash % len(demo_users)]

        access_data = {
            "access_id": f"ACC{random.randint(10000, 99999)}",
            "file_id": file_id,
            "user_name": current_user_name,
            "user_role": current_user_role,
            "access_timestamp": datetime.now().isoformat(),
            "access_type": "view",
            "ip_address": ip_address,
            "user_agent": user_agent,
            "session_duration": None,
        }

        try:
            db_manager.insert_file_access(access_data)
            db_manager.update_file_access_time(file_id)

            # Log file access event
            log_business_event(
                "file_accessed",
                entity_type="file",
                entity_id=file_id,
                user_name=current_user_name,
                user_role=current_user_role,
                access_type="view",
            )
        except Exception as e:
            logger.error(
                "Error recording file access",
                extra={
                    "event": "file_access_record_error",
                    "file_id": file_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        # Convert datetime objects in access_history for template compatibility
        for access in access_history:
            for key, value in access.items():
                if hasattr(value, "isoformat"):
                    access[key] = value.isoformat() if value else None

        # Sort access history by timestamp (most recent first)
        access_history.sort(key=lambda x: x["access_timestamp"], reverse=True)

        # Log file detail view performance
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_performance_metric("file_detail_load_time", duration, file_id=file_id)

        return render_template(
            "file_detail.html",
            file=file_data,
            recommendations=recommendations,
            access_history=access_history,
            access_stats=access_stats,
            comments=comments,
            get_client_name=get_client_name,
            get_case_type=get_case_type,
        )
    except Exception as e:
        logger.error(
            "File detail error",
            extra={"event": "file_detail_error", "file_id": file_id, "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        return render_template("500.html"), 500


@main_bp.route("/client/<client_id>")
def client_detail(client_id):
    """Client profile with recommendations and related information"""
    logger = get_logger("views.main")
    start_time = datetime.utcnow()
    db_manager = get_db_manager()

    try:
        # Get client information
        client = db_manager.get_client_by_id(client_id)
        if not client:
            return render_template("404.html"), 404

        # Get client's cases
        cases = db_manager.get_cases_by_client(client_id)

        # Get client's payments
        payments = db_manager.get_payments_by_client(client_id)

        # Calculate payment summary
        total_paid = sum(float(p["amount"] or 0) for p in payments if p["status"] == "Paid")
        total_pending = sum(float(p["amount"] or 0) for p in payments if p["status"] == "Pending")
        total_overdue = sum(float(p["amount"] or 0) for p in payments if p["status"] == "Overdue")

        # Get related files
        all_files = db_manager.search_files()
        related_files = [f for f in all_files if f["client_id"] == client_id]

        # Get recent file accesses for this client's files
        client_file_ids = [f["file_id"] for f in related_files]
        all_accesses = db_manager.get_recent_file_accesses(limit=50)
        recent_accesses = [a for a in all_accesses if a["file_id"] in client_file_ids][:5]

        # Create recommendations object
        recommendations = get_client_recommendations_full(
            client, cases, payments, related_files, recent_accesses, total_paid, total_pending, total_overdue
        )

        # Log client detail view
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_performance_metric("client_detail_load_time", duration, client_id=client_id)
        log_business_event(
            "client_viewed",
            entity_type="client",
            entity_id=client_id,
            cases_count=len(cases),
            files_count=len(related_files),
        )

        return render_template("client_detail.html", recommendations=recommendations)
    except Exception as e:
        logger.error(
            "Client detail error",
            extra={
                "event": "client_detail_error",
                "client_id": client_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return render_template("500.html"), 500


@main_bp.route("/debug-search")
def debug_search():
    """Debug page for testing search dropdown functionality"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Search Debug</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h2>🔍 Search Dropdown Debug</h2>
        <div class="position-relative mb-3">
            <input type="text" class="form-control" id="q" placeholder="Type 'jen' to test..." autocomplete="off">
            <div id="search-suggestions" class="position-absolute w-100 bg-white border rounded shadow-sm d-none" style="z-index: 1000; top: 100%;">
                <div class="p-3">Loading...</div>
            </div>
        </div>

        <div class="mb-3">
            <button onclick="testAPI()" class="btn btn-primary">Test API</button>
            <button onclick="testDropdown()" class="btn btn-secondary">Test Dropdown</button>
            <button onclick="showConsoleLog()" class="btn btn-info">Show Log</button>
        </div>

        <div id="debug-output"></div>
        <div id="console-log"></div>
    </div>

    <script>
        const searchInput = document.getElementById('q');
        const suggestionsContainer = document.getElementById('search-suggestions');
        let logs = [];

        function log(message) {
            console.log(message);
            logs.push(new Date().toLocaleTimeString() + ': ' + message);
        }

        log('Elements found - Input: ' + !!searchInput + ', Container: ' + !!suggestionsContainer);

        searchInput.addEventListener('input', function(e) {
            const query = e.target.value;
            log('Input: ' + query);
            if (query.length >= 2) {
                showSuggestions(query);
            } else {
                hideSuggestions();
            }
        });

        async function showSuggestions(query) {
            log('Showing suggestions for: ' + query);
            try {
                const response = await fetch('/api/intelligent-suggestions?q=' + encodeURIComponent(query) + '&limit=8');
                const data = await response.json();
                log('Got ' + (data.suggestions ? data.suggestions.length : 0) + ' suggestions');

                if (data.suggestions && data.suggestions.length > 0) {
                    let html = data.suggestions.map(s =>
                        '<div class="px-3 py-2 border-bottom" style="cursor:pointer;"><i class="fas fa-file me-2"></i>' + s.text + '</div>'
                    ).join('');
                    suggestionsContainer.innerHTML = html;
                    suggestionsContainer.classList.remove('d-none');
                    log('Dropdown shown');
                } else {
                    suggestionsContainer.innerHTML = '<div class="px-3 py-2 text-muted">No suggestions</div>';
                    suggestionsContainer.classList.remove('d-none');
                }
            } catch (error) {
                log('Error: ' + error.message);
            }
        }

        function hideSuggestions() {
            suggestionsContainer.classList.add('d-none');
        }

        async function testAPI() {
            const response = await fetch('/api/intelligent-suggestions?q=jen&limit=8');
            const data = await response.json();
            document.getElementById('debug-output').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }

        function testDropdown() {
            suggestionsContainer.innerHTML = '<div class="px-3 py-2 bg-success text-white">✅ Dropdown is working!</div>';
            suggestionsContainer.classList.remove('d-none');
        }

        function showConsoleLog() {
            document.getElementById('console-log').innerHTML = '<h5>Log:</h5><pre>' + logs.join('\\n') + '</pre>';
        }
    </script>
</body>
</html>
    """


@main_bp.route("/health")
def health_check():
    """Health check endpoint"""
    db_manager = get_db_manager()

    try:
        # Test database connection
        stats = db_manager.get_dashboard_stats()
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }, 500
