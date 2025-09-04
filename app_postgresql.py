from flask import Flask, render_template, request, jsonify, url_for, session
from datetime import datetime, timedelta
import json
import random
import uuid
from typing import List, Dict, Any, Optional
import re
import os
from config import Config
from database import DatabaseConnection, LegalFileManagerDB

# Import the migration blueprint if it exists
try:
    from ai_migration import migration_bp
    MIGRATION_AVAILABLE = True
except ImportError:
    MIGRATION_AVAILABLE = False
    print("Migration blueprint not available - continuing without it")

app = Flask(__name__)

# Load configuration
try:
    Config.validate_config()
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please check your environment variables or .env file")
    exit(1)

# Register migration blueprint if available
if MIGRATION_AVAILABLE:
    app.register_blueprint(migration_bp)

# Initialize database connection
try:
    db_connection = DatabaseConnection(**Config.get_database_config())
    db_manager = LegalFileManagerDB(db_connection)
    print("Database connection established successfully")
except Exception as e:
    print(f"Failed to connect to database: {e}")
    print("Please ensure PostgreSQL is running and credentials are correct")
    exit(1)

def generate_session_id():
    """Generate a unique session ID"""
    return f"session_{uuid.uuid4().hex[:8]}"

@app.before_request
def before_request():
    """Initialize session if needed"""
    if 'session_id' not in session:
        session['session_id'] = generate_session_id()

@app.route('/')
def index():
    return dashboard()

def dashboard():
    """Main dashboard with statistics and recent activity"""
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
            if 'access_timestamp' in access and access['access_timestamp']:
                timestamp = access['access_timestamp']
                access['access_timestamp'] = timestamp.strftime('%Y-%m-%d %H:%M')
                # Add relative time formatting
                now = datetime.now()
                diff = now - timestamp
                total_seconds = int(diff.total_seconds())
                
                if total_seconds < 60:
                    access['relative_time'] = 'Just now'
                elif total_seconds < 3600:
                    access['relative_time'] = f"{total_seconds // 60}m ago"
                elif total_seconds < 86400:
                    access['relative_time'] = f"{total_seconds // 3600}h ago"
                elif total_seconds < 604800:
                    access['relative_time'] = f"{total_seconds // 86400}d ago"
                else:
                    access['relative_time'] = timestamp.strftime('%Y-%m-%d')
        
        for search in recent_searches:
            if 'latest_date' in search and search['latest_date']:
                search['latest_date'] = search['latest_date'].strftime('%Y-%m-%d %H:%M')
        
        for search in popular_searches:
            if 'last_searched' in search and search['last_searched']:
                search['last_searched'] = search['last_searched'].strftime('%Y-%m-%d %H:%M')
        
        # Get recent files for dashboard (matching original app)
        all_files = db_manager.search_files()
        recent_files_sorted = sorted(all_files, 
                                   key=lambda x: x.get('last_accessed') or datetime.min, 
                                   reverse=True)[:10]
        
        # Convert dictionaries to namespace objects for template dot notation
        class FileNamespace:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        recent_files = [FileNamespace(**file) for file in recent_files_sorted]

        return render_template('dashboard.html',
                             total_clients=stats.get('total_clients', 0),
                             total_cases=stats.get('total_cases', 0),
                             total_files=stats.get('total_files', 0),
                             active_cases=stats.get('active_cases', 0),
                             active_clients=stats.get('active_clients', 0),
                             active_files=stats.get('active_files', 0),
                             total_paid=float(stats.get('total_paid', 0) or 0),
                             total_pending=float(stats.get('total_pending', 0) or 0),
                             total_overdue=float(stats.get('total_overdue', 0) or 0),
                             recent_files=recent_files,
                             recent_accesses=recent_accesses,
                             popular_searches=popular_searches,
                             recent_searches=recent_searches,
                             get_client_name=get_client_name,
                             get_case_type=get_case_type)
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('dashboard.html',
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
                             recent_searches=[])

