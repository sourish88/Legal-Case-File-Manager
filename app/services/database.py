"""
Database service for the Legal Case File Manager application.

This module provides secure database connection pooling and query functionality using PostgreSQL.
Features include:
- ThreadedConnectionPool for efficient connection management
- Connection timeout and retry logic
- Proper connection cleanup with context managers
- Connection health monitoring
- Backward compatibility with existing LegalFileManagerDB class
"""

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, cast

import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json, RealDictCursor

# Use structured logging
from app.utils.logging_config import get_logger, log_database_operation, log_performance_metric

# Import entity models
from ..models.entities import MigrationJob, TerraformJob


class ConnectionPoolManager:
    """
    Manages a secure ThreadedConnectionPool with health monitoring and retry logic.
    """

    def __init__(
        self,
        connection_params: Dict[str, Any],
        min_connections: int = 2,
        max_connections: int = 20,
        connection_timeout: int = 30,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the connection pool manager.

        Args:
            connection_params: Database connection parameters
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections in pool
            connection_timeout: Connection timeout in seconds
            retry_attempts: Number of retry attempts for failed operations
            retry_delay: Delay between retry attempts in seconds
        """
        self.connection_params = connection_params.copy()
        self.connection_params["connect_timeout"] = connection_timeout
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self._pool = None
        self._pool_lock = threading.Lock()
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = None
        self._failed_connections = 0
        self._total_connections = 0
        self.logger = get_logger("database.pool")

        # Initialize the connection pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool with error handling."""
        try:
            with self._pool_lock:
                if self._pool is not None:
                    self._pool.closeall()

                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=self.min_connections, maxconn=self.max_connections, **self.connection_params
                )
                self.logger.info(
                    "Connection pool initialized successfully",
                    extra={
                        "event": "pool_initialized",
                        "min_connections": self.min_connections,
                        "max_connections": self.max_connections,
                    },
                )

        except Exception as e:
            self.logger.error(
                "Failed to initialize connection pool",
                extra={"event": "pool_init_failed", "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            raise

    def _is_connection_healthy(self, conn) -> bool:
        """Check if a connection is healthy by executing a simple query."""
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception as e:
            self.logger.warning(
                "Connection health check failed",
                extra={"event": "health_check_failed", "error": str(e), "error_type": type(e).__name__},
            )
            return False

    def _perform_health_check(self):
        """Perform periodic health check on the connection pool."""
        current_time = datetime.now()

        if self._last_health_check is None or current_time - self._last_health_check > timedelta(
            seconds=self._health_check_interval
        ):
            self.logger.debug("Performing connection pool health check", extra={"event": "health_check_start"})
            self._last_health_check = current_time

            # Test a connection from the pool
            try:
                conn = self.get_connection()
                if conn:
                    if not self._is_connection_healthy(conn):
                        self.logger.warning(
                            "Unhealthy connection detected, reinitializing pool",
                            extra={"event": "pool_reinit_unhealthy"},
                        )
                        self._initialize_pool()
                    self.return_connection(conn)
            except Exception as e:
                self.logger.error(
                    "Health check failed",
                    extra={"event": "health_check_error", "error": str(e), "error_type": type(e).__name__},
                    exc_info=True,
                )
                self._initialize_pool()

    def get_connection(self):
        """
        Get a connection from the pool with retry logic.

        Returns:
            Database connection or None if all attempts fail
        """
        self._perform_health_check()

        for attempt in range(self.retry_attempts):
            try:
                with self._pool_lock:
                    if self._pool is None:
                        self._initialize_pool()

                    conn = self._pool.getconn()
                    if conn:
                        self._total_connections += 1
                        return conn

            except Exception as e:
                self._failed_connections += 1
                self.logger.warning(
                    "Connection attempt failed",
                    extra={
                        "event": "connection_attempt_failed",
                        "attempt": attempt + 1,
                        "max_attempts": self.retry_attempts,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    self.logger.error(
                        "All connection attempts failed",
                        extra={
                            "event": "all_connection_attempts_failed",
                            "attempts": self.retry_attempts,
                            "failed_connections": self._failed_connections,
                        },
                    )

        return None

    def return_connection(self, conn):
        """Return a connection to the pool."""
        try:
            with self._pool_lock:
                if self._pool and conn:
                    self._pool.putconn(conn)
        except Exception as e:
            self.logger.error(
                "Failed to return connection to pool",
                extra={"event": "connection_return_failed", "error": str(e), "error_type": type(e).__name__},
            )

    def close_all_connections(self):
        """Close all connections in the pool."""
        try:
            with self._pool_lock:
                if self._pool:
                    self._pool.closeall()
                    self.logger.info("All connections closed", extra={"event": "all_connections_closed"})
        except Exception as e:
            self.logger.error(
                "Error closing connections",
                extra={"event": "connection_close_error", "error": str(e), "error_type": type(e).__name__},
            )

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "total_connections_created": self._total_connections,
            "failed_connections": self._failed_connections,
            "last_health_check": self._last_health_check,
            "pool_initialized": self._pool is not None,
        }


class DatabaseConnection:
    """
    Enhanced database connection class with connection pooling and health monitoring.
    """

    def __init__(
        self,
        host="localhost",
        port=5432,
        database="legal_case_manager",
        user="postgres",
        password="postgres",
        min_connections=2,
        max_connections=20,
        connection_timeout=30,
    ):
        """
        Initialize database connection with connection pooling.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            connection_timeout: Connection timeout in seconds
        """
        self.connection_params = {"host": host, "port": port, "database": database, "user": user, "password": password}

        # Initialize connection pool manager
        self.pool_manager = ConnectionPoolManager(
            connection_params=self.connection_params,
            min_connections=min_connections,
            max_connections=max_connections,
            connection_timeout=connection_timeout,
        )

        self.logger = get_logger("database.connection")
        self.logger.info(
            "DatabaseConnection initialized",
            extra={
                "event": "db_connection_init",
                "database": database,
                "host": host,
                "port": port,
                "min_connections": min_connections,
                "max_connections": max_connections,
            },
        )

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting and properly cleaning up database connections.

        Yields:
            Database connection with automatic cleanup
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            if conn is None:
                raise psycopg2.OperationalError("Failed to get connection from pool")
            yield conn
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if conn:
                try:
                    self.pool_manager.return_connection(conn)
                except Exception as e:
                    self.logger.error(
                        "Error returning connection to pool",
                        extra={"event": "connection_cleanup_error", "error": str(e), "error_type": type(e).__name__},
                    )

    def execute_query(
        self, query: str, params: Optional[Union[tuple, dict]] = None, fetch_one: bool = False, fetch_all: bool = True
    ) -> Any:
        """
        Execute a query with connection pooling and proper error handling.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Return single row
            fetch_all: Return all rows

        Returns:
            Query results based on fetch parameters
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)

                    if fetch_one:
                        result = cursor.fetchone()
                    elif fetch_all:
                        result = cursor.fetchall()
                    else:
                        result = None

                    conn.commit()
                    return result

            except psycopg2.Error as e:
                conn.rollback()
                self.logger.error(
                    "Database query error",
                    extra={
                        "event": "query_error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "query": query[:200] + "..." if len(query) > 200 else query,
                        "params_provided": params is not None,
                    },
                    exc_info=True,
                )
                raise

    def execute_many(self, query: str, params_list: List[Union[tuple, dict]]) -> None:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query to execute
            params_list: List of parameter sets
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()

            except psycopg2.Error as e:
                conn.rollback()
                self.logger.error(
                    "Database executemany error",
                    extra={
                        "event": "executemany_error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "query": query[:200] + "..." if len(query) > 200 else query,
                        "batch_size": len(params_list),
                    },
                    exc_info=True,
                )
                raise

    def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """
        Execute multiple operations in a single transaction.

        Args:
            operations: List of operations with 'query', 'params', and optional 'fetch' keys

        Returns:
            True if transaction succeeded, False otherwise
        """
        with self.get_connection() as conn:
            try:
                results = []
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    for operation in operations:
                        query = operation["query"]
                        params = operation.get("params")
                        fetch = operation.get("fetch", False)

                        cursor.execute(query, params)

                        if fetch == "one":
                            results.append(cursor.fetchone())
                        elif fetch == "all":
                            results.append(cursor.fetchall())
                        else:
                            results.append(None)

                conn.commit()
                return True

            except psycopg2.Error as e:
                conn.rollback()
                self.logger.error(
                    "Transaction failed",
                    extra={
                        "event": "transaction_failed",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "operations_count": len(operations),
                    },
                    exc_info=True,
                )
                return False

    def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            self.logger.error(
                "Connection test failed",
                extra={"event": "connection_test_failed", "error": str(e), "error_type": type(e).__name__},
            )
            return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self.pool_manager.get_pool_stats()

    def close_all_connections(self):
        """Close all connections in the pool."""
        self.pool_manager.close_all_connections()


class LegalFileManagerDB:
    """
    Legal File Manager database operations with enhanced connection pooling.
    Maintains backward compatibility with the existing interface.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize with a DatabaseConnection instance.

        Args:
            db_connection: DatabaseConnection instance with connection pooling
        """
        self.db = db_connection
        self.logger = get_logger("database.manager")
        self.logger.info("LegalFileManagerDB initialized with connection pooling", extra={"event": "db_manager_init"})

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
        return cast(List[Dict[str, Any]], self.db.execute_query(query))

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
        params = (
            search_query,
            search_query,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            limit,
        )
        return cast(List[Dict[str, Any]], self.db.execute_query(query, params))

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
        params = (
            search_query,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            limit,
        )
        return cast(List[Dict[str, Any]], self.db.execute_query(query, params))

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
        params = (
            search_query,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            search_param,
            limit,
        )
        return cast(List[Dict[str, Any]], self.db.execute_query(query, params))

    def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID"""
        query = "SELECT * FROM clients WHERE client_id = %s"
        return cast(Optional[Dict[str, Any]], self.db.execute_query(query, (client_id,), fetch_one=True))

    def update_client(self, client_id: str, client_data: Dict[str, Any]) -> None:
        """Update a client"""
        set_clause = ", ".join([f"{key} = %({key})s" for key in client_data.keys()])
        query = f"UPDATE clients SET {set_clause} WHERE client_id = %(client_id)s"
        client_data["client_id"] = client_id
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
        return cast(List[Dict[str, Any]], self.db.execute_query(query))

    def get_cases_by_client(self, client_id: str) -> List[Dict[str, Any]]:
        """Get cases for a specific client"""
        query = "SELECT * FROM cases WHERE client_id = %s ORDER BY created_date DESC"
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (client_id,)))

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get a case by ID"""
        query = "SELECT * FROM cases WHERE case_id = %s"
        return cast(Optional[Dict[str, Any]], self.db.execute_query(query, (case_id,), fetch_one=True))

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
        return cast(List[Dict[str, Any]], self.db.execute_query(query))

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
        return cast(Optional[Dict[str, Any]], self.db.execute_query(query, (file_id,), fetch_one=True))

    def search_files(
        self, search_query: str = "", filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
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
        params = [search_query or ""]  # First param for relevance calculation
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
            if filters.get("case_type"):
                conditions.append("AND c.case_type = %s")
                params.append(filters["case_type"])

            if filters.get("file_type"):
                conditions.append("AND f.file_type = %s")
                params.append(filters["file_type"])

            if filters.get("confidentiality_level"):
                conditions.append("AND f.confidentiality_level = %s")
                params.append(filters["confidentiality_level"])

            if filters.get("warehouse_location"):
                conditions.append("AND f.warehouse_location = %s")
                params.append(filters["warehouse_location"])

            if filters.get("storage_status"):
                conditions.append("AND f.storage_status = %s")
                params.append(filters["storage_status"])

        # Order by relevance first, then by recency
        order_clause = " ORDER BY relevance_score DESC, f.last_accessed DESC NULLS LAST, f.created_date DESC"
        limit_clause = f" LIMIT {limit}"

        query = base_query + " ".join(conditions) + order_clause + limit_clause
        return cast(List[Dict[str, Any]], self.db.execute_query(query, tuple(params) if params else None))

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
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (client_id,)))

    def get_payments_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """Get payments for a specific case"""
        query = "SELECT * FROM payments WHERE case_id = %s ORDER BY payment_date DESC"
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (case_id,)))

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
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (limit,)))

    def get_file_access_history(self, file_id: str) -> List[Dict[str, Any]]:
        """Get access history for a specific file"""
        query = "SELECT * FROM file_accesses WHERE file_id = %s ORDER BY access_timestamp DESC"
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (file_id,)))

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
        query = (
            "SELECT * FROM user_comments WHERE entity_type = 'file' AND entity_id = %s ORDER BY created_timestamp DESC"
        )
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (file_id,)))

    def get_comments_by_entity(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Get comments for a specific entity"""
        query = "SELECT * FROM user_comments WHERE entity_type = %s AND entity_id = %s ORDER BY created_timestamp DESC"
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (entity_type, entity_id)))

    # Analytics methods
    def add_recent_search(self, search_query: str, user_session: Optional[str] = None) -> None:
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
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (limit,)))

    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent searches"""
        query = "SELECT search_query, MAX(search_date) as latest_date FROM recent_searches GROUP BY search_query ORDER BY latest_date DESC LIMIT %s"
        return cast(List[Dict[str, Any]], self.db.execute_query(query, (limit,)))

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
        case_types = [row["case_type"] for row in self.db.execute_query(case_types_query)]
        options["case_types"] = case_types

        # File types
        file_types_query = (
            "SELECT DISTINCT file_type FROM physical_files WHERE file_type IS NOT NULL ORDER BY file_type"
        )
        file_types = [row["file_type"] for row in self.db.execute_query(file_types_query)]
        options["file_types"] = file_types

        # Confidentiality levels
        conf_query = "SELECT DISTINCT confidentiality_level FROM physical_files WHERE confidentiality_level IS NOT NULL ORDER BY confidentiality_level"
        conf_levels = [row["confidentiality_level"] for row in self.db.execute_query(conf_query)]
        options["confidentiality_levels"] = conf_levels

        # Warehouse locations
        warehouse_query = "SELECT DISTINCT warehouse_location FROM physical_files WHERE warehouse_location IS NOT NULL ORDER BY warehouse_location"
        warehouses = [row["warehouse_location"] for row in self.db.execute_query(warehouse_query)]
        options["warehouse_locations"] = warehouses

        # Storage statuses
        status_query = "SELECT DISTINCT storage_status FROM physical_files WHERE storage_status IS NOT NULL ORDER BY storage_status"
        statuses = [row["storage_status"] for row in self.db.execute_query(status_query)]
        options["storage_statuses"] = statuses

        return options

    def get_file_access_stats(self, file_id: str) -> Dict[str, Any]:
        """Get access statistics for a specific file (matching original app)"""
        accesses = self.get_file_access_history(file_id)

        if not accesses:
            return {
                "total_accesses": 0,
                "unique_users": 0,
                "last_accessed": None,
                "most_frequent_user": None,
                "access_types": {},
                "user_access_counts": {},
            }

        # Calculate statistics
        unique_users = len(set(access["user_name"] for access in accesses))
        last_access = max(accesses, key=lambda x: x["access_timestamp"])

        # Count access types and user accesses
        access_type_counts: Dict[str, int] = {}
        user_access_counts: Dict[str, int] = {}

        for access in accesses:
            access_type = access["access_type"]
            user_name = access["user_name"]

            access_type_counts[access_type] = access_type_counts.get(access_type, 0) + 1
            user_access_counts[user_name] = user_access_counts.get(user_name, 0) + 1

        most_frequent_user = max(user_access_counts.items(), key=lambda x: x[1])[0] if user_access_counts else None

        return {
            "total_accesses": len(accesses),
            "unique_users": unique_users,
            "last_accessed": last_access,
            "most_frequent_user": most_frequent_user,
            "access_types": access_type_counts,
            "user_access_counts": user_access_counts,
        }

    # Job persistence methods
    def save_terraform_job(self, job: "TerraformJob") -> bool:
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
                job.errors,
            )

            self.db.execute_query(query, params, fetch_all=False)
            return True

        except Exception as e:
            self.logger.error(
                "Error saving terraform job",
                extra={
                    "event": "terraform_job_save_error",
                    "job_id": job.job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return False

    def get_terraform_job(self, job_id: str) -> Optional["TerraformJob"]:
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
                    job_id=result["job_id"],
                    source_db_type=result["source_db_type"],
                    target_cloud=result["target_cloud"],
                    source_connection=result["source_connection"],
                    target_tables=result["target_tables"],
                    status=result["status"],
                    progress=float(result["progress"]),
                    created_at=result["created_at"],
                    completed_at=result["completed_at"],
                    terraform_config=result["terraform_config"] if result["terraform_config"] else None,
                    field_mappings=result["field_mappings"] if result["field_mappings"] else None,
                    ai_analysis=result["ai_analysis"] if result["ai_analysis"] else None,
                    estimated_cost=result["estimated_cost"] if result["estimated_cost"] else None,
                    errors=result["errors"],
                )
            return None

        except Exception as e:
            self.logger.error(
                "Error getting terraform job",
                extra={
                    "event": "terraform_job_get_error",
                    "job_id": job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    def get_all_terraform_jobs(self) -> List["TerraformJob"]:
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
                        job_id=result["job_id"],
                        source_db_type=result["source_db_type"],
                        target_cloud=result["target_cloud"],
                        source_connection=result["source_connection"],
                        target_tables=result["target_tables"],
                        status=result["status"],
                        progress=float(result["progress"]),
                        created_at=result["created_at"],
                        completed_at=result["completed_at"],
                        terraform_config=result["terraform_config"] if result["terraform_config"] else None,
                        field_mappings=result["field_mappings"] if result["field_mappings"] else None,
                        ai_analysis=result["ai_analysis"] if result["ai_analysis"] else None,
                        estimated_cost=result["estimated_cost"] if result["estimated_cost"] else None,
                        errors=result["errors"],
                    )
                    jobs.append(job)

            return jobs

        except Exception as e:
            self.logger.error(
                "Error getting terraform jobs",
                extra={"event": "terraform_jobs_get_error", "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            return []

    def save_migration_job(self, job: "MigrationJob") -> bool:
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
                job.errors,
            )

            self.db.execute_query(query, params, fetch_all=False)
            return True

        except Exception as e:
            self.logger.error(
                "Error saving migration job",
                extra={
                    "event": "migration_job_save_error",
                    "job_id": job.job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return False

    def get_migration_job(self, job_id: str) -> Optional["MigrationJob"]:
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
                    job_id=result["job_id"],
                    source_db_type=result["source_db_type"],
                    source_connection=result["source_connection"],
                    target_tables=result["target_tables"],
                    status=result["status"],
                    progress=float(result["progress"]),
                    created_at=result["created_at"],
                    completed_at=result["completed_at"],
                    table_count=result["table_count"],
                    total_records=result["total_records"],
                    migrated_records=result["migrated_records"],
                    errors=result["errors"],
                )
            return None

        except Exception as e:
            self.logger.error(
                "Error getting migration job",
                extra={
                    "event": "migration_job_get_error",
                    "job_id": job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    def get_all_migration_jobs(self) -> List["MigrationJob"]:
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
                        job_id=result["job_id"],
                        source_db_type=result["source_db_type"],
                        source_connection=result["source_connection"],
                        target_tables=result["target_tables"],
                        status=result["status"],
                        progress=float(result["progress"]),
                        created_at=result["created_at"],
                        completed_at=result["completed_at"],
                        table_count=result["table_count"],
                        total_records=result["total_records"],
                        migrated_records=result["migrated_records"],
                        errors=result["errors"],
                    )
                    jobs.append(job)

            return jobs

        except Exception as e:
            self.logger.error(
                "Error getting migration jobs",
                extra={"event": "migration_jobs_get_error", "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            return []

    def delete_terraform_job(self, job_id: str) -> bool:
        """Delete a terraform job"""
        try:
            query = "DELETE FROM terraform_jobs WHERE job_id = %s"
            self.db.execute_query(query, (job_id,), fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(
                "Error deleting terraform job",
                extra={
                    "event": "terraform_job_delete_error",
                    "job_id": job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return False

    def delete_migration_job(self, job_id: str) -> bool:
        """Delete a migration job"""
        try:
            query = "DELETE FROM migration_jobs WHERE job_id = %s"
            self.db.execute_query(query, (job_id,), fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(
                "Error deleting migration job",
                extra={
                    "event": "migration_job_delete_error",
                    "job_id": job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return False

    # Enhanced methods for connection pool management
    def test_database_connection(self) -> bool:
        """Test database connectivity."""
        return self.db.test_connection()

    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self.db.get_connection_stats()

    def close_all_connections(self):
        """Close all connections in the pool."""
        self.db.close_all_connections()


# Convenience function for creating database connection from config
def create_database_connection(config_class=None, **kwargs) -> DatabaseConnection:
    """
    Create a DatabaseConnection instance from configuration.

    Args:
        config_class: Configuration class with database settings
        **kwargs: Override parameters

    Returns:
        DatabaseConnection instance with connection pooling
    """
    if config_class:
        db_config = config_class.get_database_config()
        db_config.update(kwargs)
    else:
        db_config = kwargs

    return DatabaseConnection(**db_config)


# Convenience function for creating LegalFileManagerDB
def create_legal_db(config_class=None, **kwargs) -> LegalFileManagerDB:
    """
    Create a LegalFileManagerDB instance from configuration.

    Args:
        config_class: Configuration class with database settings
        **kwargs: Override parameters

    Returns:
        LegalFileManagerDB instance with connection pooling
    """
    db_connection = create_database_connection(config_class, **kwargs)
    return LegalFileManagerDB(db_connection)
