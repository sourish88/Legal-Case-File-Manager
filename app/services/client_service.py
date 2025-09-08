"""
Client service for handling client-related business logic.

This module contains functions for client recommendations and related data processing.
"""

from datetime import datetime
from typing import Any, Dict, List

from app import get_db_manager


def get_client_recommendations_data(
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


def get_client_recommendations_for_file(client_id: str) -> Dict[str, Any]:
    """Get client recommendations for file detail page (optimized version)"""
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
        print(f"Error getting client recommendations for file: {e}")
        return {}
