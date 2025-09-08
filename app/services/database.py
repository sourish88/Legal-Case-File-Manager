"""
Database service for the Legal Case File Manager application.

This module provides database connection and query functionality using PostgreSQL.
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

class DatabaseConnection:
    def __init__(self, host='localhost', port=5432, database='legal_case_manager', 
                 user='postgres', password='postgres'):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
    
    def get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(**self.connection_params)
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, 
                     fetch_all: bool = True) -> Any:
        """Execute a query and return results"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = None
                
            conn.commit()
            cursor.close()
            conn.close()
            return result
        except psycopg2.Error as e:
            print(f"Database error: {e}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute a query with multiple parameter sets"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            print(f"Database error: {e}")
            raise

class LegalFileManagerDB:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    # Client methods
    def insert_client(self, client_data: Dict[str, Any]) -> None:
        """Insert a new client"""
        query = """
        INSERT INTO clients (client_id, first_name, last_name, email, phone, address, 
                           date_of_birth, client_type, registration_date, status)
        VALUES (%(client_id)s, %(first_name)s, %(last_name)s, %(email)s, %(phone)s, 
                %(address)s, %(date_of_birth)s, %(client_type)s, %(registration_date)s, %(status)s)
        """
        self.db.execute_query(query, client_data, fetch_all=False)
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients"""
        query = "SELECT * FROM clients ORDER BY last_name, first_name"
        return self.db.execute_query(query)
    
    def search_clients(self, search_query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Efficiently search clients using database indexes"""
        if not search_query:
            return []
            
        query = """
        SELECT *, 
               ts_rank(to_tsvector('english', coalesce(first_name, '') || ' ' || coalesce(last_name, '')), 
                      plainto_tsquery('english', %s)) as relevance_score
        FROM clients 
        WHERE to_tsvector('english', coalesce(first_name, '') || ' ' || coalesce(last_name, '')) @@ plainto_tsquery('english', %s)
           OR first_name ILIKE %s 
           OR last_name ILIKE %s
           OR email ILIKE %s
           OR phone ILIKE %s
           OR address ILIKE %s
           OR client_type ILIKE %s
           OR status ILIKE %s
        ORDER BY relevance_score DESC, last_name, first_name
        LIMIT %s
        """
        search_param = f"%{search_query}%"
        params = (search_query, search_query, search_param, search_param, search_param, 
                 search_param, search_param, search_param, search_param, limit)
        return self.db.execute_query(query, params)
    
    def search_cases(self, search_query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Efficiently search cases with client names included"""
        if not search_query:
            return []
            
        query = """
        SELECT c.*, cl.first_name, cl.last_name,
               (cl.first_name || ' ' || cl.last_name) as client_name,
               CASE 
                   WHEN %s = '' THEN 0
                   ELSE (
                       CASE WHEN c.reference_number ILIKE %s THEN 10 ELSE 0 END +
                       CASE WHEN c.case_type ILIKE %s THEN 8 ELSE 0 END +
                       CASE WHEN c.description ILIKE %s THEN 7 ELSE 0 END +
                       CASE WHEN c.assigned_lawyer ILIKE %s THEN 6 ELSE 0 END +
                       CASE WHEN c.case_status ILIKE %s THEN 5 ELSE 0 END +
                       CASE WHEN (cl.first_name || ' ' || cl.last_name) ILIKE %s THEN 9 ELSE 0 END
                   )
               END as relevance_score
        FROM cases c
        JOIN clients cl ON c.client_id = cl.client_id
        WHERE c.reference_number ILIKE %s 
           OR c.case_type ILIKE %s
           OR c.description ILIKE %s
           OR c.assigned_lawyer ILIKE %s
           OR c.case_status ILIKE %s
           OR (cl.first_name || ' ' || cl.last_name) ILIKE %s
        ORDER BY relevance_score DESC, c.created_date DESC
        LIMIT %s
        """
        search_param = f"%{search_query}%"
        params = (search_query, search_param, search_param, search_param, search_param, 
                 search_param, search_param, search_param, search_param, search_param, 
                 search_param, search_param, search_param, limit)
        return self.db.execute_query(query, params)
    
    def search_payments(self, search_query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Efficiently search payments with client names included"""
        if not search_query:
            return []
            
        query = """
        SELECT p.*, cl.first_name, cl.last_name,
               (cl.first_name || ' ' || cl.last_name) as client_name,
               CASE 
                   WHEN %s = '' THEN 0
                   ELSE (
                       CASE WHEN p.payment_id ILIKE %s THEN 10 ELSE 0 END +
                       CASE WHEN p.description ILIKE %s THEN 8 ELSE 0 END +
                       CASE WHEN p.payment_method ILIKE %s THEN 6 ELSE 0 END +
                       CASE WHEN p.status ILIKE %s THEN 5 ELSE 0 END +
                       CASE WHEN (cl.first_name || ' ' || cl.last_name) ILIKE %s THEN 9 ELSE 0 END
                   )
               END as relevance_score
        FROM payments p
        JOIN clients cl ON p.client_id = cl.client_id
        WHERE p.payment_id ILIKE %s 
           OR p.description ILIKE %s
           OR p.payment_method ILIKE %s
           OR p.status ILIKE %s
           OR (cl.first_name || ' ' || cl.last_name) ILIKE %s
        ORDER BY relevance_score DESC, p.payment_date DESC
        LIMIT %s
        """
        search_param = f"%{search_query}%"
        params = (search_query, search_param, search_param, search_param, search_param, 
                 search_param, search_param, search_param, search_param, search_param, 
                 search_param, limit)
        return self.db.execute_query(query, params)
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID"""
        query = "SELECT * FROM clients WHERE client_id = %s"
        return self.db.execute_query(query, (client_id,), fetch_one=True)
    
    def update_client(self, client_id: str, client_data: Dict[str, Any]) -> None:
        """Update a client"""
        set_clause = ", ".join([f"{key} = %({key})s" for key in client_data.keys()])
        query = f"UPDATE clients SET {set_clause} WHERE client_id = %(client_id)s"
        client_data['client_id'] = client_id
        self.db.execute_query(query, client_data, fetch_all=False)
    
    # Case methods
    def insert_case(self, case_data: Dict[str, Any]) -> None:
        """Insert a new case"""
        query = """
        INSERT INTO cases (case_id, reference_number, client_id, case_type, case_status,
                          created_date, assigned_lawyer, priority, estimated_value, description)
        VALUES (%(case_id)s, %(reference_number)s, %(client_id)s, %(case_type)s, %(case_status)s,
                %(created_date)s, %(assigned_lawyer)s, %(priority)s, %(estimated_value)s, %(description)s)
        """
        self.db.execute_query(query, case_data, fetch_all=False)
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases"""
        query = """
        SELECT c.*, cl.first_name, cl.last_name 
        FROM cases c 
        JOIN clients cl ON c.client_id = cl.client_id 
        ORDER BY c.created_date DESC
        """
        return self.db.execute_query(query)
    
    def get_cases_by_client(self, client_id: str) -> List[Dict[str, Any]]:
        """Get cases for a specific client"""
        query = "SELECT * FROM cases WHERE client_id = %s ORDER BY created_date DESC"
        return self.db.execute_query(query, (client_id,))
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get a case by ID"""
        query = "SELECT * FROM cases WHERE case_id = %s"
        return self.db.execute_query(query, (case_id,), fetch_one=True)
    
    # Physical File methods
    def insert_physical_file(self, file_data: Dict[str, Any]) -> None:
        """Insert a new physical file"""
        query = """
        INSERT INTO physical_files (file_id, reference_number, case_id, client_id, file_type,
                                  document_category, warehouse_location, shelf_number, box_number,
                                  file_size, created_date, last_accessed, last_modified,
                                  storage_status, confidentiality_level, keywords, file_description)
        VALUES (%(file_id)s, %(reference_number)s, %(case_id)s, %(client_id)s, %(file_type)s,
                %(document_category)s, %(warehouse_location)s, %(shelf_number)s, %(box_number)s,
                %(file_size)s, %(created_date)s, %(last_accessed)s, %(last_modified)s,
                %(storage_status)s, %(confidentiality_level)s, %(keywords)s, %(file_description)s)
        """
        self.db.execute_query(query, file_data, fetch_all=False)
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all physical files"""
        query = """
        SELECT f.*, c.case_type, c.case_status, cl.first_name, cl.last_name 
        FROM physical_files f 
        LEFT JOIN cases c ON f.case_id = c.case_id 
        LEFT JOIN clients cl ON f.client_id = cl.client_id 
        ORDER BY f.created_date DESC
        """
        return self.db.execute_query(query)
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get a file by ID with related information"""
        query = """
        SELECT f.*, c.case_type, c.case_status, c.reference_number as case_reference,
               cl.first_name, cl.last_name, cl.email, cl.phone
        FROM physical_files f 
        LEFT JOIN cases c ON f.case_id = c.case_id 
        LEFT JOIN clients cl ON f.client_id = cl.client_id 
        WHERE f.file_id = %s
        """
        return self.db.execute_query(query, (file_id,), fetch_one=True)
    
    def search_files(self, search_query: str = "", filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search files with optional filters - optimized for performance"""
        base_query = """
        SELECT f.*, c.case_type, c.case_status, cl.first_name, cl.last_name,
               CASE 
                   WHEN %s = '' THEN 0
                   ELSE (
                       CASE WHEN f.reference_number ILIKE %s THEN 10 ELSE 0 END +
                       CASE WHEN f.file_description ILIKE %s THEN 8 ELSE 0 END +
                       CASE WHEN cl.first_name ILIKE %s THEN 7 ELSE 0 END +
                       CASE WHEN cl.last_name ILIKE %s THEN 7 ELSE 0 END +
                       CASE WHEN array_to_string(f.keywords, ' ') ILIKE %s THEN 6 ELSE 0 END +
                       CASE WHEN c.case_type ILIKE %s THEN 5 ELSE 0 END
                   )
               END as relevance_score
        FROM physical_files f 
        LEFT JOIN cases c ON f.case_id = c.case_id 
        LEFT JOIN clients cl ON f.client_id = cl.client_id 
        WHERE 1=1
        """
        
        conditions = []
        params = [search_query or '']  # First param for relevance calculation
        search_param = f"%{search_query}%" if search_query else "%"
        params.extend([search_param] * 6)  # For relevance calculation
        
        if search_query:
            # Use indexes for fast filtering
            search_condition = """
            AND (f.reference_number ILIKE %s 
                 OR f.file_description ILIKE %s 
                 OR cl.first_name ILIKE %s 
                 OR cl.last_name ILIKE %s
                 OR array_to_string(f.keywords, ' ') ILIKE %s
                 OR c.case_type ILIKE %s)
            """
            conditions.append(search_condition)
            params.extend([search_param] * 6)
        
        if filters:
            if filters.get('case_type'):
                conditions.append("AND c.case_type = %s")
                params.append(filters['case_type'])
            
            if filters.get('file_type'):
                conditions.append("AND f.file_type = %s")
                params.append(filters['file_type'])
            
            if filters.get('confidentiality_level'):
                conditions.append("AND f.confidentiality_level = %s")
                params.append(filters['confidentiality_level'])
            
            if filters.get('warehouse_location'):
                conditions.append("AND f.warehouse_location = %s")
                params.append(filters['warehouse_location'])
            
            if filters.get('storage_status'):
                conditions.append("AND f.storage_status = %s")
                params.append(filters['storage_status'])
        
        # Order by relevance first, then by recency
        order_clause = " ORDER BY relevance_score DESC, f.last_accessed DESC NULLS LAST, f.created_date DESC"
        limit_clause = f" LIMIT {limit}"
        
        query = base_query + " ".join(conditions) + order_clause + limit_clause
        return self.db.execute_query(query, tuple(params) if params else None)
    
    def update_file_access_time(self, file_id: str) -> None:
        """Update the last accessed time for a file"""
        query = "UPDATE physical_files SET last_accessed = CURRENT_TIMESTAMP WHERE file_id = %s"
        self.db.execute_query(query, (file_id,), fetch_all=False)
    
    # Payment methods
    def insert_payment(self, payment_data: Dict[str, Any]) -> None:
        """Insert a new payment"""
        query = """
        INSERT INTO payments (payment_id, client_id, case_id, amount, payment_date,
                            payment_method, status, description)
        VALUES (%(payment_id)s, %(client_id)s, %(case_id)s, %(amount)s, %(payment_date)s,
                %(payment_method)s, %(status)s, %(description)s)
        """
        self.db.execute_query(query, payment_data, fetch_all=False)
    
    def get_payments_by_client(self, client_id: str) -> List[Dict[str, Any]]:
        """Get payments for a specific client"""
        query = "SELECT * FROM payments WHERE client_id = %s ORDER BY payment_date DESC"
        return self.db.execute_query(query, (client_id,))
    
    def get_payments_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """Get payments for a specific case"""
        query = "SELECT * FROM payments WHERE case_id = %s ORDER BY payment_date DESC"
        return self.db.execute_query(query, (case_id,))
    
    # File Access methods
    def insert_file_access(self, access_data: Dict[str, Any]) -> None:
        """Insert file access record"""
        query = """
        INSERT INTO file_accesses (access_id, file_id, user_name, user_role, access_timestamp, access_type, ip_address, user_agent, session_duration)
        VALUES (%(access_id)s, %(file_id)s, %(user_name)s, %(user_role)s, %(access_timestamp)s, %(access_type)s, %(ip_address)s, %(user_agent)s, %(session_duration)s)
        """
        self.db.execute_query(query, access_data, fetch_all=False)
    
    def get_recent_file_accesses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent file accesses"""
        query = """
        SELECT fa.*, f.reference_number, f.file_description 
        FROM file_accesses fa 
        JOIN physical_files f ON fa.file_id = f.file_id 
        ORDER BY fa.access_timestamp DESC 
        LIMIT %s
        """
        return self.db.execute_query(query, (limit,))
    
    def get_file_access_history(self, file_id: str) -> List[Dict[str, Any]]:
        """Get access history for a specific file"""
        query = "SELECT * FROM file_accesses WHERE file_id = %s ORDER BY access_timestamp DESC"
        return self.db.execute_query(query, (file_id,))
    
    # Comment methods
    def insert_comment(self, comment_data: Dict[str, Any]) -> None:
        """Insert a new comment"""
        query = """
        INSERT INTO user_comments (comment_id, entity_type, entity_id, user_name, user_role, comment_text, created_timestamp, is_private)
        VALUES (%(comment_id)s, %(entity_type)s, %(entity_id)s, %(user_name)s, %(user_role)s, %(comment_text)s, %(created_timestamp)s, %(is_private)s)
        """
        self.db.execute_query(query, comment_data, fetch_all=False)
    
    def get_comments_by_file(self, file_id: str) -> List[Dict[str, Any]]:
        """Get comments for a specific file"""
        query = "SELECT * FROM user_comments WHERE entity_type = 'file' AND entity_id = %s ORDER BY created_timestamp DESC"
        return self.db.execute_query(query, (file_id,))
    
    def get_comments_by_entity(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Get comments for a specific entity"""
        query = "SELECT * FROM user_comments WHERE entity_type = %s AND entity_id = %s ORDER BY created_timestamp DESC"
        return self.db.execute_query(query, (entity_type, entity_id))
    
    # Analytics methods
    def add_recent_search(self, search_query: str, user_session: str = None) -> None:
        """Add a recent search"""
        query = "INSERT INTO recent_searches (search_query, user_session) VALUES (%s, %s)"
        self.db.execute_query(query, (search_query, user_session), fetch_all=False)
    
    def update_popular_search(self, search_query: str) -> None:
        """Update popular search count"""
        query = """
        INSERT INTO popular_searches (search_query, search_count, last_searched) 
        VALUES (%s, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (search_query) 
        DO UPDATE SET search_count = popular_searches.search_count + 1, 
                      last_searched = CURRENT_TIMESTAMP
        """
        self.db.execute_query(query, (search_query,), fetch_all=False)
    
    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular searches"""
        query = "SELECT * FROM popular_searches ORDER BY search_count DESC LIMIT %s"
        return self.db.execute_query(query, (limit,))
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent searches"""
        query = "SELECT search_query, MAX(search_date) as latest_date FROM recent_searches GROUP BY search_query ORDER BY latest_date DESC LIMIT %s"
        return self.db.execute_query(query, (limit,))
    
    # Statistics methods
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        stats = {}
        
        # Client stats
        client_query = """
        SELECT 
            COUNT(*) as total_clients,
            COUNT(CASE WHEN status = 'Active' THEN 1 END) as active_clients
        FROM clients
        """
        client_stats = self.db.execute_query(client_query, fetch_one=True)
        stats.update(client_stats)
        
        # Case stats
        case_query = """
        SELECT 
            COUNT(*) as total_cases,
            COUNT(CASE WHEN case_status = 'Open' THEN 1 END) as active_cases,
            COUNT(CASE WHEN case_status = 'Closed' THEN 1 END) as closed_cases
        FROM cases
        """
        case_stats = self.db.execute_query(case_query, fetch_one=True)
        stats.update(case_stats)
        
        # File stats
        file_query = """
        SELECT 
            COUNT(*) as total_files,
            COUNT(CASE WHEN storage_status = 'Active' THEN 1 END) as active_files
        FROM physical_files
        """
        file_stats = self.db.execute_query(file_query, fetch_one=True)
        stats.update(file_stats)
        
        # Payment stats
        payment_query = """
        SELECT 
            COUNT(*) as total_payments,
            SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END) as total_paid,
            SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END) as total_pending,
            SUM(CASE WHEN status = 'Overdue' THEN amount ELSE 0 END) as total_overdue
        FROM payments
        """
        payment_stats = self.db.execute_query(payment_query, fetch_one=True)
        stats.update(payment_stats)
        
        return stats
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options for search"""
        options = {}
        
        # Case types
        case_types_query = "SELECT DISTINCT case_type FROM cases WHERE case_type IS NOT NULL ORDER BY case_type"
        case_types = [row['case_type'] for row in self.db.execute_query(case_types_query)]
        options['case_types'] = case_types
        
        # File types
        file_types_query = "SELECT DISTINCT file_type FROM physical_files WHERE file_type IS NOT NULL ORDER BY file_type"
        file_types = [row['file_type'] for row in self.db.execute_query(file_types_query)]
        options['file_types'] = file_types
        
        # Confidentiality levels
        conf_query = "SELECT DISTINCT confidentiality_level FROM physical_files WHERE confidentiality_level IS NOT NULL ORDER BY confidentiality_level"
        conf_levels = [row['confidentiality_level'] for row in self.db.execute_query(conf_query)]
        options['confidentiality_levels'] = conf_levels
        
        # Warehouse locations
        warehouse_query = "SELECT DISTINCT warehouse_location FROM physical_files WHERE warehouse_location IS NOT NULL ORDER BY warehouse_location"
        warehouses = [row['warehouse_location'] for row in self.db.execute_query(warehouse_query)]
        options['warehouse_locations'] = warehouses
        
        # Storage statuses
        status_query = "SELECT DISTINCT storage_status FROM physical_files WHERE storage_status IS NOT NULL ORDER BY storage_status"
        statuses = [row['storage_status'] for row in self.db.execute_query(status_query)]
        options['storage_statuses'] = statuses
        
        return options
    
    # Additional methods to support unified search
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases"""
        query = "SELECT * FROM cases ORDER BY created_date DESC"
        return self.db.execute_query(query)
    
    def get_all_payments(self) -> List[Dict[str, Any]]:
        """Get all payments"""
        query = "SELECT * FROM payments ORDER BY payment_date DESC"
        return self.db.execute_query(query)
    
    def get_all_comments(self) -> List[Dict[str, Any]]:
        """Get all comments"""
        query = "SELECT * FROM user_comments ORDER BY created_timestamp DESC"
        return self.db.execute_query(query)
    
    def update_file_access_time(self, file_id: str) -> None:
        """Update the last_accessed time for a file"""
        query = "UPDATE physical_files SET last_accessed = CURRENT_TIMESTAMP WHERE file_id = %s"
        self.db.execute_query(query, (file_id,), fetch_all=False)
    
    def get_file_access_stats(self, file_id: str) -> Dict[str, Any]:
        """Get access statistics for a specific file (matching original app)"""
        accesses = self.get_file_access_history(file_id)
        
        if not accesses:
            return {
                'total_accesses': 0,
                'unique_users': 0,
                'last_accessed': None,
                'most_frequent_user': None,
                'access_types': {},
                'user_access_counts': {}
            }
        
        # Calculate statistics
        unique_users = len(set(access['user_name'] for access in accesses))
        last_access = max(accesses, key=lambda x: x['access_timestamp'])
        
        # Count access types and user accesses
        access_type_counts = {}
        user_access_counts = {}
        
        for access in accesses:
            access_type = access['access_type']
            user_name = access['user_name']
            
            access_type_counts[access_type] = access_type_counts.get(access_type, 0) + 1
            user_access_counts[user_name] = user_access_counts.get(user_name, 0) + 1
        
        most_frequent_user = max(user_access_counts.items(), key=lambda x: x[1])[0] if user_access_counts else None
        
        return {
            'total_accesses': len(accesses),
            'unique_users': unique_users,
            'last_accessed': last_access,
            'most_frequent_user': most_frequent_user,
            'access_types': access_type_counts,
            'user_access_counts': user_access_counts
        }

    # Job persistence methods
    def save_terraform_job(self, job: 'TerraformJob') -> bool:
        """Save or update a terraform job in the database"""
        try:
            query = """
                INSERT INTO terraform_jobs (
                    job_id, source_db_type, target_cloud, source_connection, 
                    target_tables, status, progress, created_at, completed_at,
                    terraform_config, field_mappings, ai_analysis, estimated_cost, errors
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    progress = EXCLUDED.progress,
                    completed_at = EXCLUDED.completed_at,
                    terraform_config = EXCLUDED.terraform_config,
                    field_mappings = EXCLUDED.field_mappings,
                    ai_analysis = EXCLUDED.ai_analysis,
                    estimated_cost = EXCLUDED.estimated_cost,
                    errors = EXCLUDED.errors,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                job.job_id,
                job.source_db_type,
                job.target_cloud,
                job.source_connection,
                job.target_tables,
                job.status,
                job.progress,
                job.created_at,
                job.completed_at,
                Json(job.terraform_config) if job.terraform_config else None,
                Json(job.field_mappings) if job.field_mappings else None,
                Json(job.ai_analysis) if job.ai_analysis else None,
                Json(job.estimated_cost) if job.estimated_cost else None,
                job.errors
            )
            
            self.db.execute_query(query, params, fetch_all=False)
            return True
            
        except Exception as e:
            print(f"Error saving terraform job: {e}")
            return False

    def get_terraform_job(self, job_id: str) -> Optional['TerraformJob']:
        """Get a terraform job by ID"""
        try:
            query = """
                SELECT job_id, source_db_type, target_cloud, source_connection, 
                       target_tables, status, progress, created_at, completed_at,
                       terraform_config, field_mappings, ai_analysis, estimated_cost, errors
                FROM terraform_jobs 
                WHERE job_id = %s
            """
            
            result = self.db.execute_query(query, (job_id,), fetch_one=True)
            
            if result:
                from app.models.entities import TerraformJob
                return TerraformJob(
                    job_id=result['job_id'],
                    source_db_type=result['source_db_type'],
                    target_cloud=result['target_cloud'],
                    source_connection=result['source_connection'],
                    target_tables=result['target_tables'],
                    status=result['status'],
                    progress=float(result['progress']),
                    created_at=result['created_at'],
                    completed_at=result['completed_at'],
                    terraform_config=result['terraform_config'] if result['terraform_config'] else None,
                    field_mappings=result['field_mappings'] if result['field_mappings'] else None,
                    ai_analysis=result['ai_analysis'] if result['ai_analysis'] else None,
                    estimated_cost=result['estimated_cost'] if result['estimated_cost'] else None,
                    errors=result['errors']
                )
            return None
            
        except Exception as e:
            print(f"Error getting terraform job: {e}")
            return None

    def get_all_terraform_jobs(self) -> List['TerraformJob']:
        """Get all terraform jobs, ordered by creation date (newest first)"""
        try:
            query = """
                SELECT job_id, source_db_type, target_cloud, source_connection, 
                       target_tables, status, progress, created_at, completed_at,
                       terraform_config, field_mappings, ai_analysis, estimated_cost, errors
                FROM terraform_jobs 
                ORDER BY created_at DESC
            """
            
            results = self.db.execute_query(query)
            jobs = []
            
            if results:
                from app.models.entities import TerraformJob
                for result in results:
                    job = TerraformJob(
                        job_id=result['job_id'],
                        source_db_type=result['source_db_type'],
                        target_cloud=result['target_cloud'],
                        source_connection=result['source_connection'],
                        target_tables=result['target_tables'],
                        status=result['status'],
                        progress=float(result['progress']),
                        created_at=result['created_at'],
                        completed_at=result['completed_at'],
                        terraform_config=result['terraform_config'] if result['terraform_config'] else None,
                        field_mappings=result['field_mappings'] if result['field_mappings'] else None,
                        ai_analysis=result['ai_analysis'] if result['ai_analysis'] else None,
                        estimated_cost=result['estimated_cost'] if result['estimated_cost'] else None,
                        errors=result['errors']
                    )
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            print(f"Error getting terraform jobs: {e}")
            return []

    def save_migration_job(self, job: 'MigrationJob') -> bool:
        """Save or update a migration job in the database"""
        try:
            query = """
                INSERT INTO migration_jobs (
                    job_id, source_db_type, source_connection, target_tables,
                    status, progress, created_at, completed_at,
                    table_count, total_records, migrated_records, errors
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    progress = EXCLUDED.progress,
                    completed_at = EXCLUDED.completed_at,
                    table_count = EXCLUDED.table_count,
                    total_records = EXCLUDED.total_records,
                    migrated_records = EXCLUDED.migrated_records,
                    errors = EXCLUDED.errors,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                job.job_id,
                job.source_db_type,
                job.source_connection,
                job.target_tables,
                job.status,
                job.progress,
                job.created_at,
                job.completed_at,
                job.table_count,
                job.total_records,
                job.migrated_records,
                job.errors
            )
            
            self.db.execute_query(query, params, fetch_all=False)
            return True
            
        except Exception as e:
            print(f"Error saving migration job: {e}")
            return False

    def get_migration_job(self, job_id: str) -> Optional['MigrationJob']:
        """Get a migration job by ID"""
        try:
            query = """
                SELECT job_id, source_db_type, source_connection, target_tables,
                       status, progress, created_at, completed_at,
                       table_count, total_records, migrated_records, errors
                FROM migration_jobs 
                WHERE job_id = %s
            """
            
            result = self.db.execute_query(query, (job_id,), fetch_one=True)
            
            if result:
                from app.models.entities import MigrationJob
                return MigrationJob(
                    job_id=result['job_id'],
                    source_db_type=result['source_db_type'],
                    source_connection=result['source_connection'],
                    target_tables=result['target_tables'],
                    status=result['status'],
                    progress=float(result['progress']),
                    created_at=result['created_at'],
                    completed_at=result['completed_at'],
                    table_count=result['table_count'],
                    total_records=result['total_records'],
                    migrated_records=result['migrated_records'],
                    errors=result['errors']
                )
            return None
            
        except Exception as e:
            print(f"Error getting migration job: {e}")
            return None

    def get_all_migration_jobs(self) -> List['MigrationJob']:
        """Get all migration jobs, ordered by creation date (newest first)"""
        try:
            query = """
                SELECT job_id, source_db_type, source_connection, target_tables,
                       status, progress, created_at, completed_at,
                       table_count, total_records, migrated_records, errors
                FROM migration_jobs 
                ORDER BY created_at DESC
            """
            
            results = self.db.execute_query(query)
            jobs = []
            
            if results:
                from app.models.entities import MigrationJob
                for result in results:
                    job = MigrationJob(
                        job_id=result['job_id'],
                        source_db_type=result['source_db_type'],
                        source_connection=result['source_connection'],
                        target_tables=result['target_tables'],
                        status=result['status'],
                        progress=float(result['progress']),
                        created_at=result['created_at'],
                        completed_at=result['completed_at'],
                        table_count=result['table_count'],
                        total_records=result['total_records'],
                        migrated_records=result['migrated_records'],
                        errors=result['errors']
                    )
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            print(f"Error getting migration jobs: {e}")
            return []

    def delete_terraform_job(self, job_id: str) -> bool:
        """Delete a terraform job"""
        try:
            query = "DELETE FROM terraform_jobs WHERE job_id = %s"
            self.db.execute_query(query, (job_id,), fetch_all=False)
            return True
        except Exception as e:
            print(f"Error deleting terraform job: {e}")
            return False

    def delete_migration_job(self, job_id: str) -> bool:
        """Delete a migration job"""
        try:
            query = "DELETE FROM migration_jobs WHERE job_id = %s"
            self.db.execute_query(query, (job_id,), fetch_all=False)
            return True
        except Exception as e:
            print(f"Error deleting migration job: {e}")
            return False

