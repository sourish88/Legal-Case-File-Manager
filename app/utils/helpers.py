"""
Helper functions for the Legal Case File Manager.

This module contains utility functions used across the application.
"""


def get_db_manager():
    """Get the database manager from the current app context"""
    from app import get_db_manager as _get_db_manager

    return _get_db_manager()


def get_client_name(client_id: str) -> str:
    """Get client name by ID"""
    db_manager = get_db_manager()

    try:
        client = db_manager.get_client_by_id(client_id)
        if client:
            return f"{client['first_name']} {client['last_name']}"
        return "Unknown Client"
    except Exception:
        return "Unknown Client"


def get_case_type(case_id: str) -> str:
    """Get case type by case ID"""
    db_manager = get_db_manager()

    try:
        case = db_manager.get_case_by_id(case_id)
        if case:
            return case["case_type"]
        return "Unknown Case Type"
    except Exception:
        return "Unknown Case Type"


def format_currency(amount: float) -> str:
    """Format currency amount for display"""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"


def format_file_size(size_category: str) -> str:
    """Format file size category for display"""
    size_mapping = {
        "Small": "< 100 pages",
        "Medium": "100-500 pages",
        "Large": "500-1000 pages",
        "Extra Large": "> 1000 pages",
    }
    return size_mapping.get(size_category, size_category)


def get_priority_badge_class(priority: str) -> str:
    """Get Bootstrap badge class for priority level"""
    priority_classes = {
        "Low": "badge-secondary",
        "Medium": "badge-primary",
        "High": "badge-warning",
        "Urgent": "badge-danger",
    }
    return priority_classes.get(priority, "badge-secondary")


def get_status_badge_class(status: str) -> str:
    """Get Bootstrap badge class for status"""
    status_classes = {
        "Active": "badge-success",
        "Inactive": "badge-secondary",
        "Open": "badge-success",
        "Closed": "badge-secondary",
        "On Hold": "badge-warning",
        "Under Review": "badge-info",
        "Paid": "badge-success",
        "Pending": "badge-warning",
        "Overdue": "badge-danger",
        "Cancelled": "badge-secondary",
    }
    return status_classes.get(status, "badge-secondary")


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def safe_get(dictionary: dict, key: str, default=None):
    """Safely get a value from dictionary with default"""
    return dictionary.get(key, default) if dictionary else default