@app.route('/search')
def search():
    """Search interface and results"""
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
    
    results = []
    if query or filters:
        try:
            search_results = db_manager.search_files(query, filters)
            
            # Convert dictionaries to namespace objects for template dot notation
            class FileNamespace:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            
            results = [FileNamespace(**file) for file in search_results]
            
            # Track search analytics
            if query:
                session_id = session.get('session_id', 'anonymous')
                db_manager.add_recent_search(query, session_id)
                db_manager.update_popular_search(query)
        except Exception as e:
            print(f"Search error: {e}")
            results = []
    
    # Get filter options
    try:
        filter_options = db_manager.get_filter_options()
    except Exception as e:
        print(f"Filter options error: {e}")
        filter_options = {
            'case_types': [],
            'file_types': [],
            'confidentiality_levels': [],
            'warehouse_locations': [],
            'storage_statuses': []
        }
    
    # Create filters object for template
    template_filters = {
        'case_type': case_type_filter,
        'file_type': file_type_filter,
        'confidentiality_level': confidentiality_filter,
        'warehouse_location': warehouse_filter,
        'storage_status': storage_status_filter
    }
    
    return render_template('search.html',
                         results=results,
                         query=query,
                         filters=template_filters,
                         case_type_filter=case_type_filter,
                         file_type_filter=file_type_filter,
                         confidentiality_filter=confidentiality_filter,
                         warehouse_filter=warehouse_filter,
                         storage_status_filter=storage_status_filter,
                         case_types=filter_options.get('case_types', []),
                         file_types=filter_options.get('file_types', []),
                         confidentiality_levels=filter_options.get('confidentiality_levels', []),
                         warehouse_locations=filter_options.get('warehouse_locations', []),
                         storage_statuses=filter_options.get('storage_statuses', []),
                         get_client_name=get_client_name,
                         get_case_type=get_case_type)

@app.route('/file/<file_id>')
def file_detail(file_id):
    """Individual file details with related information (matching original app)"""
    try:
        # Get file details
        file_data = db_manager.get_file_by_id(file_id)
        
        if not file_data:
            return render_template('404.html'), 404
        
        # Get client information and recommendations (matching original app structure)
        recommendations = get_client_recommendations_for_file(file_data['client_id'])
        
        # Get file access history and statistics
        access_history = db_manager.get_file_access_history(file_id)
        access_stats = db_manager.get_file_access_stats(file_id)
        
        # Convert datetime objects in access_stats for template compatibility
        if access_stats.get('last_accessed') and hasattr(access_stats['last_accessed'], 'get'):
            # It's a database row object, convert datetime fields
            last_accessed = dict(access_stats['last_accessed'])
            for key, value in last_accessed.items():
                if hasattr(value, 'isoformat'):
                    last_accessed[key] = value.isoformat() if value else None
            access_stats['last_accessed'] = last_accessed
        
        # Get comments for this file
        comments = db_manager.get_comments_by_file(file_id)
        
        # Record file access (simulate different users like original app)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip_address = request.remote_addr or '127.0.0.1'
        
        # Simulate different users based on session/time (matching original app)
        demo_users = [
            ('John Smith', 'Partner'), ('Sarah Johnson', 'Associate'), 
            ('Michael Brown', 'Paralegal'), ('Current User', 'Demo User')
        ]
        import hashlib
        user_hash = int(hashlib.md5(f"{ip_address}{user_agent}".encode()).hexdigest()[:8], 16)
        current_user_name, current_user_role = demo_users[user_hash % len(demo_users)]
        
        access_data = {
            'access_id': f"ACC{random.randint(10000, 99999)}",
            'file_id': file_id,
            'user_name': current_user_name,
            'user_role': current_user_role,
            'access_timestamp': datetime.now().isoformat(),
            'access_type': 'view',
            'ip_address': ip_address,
            'user_agent': user_agent,
            'session_duration': None
        }
        
        try:
            db_manager.insert_file_access(access_data)
            db_manager.update_file_access_time(file_id)
        except Exception as e:
            print(f"Error recording file access: {e}")
        
        # Convert datetime objects in access_history for template compatibility
        for access in access_history:
            for key, value in access.items():
                if hasattr(value, 'isoformat'):
                    access[key] = value.isoformat() if value else None
        
        # Sort access history by timestamp (most recent first)
        access_history.sort(key=lambda x: x['access_timestamp'], reverse=True)
        
        return render_template('file_detail.html',
                             file=file_data,
                             recommendations=recommendations,
                             access_history=access_history,
                             access_stats=access_stats,
                             comments=comments,
                             get_client_name=get_client_name,
                             get_case_type=get_case_type)
    except Exception as e:
        print(f"File detail error: {e}")
        return render_template('500.html'), 500

