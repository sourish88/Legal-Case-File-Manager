"""
Search service for handling search-related business logic.

This module contains functions for unified search, suggestions, and search analytics.
"""

from typing import Any, Dict, List, Optional, Tuple, cast

from app import get_db_manager


def _convert_datetime_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert datetime objects to ISO format strings in a dictionary."""
    result = dict(data)
    for key, value in result.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat() if value else None
    return result


def _deduplicate_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate files based on file_id."""
    seen_ids = set()
    unique_files = []
    for file in files:
        if file["file_id"] not in seen_ids:
            seen_ids.add(file["file_id"])
            unique_files.append(file)
    return unique_files


def _search_files_with_fallback(db_manager: Any, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search files with fallback to individual words if no results."""
    files = cast(List[Dict[str, Any]], db_manager.search_files(query, filters, limit=20))

    # If no results and query has multiple words, try searching for individual words
    if not files and " " in query:
        query_words = query.split()
        for word in query_words:
            if len(word) > 2:  # Skip very short words
                word_files = cast(List[Dict[str, Any]], db_manager.search_files(word, filters, limit=20))
                files.extend(word_files)
        files = _deduplicate_files(files)

    return files


def _score_file_match(file: Dict[str, Any], query_lower: str) -> Tuple[int, List[str]]:
    """Calculate relevance score and match details for a file."""
    score = 0
    matches = []

    # Check various file fields with different weights
    if query_lower in file["reference_number"].lower():
        score += 10
        matches.append(f"Reference: {file['reference_number']}")
    if query_lower in (file.get("file_description") or "").lower():
        score += 8
        matches.append(f"Description: {(file.get('file_description') or '')[:100]}...")
    if query_lower in (file.get("document_category") or "").lower():
        score += 6
        matches.append(f"Category: {file.get('document_category')}")
    if query_lower in (file.get("file_type") or "").lower():
        score += 6
        matches.append(f"Type: {file.get('file_type')}")
    if file.get("keywords") and any(query_lower in (keyword or "").lower() for keyword in file["keywords"]):
        score += 7
        matching_keywords = [kw for kw in file["keywords"] if query_lower in (kw or "").lower()]
        matches.append(f"Keywords: {', '.join(matching_keywords)}")

    # Client name should already be included from optimized search_files
    client_name = f"{file.get('first_name', '')} {file.get('last_name', '')}".strip()
    if client_name and query_lower in client_name.lower():
        score = max(score, file.get("relevance_score", 0))
        matches.append(f"Client: {client_name}")

    # Case type should already be included from optimized search_files
    case_type = file.get("case_type", "")
    if case_type and query_lower in case_type.lower():
        score = max(score, file.get("relevance_score", 0))
        matches.append(f"Case Type: {case_type}")

    return score, matches


def _process_file_results(files: List[Dict[str, Any]], query_lower: str) -> List[Dict[str, Any]]:
    """Process file search results with scoring and match details."""
    results = []
    for file in files:
        score, matches = _score_file_match(file, query_lower)
        if score > 0:
            file_result = dict(file)
            file_result["client_name"] = f"{file.get('first_name', '')} {file.get('last_name', '')}".strip()
            file_result["case_type"] = file.get("case_type", "")
            file_result["relevance_score"] = score
            file_result["match_details"] = matches
            file_result = _convert_datetime_objects(file_result)
            results.append(file_result)
    return results


def _score_client_match(client: Dict[str, Any], query_lower: str) -> Tuple[int, List[str]]:
    """Calculate relevance score and match details for a client."""
    score = int(client.get("relevance_score", 0) * 10)  # Convert DB relevance to our scale
    matches = []

    # Add specific match details based on what was found
    full_name = f"{client['first_name']} {client['last_name']}"
    if query_lower in full_name.lower():
        matches.append(f"Name: {full_name}")
    if query_lower in client["email"].lower():
        matches.append(f"Email: {client['email']}")
    if query_lower in (client.get("phone") or "").lower():
        matches.append(f"Phone: {client.get('phone')}")
    if query_lower in (client.get("address") or "").lower():
        matches.append(f"Address: {(client.get('address') or '')[:100]}...")
    if query_lower in (client.get("client_type") or "").lower():
        matches.append(f"Type: {client.get('client_type')}")
    if query_lower in (client.get("status") or "").lower():
        matches.append(f"Status: {client.get('status')}")

    return score, matches


def _process_client_results(clients: List[Dict[str, Any]], query_lower: str) -> List[Dict[str, Any]]:
    """Process client search results with scoring and match details."""
    results = []
    for client in clients:
        score, matches = _score_client_match(client, query_lower)
        if score > 0 or matches:  # Include if DB found a match
            client_result = dict(client)
            client_result["relevance_score"] = score
            client_result["match_details"] = matches
            client_result = _convert_datetime_objects(client_result)
            results.append(client_result)
    return results


def _score_case_match(case: Dict[str, Any], query_lower: str) -> Tuple[int, List[str]]:
    """Calculate relevance score and match details for a case."""
    score = 0
    matches = []

    if query_lower in case["reference_number"].lower():
        score += 10
        matches.append(f"Reference: {case['reference_number']}")
    if query_lower in (case.get("case_type") or "").lower():
        score += 8
        matches.append(f"Type: {case.get('case_type')}")
    if query_lower in (case.get("description") or "").lower():
        score += 7
        matches.append(f"Description: {(case.get('description') or '')[:100]}...")
    if query_lower in (case.get("assigned_lawyer") or "").lower():
        score += 6
        matches.append(f"Lawyer: {case.get('assigned_lawyer')}")
    if query_lower in (case.get("case_status") or "").lower():
        score += 5
        matches.append(f"Status: {case.get('case_status')}")

    # Client name should already be included from optimized search
    client_name = case.get("client_name", "")
    if client_name and query_lower in client_name.lower():
        score = max(score, case.get("relevance_score", 0))
        matches.append(f"Client: {client_name}")

    return score, matches


def _process_case_results(cases: List[Dict[str, Any]], query_lower: str) -> List[Dict[str, Any]]:
    """Process case search results with scoring and match details."""
    results = []
    for case in cases:
        score, matches = _score_case_match(case, query_lower)
        if score > 0:
            case_result = dict(case)
            case_result["client_name"] = case.get("client_name", "")
            case_result["relevance_score"] = score
            case_result["match_details"] = matches
            case_result = _convert_datetime_objects(case_result)
            results.append(case_result)
    return results


def _score_payment_match(payment: Dict[str, Any], query_lower: str) -> Tuple[int, List[str]]:
    """Calculate relevance score and match details for a payment."""
    score = 0
    matches = []

    if query_lower in (payment.get("description") or "").lower():
        score += 8
        matches.append(f"Description: {payment.get('description')}")
    if query_lower in (payment.get("payment_method") or "").lower():
        score += 6
        matches.append(f"Method: {payment.get('payment_method')}")
    if query_lower in (payment.get("status") or "").lower():
        score += 5
        matches.append(f"Status: {payment.get('status')}")

    # Check amount (convert to string for search)
    amount_str = str(payment.get("amount", ""))
    if query_lower in amount_str:
        score += 7
        matches.append(f"Amount: ${payment.get('amount')}")

    # Client name should already be included from optimized search
    client_name = payment.get("client_name", "")
    if client_name and query_lower in client_name.lower():
        score = max(score, payment.get("relevance_score", 0))
        matches.append(f"Client: {client_name}")

    return score, matches


def _process_payment_results(payments: List[Dict[str, Any]], query_lower: str) -> List[Dict[str, Any]]:
    """Process payment search results with scoring and match details."""
    results = []
    for payment in payments:
        score, matches = _score_payment_match(payment, query_lower)
        if score > 0:
            payment_result = dict(payment)
            payment_result["client_name"] = payment.get("client_name", "")
            payment_result["relevance_score"] = score
            payment_result["match_details"] = matches
            payment_result = _convert_datetime_objects(payment_result)
            results.append(payment_result)
    return results


def _score_access_match(access: Dict[str, Any], query_lower: str) -> Tuple[int, List[str]]:
    """Calculate relevance score and match details for an access record."""
    score = 0
    matches = []

    if query_lower in (access.get("user_name") or "").lower():
        score += 8
        matches.append(f"User: {access.get('user_name')}")
    if query_lower in (access.get("access_type") or "").lower():
        score += 6
        matches.append(f"Access Type: {access.get('access_type')}")
    if query_lower in (access.get("user_role") or "").lower():
        score += 5
        matches.append(f"Role: {access.get('user_role')}")

    # Check if file reference matches
    if access.get("reference_number") and query_lower in access["reference_number"].lower():
        score += 9
        matches.append(f"File: {access['reference_number']}")

    return score, matches


def _process_access_results(accesses: List[Dict[str, Any]], query_lower: str) -> List[Dict[str, Any]]:
    """Process access history search results with scoring and match details."""
    results = []
    for access in accesses:
        score, matches = _score_access_match(access, query_lower)
        if score > 0:
            access_result = dict(access)
            access_result["relevance_score"] = score
            access_result["match_details"] = matches
            access_result = _convert_datetime_objects(access_result)
            results.append(access_result)
    return results


def _get_empty_results(query: str) -> Dict[str, Any]:
    """Return empty results structure."""
    return {
        "files": [],
        "clients": [],
        "cases": [],
        "payments": [],
        "access_history": [],
        "comments": [],
        "total_results": 0,
        "query": query,
    }


def unified_search_data(
    query: str, filters: Optional[Dict[str, Any]] = None, include_private_comments: bool = False
) -> Dict[str, Any]:
    """
    Unified search across all data types: files, clients, cases, payments, access history, and comments
    Returns categorized results with relevance scoring
    """
    db_manager = get_db_manager()

    if not query and not filters:
        return _get_empty_results(query)

    query_lower = query.lower() if query else ""
    results = _get_empty_results(query)

    try:
        # Search each entity type if query is provided
        if query:
            # Search Files with fallback
            files = _search_files_with_fallback(db_manager, query, filters or {})
            results["files"] = _process_file_results(files, query_lower)

            # Search Clients
            clients = db_manager.search_clients(query, limit=20)
            results["clients"] = _process_client_results(clients, query_lower)

            # Search Cases
            cases = db_manager.search_cases(query, limit=20)
            results["cases"] = _process_case_results(cases, query_lower)

            # Search Payments
            payments = db_manager.search_payments(query, limit=20)
            results["payments"] = _process_payment_results(payments, query_lower)

            # Search Access History
            accesses = db_manager.get_recent_file_accesses(100)  # Get more for searching
            results["access_history"] = _process_access_results(accesses, query_lower)

        # Search Comments (placeholder for now)
        results["comments"] = []

        # Sort all results by relevance score
        for category in ["files", "clients", "cases", "payments", "access_history"]:
            results[category] = sorted(results[category], key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Calculate total results
        results["total_results"] = sum(
            len(results[cat]) for cat in ["files", "clients", "cases", "payments", "access_history", "comments"]
        )

        return results

    except Exception as e:
        print(f"Unified search error: {e}")
        error_result = _get_empty_results(query)
        error_result["error"] = str(e)
        return error_result


def api_intelligent_suggestions_data(query: str, limit: int = 8) -> Dict[str, Any]:
    """Helper function to get intelligent suggestions data"""
    db_manager = get_db_manager()

    try:
        if len(query) < 2:
            return {"suggestions": []}

        # Get suggestions from various sources
        suggestions = []

        # Search files for matching terms (optimized)
        files = db_manager.search_files(query, {}, limit=limit // 2)
        for file in files:
            suggestions.append(
                {
                    "type": "file",
                    "text": file["reference_number"],
                    "description": file["file_description"][:100] + "..."
                    if len(file.get("file_description", "")) > 100
                    else file.get("file_description", ""),
                    "url": f"/file/{file['file_id']}",
                }
            )

        # Search clients (optimized)
        matching_clients = db_manager.search_clients(query, limit=limit // 4)
        for client in matching_clients:
            suggestions.append(
                {
                    "type": "client",
                    "text": f"{client['first_name']} {client['last_name']}",
                    "description": f"{client['client_type']} - {client['email']}",
                    "url": f"/client/{client['client_id']}",
                }
            )

        return {"suggestions": suggestions[:limit]}
    except Exception:
        return {"suggestions": []}
