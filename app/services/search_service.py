"""
Search service for handling search-related business logic.

This module contains functions for unified search, suggestions, and search analytics.
"""

from typing import Any, Dict, List, Optional

from app import get_db_manager


def unified_search_data(
    query: str, filters: Optional[Dict[str, Any]] = None, include_private_comments: bool = False
) -> Dict[str, Any]:
    """
    Unified search across all data types: files, clients, cases, payments, access history, and comments
    Returns categorized results with relevance scoring
    """
    db_manager = get_db_manager()

    if not query and not filters:
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

    query_lower = query.lower() if query else ""
    results: Dict[str, List[Any]] = {
        "files": [],
        "clients": [],
        "cases": [],
        "payments": [],
        "access_history": [],
        "comments": [],
        "total_results": 0,
        "query": query,
    }

    try:
        # Search Files (optimized) - also search for individual words
        if query:
            files = db_manager.search_files(query, filters or {}, limit=20)

            # If no results and query has multiple words, try searching for individual words
            if not files and " " in query:
                query_words = query.split()
                for word in query_words:
                    if len(word) > 2:  # Skip very short words
                        word_files = db_manager.search_files(word, filters or {}, limit=20)
                        files.extend(word_files)

                # Remove duplicates based on file_id
                seen_ids = set()
                unique_files = []
                for file in files:
                    if file["file_id"] not in seen_ids:
                        seen_ids.add(file["file_id"])
                        unique_files.append(file)
                files = unique_files
            for file in files:
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

                if score > 0:
                    file_result = dict(file)
                    file_result["client_name"] = client_name
                    file_result["case_type"] = case_type
                    file_result["relevance_score"] = score
                    file_result["match_details"] = matches
                    # Convert datetime objects
                    for key, value in file_result.items():
                        if hasattr(value, "isoformat"):
                            file_result[key] = value.isoformat() if value else None
                    results["files"].append(file_result)

        # Search Clients (optimized)
        if query:
            search_clients = db_manager.search_clients(query, limit=20)
            for client in search_clients:
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

                if score > 0 or matches:  # Include if DB found a match
                    client_result = dict(client)
                    client_result["relevance_score"] = score
                    client_result["match_details"] = matches
                    # Convert datetime objects
                    for key, value in client_result.items():
                        if hasattr(value, "isoformat"):
                            client_result[key] = value.isoformat() if value else None
                    results["clients"].append(client_result)

        # Search Cases (optimized)
        if query:
            search_cases = db_manager.search_cases(query, limit=20)
            for case in search_cases:
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

                if score > 0:
                    case_result = dict(case)
                    case_result["client_name"] = client_name
                    case_result["relevance_score"] = score
                    case_result["match_details"] = matches
                    # Convert datetime objects
                    for key, value in case_result.items():
                        if hasattr(value, "isoformat"):
                            case_result[key] = value.isoformat() if value else None
                    results["cases"].append(case_result)

        # Search Payments (optimized)
        if query:
            search_payments = db_manager.search_payments(query, limit=20)
            for payment in search_payments:
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

                if score > 0:
                    payment_result = dict(payment)
                    payment_result["client_name"] = client_name
                    payment_result["relevance_score"] = score
                    payment_result["match_details"] = matches
                    # Convert datetime objects
                    for key, value in payment_result.items():
                        if hasattr(value, "isoformat"):
                            payment_result[key] = value.isoformat() if value else None
                    results["payments"].append(payment_result)

        # Search Access History
        if query:
            recent_accesses = db_manager.get_recent_file_accesses(100)  # Get more for searching
            for access in recent_accesses:
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

                if score > 0:
                    access_result = dict(access)
                    access_result["relevance_score"] = score
                    access_result["match_details"] = matches
                    # Convert datetime objects
                    for key, value in access_result.items():
                        if hasattr(value, "isoformat"):
                            access_result[key] = value.isoformat() if value else None
                    results["access_history"].append(access_result)

        # Search Comments (if available)
        # Note: We would need to implement get_all_comments in database.py
        results["comments"] = []  # Placeholder for now

        # Sort results by relevance score
        for category in ["files", "clients", "cases", "payments", "access_history"]:
            results[category] = sorted(results[category], key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Calculate total results
        results["total_results"] = sum(
            len(results[cat]) for cat in ["files", "clients", "cases", "payments", "access_history", "comments"]
        )

        return results

    except Exception as e:
        print(f"Unified search error: {e}")
        return {
            "files": [],
            "clients": [],
            "cases": [],
            "payments": [],
            "access_history": [],
            "comments": [],
            "total_results": 0,
            "query": query,
            "error": str(e),
        }


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
    except Exception as e:
        return {"suggestions": []}
