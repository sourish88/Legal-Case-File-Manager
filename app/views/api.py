"""
API routes for the Legal Case File Manager.

This module contains all JSON API endpoints for the application.
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
from typing import Dict, Any

from app.services.search_service import unified_search_data, api_intelligent_suggestions_data

api_bp = Blueprint('api', __name__)


def get_db_manager():
    """Get the database manager from the current app context"""
    from app import get_db_manager as _get_db_manager
    return _get_db_manager()


@api_bp.route('/search')
def search():
    """JSON API for search functionality"""
    db_manager = get_db_manager()
    
    query = request.args.get('q', '').strip()
    case_type_filter = request.args.get('case_type', '')
    file_type_filter = request.args.get('file_type', '')
    confidentiality_filter = request.args.get('confidentiality', '')
    warehouse_filter = request.args.get('warehouse', '')
    storage_status_filter = request.args.get('storage_status', '')
    
    # Build filters dictionary
    filters = {}
    if case_type_filter:
        filters['case_type'] = case_type_filter
    if file_type_filter:
        filters['file_type'] = file_type_filter
    if confidentiality_filter:
        filters['confidentiality_level'] = confidentiality_filter
    if warehouse_filter:
        filters['warehouse_location'] = warehouse_filter
    if storage_status_filter:
        filters['storage_status'] = storage_status_filter
    
    try:
        results = db_manager.search_files(query, filters, limit=100)
        
        # Convert datetime objects to strings for JSON serialization
        for result in results:
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif hasattr(value, 'isoformat'):  # Handle date objects
                    result[key] = value.isoformat()
        
        # Track search analytics
        if query:
            session_id = session.get('session_id', 'anonymous')
            db_manager.add_recent_search(query, session_id)
            db_manager.update_popular_search(query)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        print(f"API search error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'results': [],
            'count': 0
        }), 500


@api_bp.route('/stats')
def stats():
    """JSON API for dashboard statistics"""
    db_manager = get_db_manager()
    
    try:
        stats = db_manager.get_dashboard_stats()
        
        # Convert Decimal to float for JSON serialization
        for key, value in stats.items():
            if hasattr(value, '__float__'):
                stats[key] = float(value)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        print(f"API stats error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {}
        }), 500


@api_bp.route('/filters')
def filters():
    """JSON API for filter options"""
    db_manager = get_db_manager()
    
    try:
        filter_options = db_manager.get_filter_options()
        return jsonify({
            'success': True,
            'filters': filter_options
        })
    except Exception as e:
        print(f"API filters error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'filters': {}
        }), 500


@api_bp.route('/unified-search')
def unified_search():
    """API endpoint for unified search across all data types"""
    query = request.args.get('q', '')
    include_private = request.args.get('include_private', 'false').lower() == 'true'
    limit_per_category = int(request.args.get('limit', 10))  # Limit results per category
    
    try:
        # Get unified search results
        results = unified_search_data(query, {}, include_private)
        
        # Limit results per category to prevent overwhelming the UI
        for category in ['files', 'clients', 'cases', 'payments', 'access_history', 'comments']:
            if len(results[category]) > limit_per_category:
                results[category] = results[category][:limit_per_category]
                results[f'{category}_truncated'] = True
            else:
                results[f'{category}_truncated'] = False
        
        # Add category counts for summary
        results['category_counts'] = {
            'files': len(results['files']),
            'clients': len(results['clients']),
            'cases': len(results['cases']),
            'payments': len(results['payments']),
            'access_history': len(results['access_history']),
            'comments': len(results['comments'])
        }
        
        return jsonify(results)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'files': [],
            'clients': [],
            'cases': [],
            'payments': [],
            'access_history': [],
            'comments': [],
            'total_results': 0,
            'query': query
        }), 500


@api_bp.route('/suggestions')
def suggestions():
    """API endpoint for intelligent search suggestions (backward compatibility)"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))
    
    try:
        # Get intelligent suggestions
        intelligent_suggestions = api_intelligent_suggestions_data(query, limit)
        
        # Format for backward compatibility - extract just the text
        simple_suggestions = [s['text'] for s in intelligent_suggestions.get('suggestions', [])]
        
        return jsonify({
            'suggestions': simple_suggestions,
            'intelligent': intelligent_suggestions,
            'query': query
        })
    except Exception as e:
        return jsonify({
            'suggestions': [],
            'intelligent': {'suggestions': []},
            'query': query
        })


@api_bp.route('/intelligent-suggestions')
def intelligent_suggestions():
    """API endpoint for intelligent search suggestions"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 8))
    
    try:
        suggestions_data = api_intelligent_suggestions_data(query, limit)
        return jsonify(suggestions_data)
    except Exception as e:
        return jsonify({'suggestions': []})


@api_bp.route('/recent-activity')
def recent_activity():
    """API endpoint to get recent file access activity"""
    db_manager = get_db_manager()
    limit = int(request.args.get('limit', 20))
    
    try:
        recent_accesses = db_manager.get_recent_file_accesses(limit)
        
        # Convert datetime objects to strings
        formatted_accesses = []
        for access in recent_accesses:
            access_dict = dict(access)
            for key, value in access_dict.items():
                if hasattr(value, 'isoformat'):
                    access_dict[key] = value.isoformat() if value else None
            formatted_accesses.append(access_dict)
        
        return jsonify({
            'recent_accesses': formatted_accesses,
            'count': len(recent_accesses)
        })
    except Exception as e:
        return jsonify({
            'recent_accesses': [],
            'count': 0,
            'error': str(e)
        })


@api_bp.route('/filter-options')
def filter_options():
    """API endpoint to get available filter options"""
    db_manager = get_db_manager()
    
    try:
        filter_options = db_manager.get_filter_options()
        return jsonify(filter_options)
    except Exception as e:
        return jsonify({
            'case_types': [],
            'file_types': [],
            'confidentiality_levels': [],
            'warehouse_locations': [],
            'storage_statuses': [],
            'error': str(e)
        })


@api_bp.route('/access-history/<file_id>')
def access_history(file_id):
    """API endpoint to get access history for a specific file"""
    db_manager = get_db_manager()
    
    try:
        access_history = db_manager.get_file_access_history(file_id)
        
        # Convert datetime objects to strings
        formatted_history = []
        for access in access_history:
            access_dict = dict(access)
            for key, value in access_dict.items():
                if hasattr(value, 'isoformat'):
                    access_dict[key] = value.isoformat() if value else None
            formatted_history.append(access_dict)
        
        return jsonify({
            'access_history': formatted_history,
            'count': len(access_history)
        })
    except Exception as e:
        return jsonify({
            'access_history': [],
            'count': 0,
            'error': str(e)
        })