@app.route('/client/<client_id>')
def client_detail(client_id):
    """Client profile with recommendations and related information"""
    try:
        # Get client information
        client = db_manager.get_client_by_id(client_id)
        if not client:
            return render_template('404.html'), 404
        
        # Get client's cases
        cases = db_manager.get_cases_by_client(client_id)
        
        # Get client's payments
        payments = db_manager.get_payments_by_client(client_id)
        
        # Calculate payment summary
        total_paid = sum(float(p['amount'] or 0) for p in payments if p['status'] == 'Paid')
        total_pending = sum(float(p['amount'] or 0) for p in payments if p['status'] == 'Pending')
        total_overdue = sum(float(p['amount'] or 0) for p in payments if p['status'] == 'Overdue')
        
        # Get related files
        all_files = db_manager.search_files()
        related_files = [f for f in all_files if f['client_id'] == client_id]
        
        # Get recent file accesses for this client's files
        client_file_ids = [f['file_id'] for f in related_files]
        all_accesses = db_manager.get_recent_file_accesses(limit=50)
        recent_accesses = [a for a in all_accesses if a['file_id'] in client_file_ids][:5]
        
        # Create recommendations object matching original app structure
        recommendations = get_client_recommendations_data(client, cases, payments, related_files, recent_accesses, total_paid, total_pending, total_overdue)
        
        return render_template('client_detail.html',
                             recommendations=recommendations)
    except Exception as e:
        print(f"Client detail error: {e}")
        return render_template('500.html'), 500

def get_client_recommendations_data(client, cases, payments, related_files, recent_accesses, total_paid, total_pending, total_overdue):
    """Create client recommendations data structure matching original app"""
    def convert_datetime_to_string(obj):
        """Convert datetime objects to strings for template compatibility"""
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if hasattr(v, 'isoformat'):  # datetime objects
                    result[k] = v.isoformat() if v else None
                elif isinstance(v, (dict, list)):
                    result[k] = convert_datetime_to_string(v)
                else:
                    result[k] = v
            return result
        elif isinstance(obj, list):
            return [convert_datetime_to_string(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat() if obj else None
        else:
            return obj

    # Sort files by last_accessed (handling None values)
    related_files_sorted = sorted(related_files, 
                                key=lambda x: x.get('last_accessed') or datetime.min, 
                                reverse=True)
    
    # Sort payments by payment_date
    payments_sorted = sorted(payments, 
                           key=lambda x: x.get('payment_date') or datetime.min, 
                           reverse=True)

    recommendations = {
        'client': convert_datetime_to_string(dict(client)),
        'active_cases': convert_datetime_to_string([dict(c) for c in cases if c.get('case_status') == 'Open']),
        'all_cases': convert_datetime_to_string([dict(c) for c in cases]),
        'payment_summary': {
            'total_paid': float(total_paid),
            'total_pending': float(total_pending),
            'total_overdue': float(total_overdue),
            'recent_payments': convert_datetime_to_string([dict(p) for p in payments_sorted[:5]])
        },
        'file_count': len(related_files),
        'recent_files': convert_datetime_to_string([dict(f) for f in related_files_sorted[:5]]),
        'all_files': convert_datetime_to_string([dict(f) for f in related_files_sorted])
    }
    
    return recommendations

def get_client_recommendations_for_file(client_id: str) -> Dict[str, Any]:
    """Get client recommendations for file detail page (optimized version)"""
    try:
        # Get client information
        client = db_manager.get_client_by_id(client_id)
        if not client:
            return {}

        # Get client's cases (only active ones for file detail)
        client_cases = db_manager.get_cases_by_client(client_id)
        active_cases = [c for c in client_cases if c.get('case_status') == 'Open']
        
        # Get client's payments (recent ones only for file detail)
        client_payments = db_manager.get_payments_by_client(client_id)
        
        # Calculate payment statistics
        total_paid = sum(float(p['amount'] or 0) for p in client_payments if p['status'] == 'Paid')
        total_pending = sum(float(p['amount'] or 0) for p in client_payments if p['status'] == 'Pending')
        total_overdue = sum(float(p['amount'] or 0) for p in client_payments if p['status'] == 'Overdue')

        # Sort payments by payment_date (recent first)
        client_payments_sorted = sorted(client_payments, 
                                      key=lambda x: x.get('payment_date') or datetime.min, 
                                      reverse=True)

        # Convert datetime objects to strings for template compatibility
        def convert_datetime_to_string(obj):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if hasattr(v, 'isoformat'):
                        result[k] = v.isoformat() if v else None
                    elif isinstance(v, (dict, list)):
                        result[k] = convert_datetime_to_string(v)
                    else:
                        result[k] = v
                return result
            elif isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat() if obj else None
            else:
                return obj

        recommendations = {
            'client': convert_datetime_to_string(dict(client)),
            'active_cases': convert_datetime_to_string([dict(c) for c in active_cases]),
            'payment_summary': {
                'total_paid': float(total_paid),
                'total_pending': float(total_pending),
                'total_overdue': float(total_overdue),
                'recent_payments': convert_datetime_to_string([dict(p) for p in client_payments_sorted[:5]])
            }
        }
        
        return recommendations
        
    except Exception as e:
        print(f"Error getting client recommendations for file: {e}")
        return {}

def get_client_name(client_id: str) -> str:
    """Get client name by ID (matching original app helper function)"""
    try:
        client = db_manager.get_client_by_id(client_id)
        if client:
            return f"{client['first_name']} {client['last_name']}"
        return "Unknown Client"
    except:
        return "Unknown Client"

def get_case_type(case_id: str) -> str:
    """Get case type by case ID (matching original app helper function)"""
    try:
        all_cases = db_manager.get_all_cases()
        case = next((c for c in all_cases if c['case_id'] == case_id), None)
        if case:
            return case['case_type']
        return "Unknown Case Type"
    except:
        return "Unknown Case Type"

@app.route('/api/search')
def api_search():
    """JSON API for search functionality"""
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
        results = db_manager.search_files(query, filters)
        
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

@app.route('/api/stats')
def api_stats():
    """JSON API for dashboard statistics"""
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

@app.route('/api/filters')
def api_filters():
    """JSON API for filter options"""
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

@app.route('/api/unified-search')
def api_unified_search():
    """API endpoint for unified search across all data types (matching original app)"""
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

def unified_search_data(query: str, filters: Dict[str, Any] = None, include_private_comments: bool = False) -> Dict[str, Any]:
    """
    Unified search across all data types: files, clients, cases, payments, access history, and comments
    Returns categorized results with relevance scoring (matching original app)
    """
    if not query and not filters:
        return {
            'files': [],
            'clients': [],
            'cases': [],
            'payments': [],
            'access_history': [],
            'comments': [],
            'total_results': 0,
            'query': query
        }
    
    query_lower = query.lower() if query else ""
    results = {
        'files': [],
        'clients': [],
        'cases': [],
        'payments': [],
        'access_history': [],
        'comments': [],
        'total_results': 0,
        'query': query
    }
    
    try:
        # Search Files (enhanced scoring)
        if query:
            files = db_manager.search_files(query, filters or {})
            for file in files:
                score = 0
                matches = []
                
                # Check various file fields with different weights
                if query_lower in file['reference_number'].lower():
                    score += 10
                    matches.append(f"Reference: {file['reference_number']}")
                if query_lower in (file.get('file_description') or '').lower():
                    score += 8
                    matches.append(f"Description: {(file.get('file_description') or '')[:100]}...")
                if query_lower in (file.get('document_category') or '').lower():
                    score += 6
                    matches.append(f"Category: {file.get('document_category')}")
                if query_lower in (file.get('file_type') or '').lower():
                    score += 6
                    matches.append(f"Type: {file.get('file_type')}")
                if file.get('keywords') and any(query_lower in (keyword or '').lower() for keyword in file['keywords']):
                    score += 7
                    matching_keywords = [kw for kw in file['keywords'] if query_lower in (kw or '').lower()]
                    matches.append(f"Keywords: {', '.join(matching_keywords)}")
                
                client_name = get_client_name(file['client_id'])
                if query_lower in client_name.lower():
                    score += 9
                    matches.append(f"Client: {client_name}")
                
                case_type = get_case_type(file['case_id'])
                if query_lower in case_type.lower():
                    score += 7
                    matches.append(f"Case Type: {case_type}")
                
                if score > 0:
                    file_result = dict(file)
                    file_result['client_name'] = client_name
                    file_result['case_type'] = case_type
                    file_result['relevance_score'] = score
                    file_result['match_details'] = matches
                    # Convert datetime objects
                    for key, value in file_result.items():
                        if hasattr(value, 'isoformat'):
                            file_result[key] = value.isoformat() if value else None
                    results['files'].append(file_result)
        
        # Search Clients
        if query:
            all_clients = db_manager.get_all_clients()
            for client in all_clients:
                score = 0
                matches = []
                
                full_name = f"{client['first_name']} {client['last_name']}".lower()
                if query_lower in full_name:
                    score += 10
                    matches.append(f"Name: {client['first_name']} {client['last_name']}")
                if query_lower in client['email'].lower():
                    score += 9
                    matches.append(f"Email: {client['email']}")
                if query_lower in (client.get('phone') or '').lower():
                    score += 8
                    matches.append(f"Phone: {client.get('phone')}")
                if query_lower in (client.get('address') or '').lower():
                    score += 6
                    matches.append(f"Address: {(client.get('address') or '')[:100]}...")
                if query_lower in (client.get('client_type') or '').lower():
                    score += 5
                    matches.append(f"Type: {client.get('client_type')}")
                if query_lower in (client.get('status') or '').lower():
                    score += 4
                    matches.append(f"Status: {client.get('status')}")
                
                if score > 0:
                    client_result = dict(client)
                    client_result['relevance_score'] = score
                    client_result['match_details'] = matches
                    # Convert datetime objects
                    for key, value in client_result.items():
                        if hasattr(value, 'isoformat'):
                            client_result[key] = value.isoformat() if value else None
                    results['clients'].append(client_result)
        
        # Search Cases
        if query:
            all_cases = db_manager.get_all_cases()
            for case in all_cases:
                score = 0
                matches = []
                
                if query_lower in case['reference_number'].lower():
                    score += 10
                    matches.append(f"Reference: {case['reference_number']}")
                if query_lower in (case.get('case_type') or '').lower():
                    score += 8
                    matches.append(f"Type: {case.get('case_type')}")
                if query_lower in (case.get('description') or '').lower():
                    score += 7
                    matches.append(f"Description: {(case.get('description') or '')[:100]}...")
                if query_lower in (case.get('assigned_lawyer') or '').lower():
                    score += 6
                    matches.append(f"Lawyer: {case.get('assigned_lawyer')}")
                if query_lower in (case.get('case_status') or '').lower():
                    score += 5
                    matches.append(f"Status: {case.get('case_status')}")
                
                client_name = get_client_name(case['client_id'])
                if query_lower in client_name.lower():
                    score += 9
                    matches.append(f"Client: {client_name}")
                
                if score > 0:
                    case_result = dict(case)
                    case_result['client_name'] = client_name
                    case_result['relevance_score'] = score
                    case_result['match_details'] = matches
                    # Convert datetime objects
                    for key, value in case_result.items():
                        if hasattr(value, 'isoformat'):
                            case_result[key] = value.isoformat() if value else None
                    results['cases'].append(case_result)
        
        # Search Payments
        if query:
            all_payments = db_manager.get_all_payments()
            for payment in all_payments:
                score = 0
                matches = []
                
                if query_lower in (payment.get('description') or '').lower():
                    score += 8
                    matches.append(f"Description: {payment.get('description')}")
                if query_lower in (payment.get('payment_method') or '').lower():
                    score += 6
                    matches.append(f"Method: {payment.get('payment_method')}")
                if query_lower in (payment.get('status') or '').lower():
                    score += 5
                    matches.append(f"Status: {payment.get('status')}")
                
                # Check amount (convert to string for search)
                amount_str = str(payment.get('amount', ''))
                if query_lower in amount_str:
                    score += 7
                    matches.append(f"Amount: ${payment.get('amount')}")
                
                client_name = get_client_name(payment['client_id'])
                if query_lower in client_name.lower():
                    score += 9
                    matches.append(f"Client: {client_name}")
                
                if score > 0:
                    payment_result = dict(payment)
                    payment_result['client_name'] = client_name
                    payment_result['relevance_score'] = score
                    payment_result['match_details'] = matches
                    # Convert datetime objects
                    for key, value in payment_result.items():
                        if hasattr(value, 'isoformat'):
                            payment_result[key] = value.isoformat() if value else None
                    results['payments'].append(payment_result)
        
        # Search Access History
        if query:
            recent_accesses = db_manager.get_recent_file_accesses(100)  # Get more for searching
            for access in recent_accesses:
                score = 0
                matches = []
                
                if query_lower in (access.get('user_name') or '').lower():
                    score += 8
                    matches.append(f"User: {access.get('user_name')}")
                if query_lower in (access.get('access_type') or '').lower():
                    score += 6
                    matches.append(f"Access Type: {access.get('access_type')}")
                if query_lower in (access.get('user_role') or '').lower():
                    score += 5
                    matches.append(f"Role: {access.get('user_role')}")
                
                # Check if file reference matches
                if access.get('reference_number') and query_lower in access['reference_number'].lower():
                    score += 9
                    matches.append(f"File: {access['reference_number']}")
                
                if score > 0:
                    access_result = dict(access)
                    access_result['relevance_score'] = score
                    access_result['match_details'] = matches
                    # Convert datetime objects
                    for key, value in access_result.items():
                        if hasattr(value, 'isoformat'):
                            access_result[key] = value.isoformat() if value else None
                    results['access_history'].append(access_result)
        
        # Search Comments (if available)
        # Note: We would need to implement get_all_comments in database.py
        results['comments'] = []  # Placeholder for now
        
        # Sort results by relevance score
        for category in ['files', 'clients', 'cases', 'payments', 'access_history']:
            results[category] = sorted(results[category], key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Calculate total results
        results['total_results'] = sum(len(results[cat]) for cat in ['files', 'clients', 'cases', 'payments', 'access_history', 'comments'])
        
        return results
        
    except Exception as e:
        print(f"Unified search error: {e}")
        return {
            'files': [],
            'clients': [],
            'cases': [],
            'payments': [],
            'access_history': [],
            'comments': [],
            'total_results': 0,
            'query': query,
            'error': str(e)
        }

@app.route('/api/suggestions')
def api_suggestions():
    """API endpoint for intelligent search suggestions (backward compatibility)"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))
    
    try:
        # Get intelligent suggestions (reuse the existing function)
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

@app.route('/api/intelligent-suggestions')
def api_intelligent_suggestions():
    """API endpoint for intelligent search suggestions (matching original app)"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 8))
    
    try:
        suggestions_data = api_intelligent_suggestions_data(query, limit)
        return jsonify(suggestions_data)
    except Exception as e:
        return jsonify({'suggestions': []})

def api_intelligent_suggestions_data(query: str, limit: int = 8) -> Dict[str, Any]:
    """Helper function to get intelligent suggestions data"""
    try:
        if len(query) < 2:
            return {'suggestions': []}
        
        # Get suggestions from various sources
        suggestions = []
        
        # Search files for matching terms
        files = db_manager.search_files(query, {})[:limit//2]
        for file in files:
            suggestions.append({
                'type': 'file',
                'text': file['reference_number'],
                'description': file['file_description'][:100] + '...' if len(file.get('file_description', '')) > 100 else file.get('file_description', ''),
                'url': f"/file/{file['file_id']}"
            })
        
        # Search clients
        all_clients = db_manager.get_all_clients()
        matching_clients = [c for c in all_clients if query.lower() in f"{c['first_name']} {c['last_name']}".lower()][:limit//4]
        for client in matching_clients:
            suggestions.append({
                'type': 'client',
                'text': f"{client['first_name']} {client['last_name']}",
                'description': f"{client['client_type']} - {client['email']}",
                'url': f"/client/{client['client_id']}"
            })
        
        return {'suggestions': suggestions[:limit]}
    except Exception as e:
        return {'suggestions': []}

@app.route('/api/recent-activity')
def api_recent_activity():
    """API endpoint to get recent file access activity (matching original app)"""
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

@app.route('/api/filter-options')
def api_filter_options():
    """API endpoint to get available filter options (matching original app)"""
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

@app.route('/api/access-history/<file_id>')
def api_access_history(file_id):
    """API endpoint to get access history for a specific file (matching original app)"""
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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle unexpected exceptions"""
    print(f"Unexpected error: {e}")
    return render_template('500.html'), 500

# Health check endpoint
@app.route('/debug-search')
def debug_search():
    """Debug page for testing search dropdown functionality"""
    return '''
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
    '''

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        stats = db_manager.get_dashboard_stats()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("Starting Legal Case File Manager with PostgreSQL backend")
    print(f"Database: {Config.DB_NAME} on {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"Server: http://{Config.APP_HOST}:{Config.APP_PORT}")
    
    app.run(
        debug=Config.DEBUG,
        host=Config.APP_HOST,
        port=Config.APP_PORT
    )

