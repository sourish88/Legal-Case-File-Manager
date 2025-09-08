#!/usr/bin/env python3
"""
Performance Index Optimization Script
Adds missing indexes to improve search performance, especially for client name searches.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
from config import Config

class PerformanceIndexOptimizer:
    def __init__(self):
        try:
            Config.validate_config()
            self.connection_params = Config.get_database_config()
            print(f"Connecting to database: {self.connection_params['database']} on {self.connection_params['host']}")
        except ValueError as e:
            print(f"Configuration error: {e}")
            print("Please check your environment variables or .env file")
            sys.exit(1)
    
    def get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(**self.connection_params)
    
    def check_existing_indexes(self):
        """Check which indexes already exist"""
        query = """
        SELECT indexname, tablename, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND (tablename = 'clients' OR tablename = 'physical_files' OR tablename = 'cases')
        ORDER BY tablename, indexname;
        """
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            indexes = cursor.fetchall()
            
            print("EXISTING INDEXES:")
            print("-" * 60)
            current_table = None
            for idx in indexes:
                if idx['tablename'] != current_table:
                    current_table = idx['tablename']
                    print(f"\n{current_table.upper()} table:")
                print(f"  {idx['indexname']}: {idx['indexdef']}")
            
            cursor.close()
            conn.close()
            return indexes
            
        except psycopg2.Error as e:
            print(f"Error checking existing indexes: {e}")
            return []
    
    def add_performance_indexes(self):
        """Add indexes to improve search performance"""
        
        # Define the performance optimization indexes
        performance_indexes = [
            # Client name indexes for faster name searches
            ("idx_clients_first_name", 
             "CREATE INDEX IF NOT EXISTS idx_clients_first_name ON clients(first_name);",
             "Index on client first names for faster name searches"),
            
            ("idx_clients_last_name", 
             "CREATE INDEX IF NOT EXISTS idx_clients_last_name ON clients(last_name);",
             "Index on client last names for faster name searches"),
            
            # Pattern matching optimization for ILIKE queries
            ("idx_clients_first_name_pattern", 
             "CREATE INDEX IF NOT EXISTS idx_clients_first_name_pattern ON clients(first_name varchar_pattern_ops);",
             "Optimized index for ILIKE pattern matching on first names"),
            
            ("idx_clients_last_name_pattern", 
             "CREATE INDEX IF NOT EXISTS idx_clients_last_name_pattern ON clients(last_name varchar_pattern_ops);",
             "Optimized index for ILIKE pattern matching on last names"),
            
            # Composite index for full name searches
            ("idx_clients_full_name", 
             "CREATE INDEX IF NOT EXISTS idx_clients_full_name ON clients(first_name, last_name);",
             "Composite index for full name searches"),
            
            # File description index for better file searches
            ("idx_files_description", 
             "CREATE INDEX IF NOT EXISTS idx_files_description ON physical_files(file_description);",
             "Index on file descriptions for faster file content searches"),
            
            # Case type pattern matching (since we use ILIKE not exact match)
            ("idx_cases_type_pattern", 
             "CREATE INDEX IF NOT EXISTS idx_cases_type_pattern ON cases(case_type varchar_pattern_ops);",
             "Optimized index for ILIKE pattern matching on case types"),
            
            # Full-text search index for advanced name searching
            ("idx_clients_fulltext", 
             "CREATE INDEX IF NOT EXISTS idx_clients_fulltext ON clients USING gin(to_tsvector('english', coalesce(first_name, '') || ' ' || coalesce(last_name, '')));",
             "Full-text search index for advanced client name searching"),
        ]
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print("\nADDING PERFORMANCE INDEXES:")
            print("=" * 60)
            
            for index_name, create_sql, description in performance_indexes:
                try:
                    print(f"\nCreating {index_name}...")
                    print(f"Description: {description}")
                    print(f"SQL: {create_sql}")
                    
                    cursor.execute(create_sql)
                    print(f"[SUCCESS] Successfully created {index_name}")
                    
                except psycopg2.Error as e:
                    if "already exists" in str(e):
                        print(f"[INFO] Index {index_name} already exists")
                    else:
                        print(f"[ERROR] Error creating {index_name}: {e}")
            
            conn.commit()
            print(f"\n[SUCCESS] Performance optimization completed!")
            print("These indexes will significantly improve search performance for client names.")
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            print(f"❌ Database error: {e}")
            sys.exit(1)
    
    def analyze_index_usage(self):
        """Analyze index usage statistics"""
        query = """
        SELECT 
            schemaname,
            relname as tablename,
            indexrelname as indexname,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes 
        WHERE schemaname = 'public'
        AND (relname = 'clients' OR relname = 'physical_files' OR relname = 'cases')
        ORDER BY idx_tup_read DESC;
        """
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            stats = cursor.fetchall()
            
            print("\nINDEX USAGE STATISTICS:")
            print("-" * 60)
            print(f"{'Index Name':<35} {'Tuples Read':<12} {'Tuples Fetched':<15}")
            print("-" * 60)
            
            for stat in stats:
                print(f"{stat['indexname']:<35} {stat['idx_tup_read']:<12} {stat['idx_tup_fetch']:<15}")
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            print(f"Error analyzing index usage: {e}")
    
    def run_optimization(self):
        """Run the complete optimization process"""
        print("LEGAL CASE FILE MANAGER - PERFORMANCE OPTIMIZATION")
        print("=" * 60)
        
        # Check existing indexes
        self.check_existing_indexes()
        
        # Add performance indexes
        self.add_performance_indexes()
        
        # Show index usage statistics
        self.analyze_index_usage()
        
        print("\n" + "=" * 60)
        print("OPTIMIZATION COMPLETE!")
        print("Name searches should now be significantly faster.")
        print("You can test the performance improvement by searching for client names.")

def main():
    optimizer = PerformanceIndexOptimizer()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            print("Checking existing indexes only...")
            optimizer.check_existing_indexes()
        elif sys.argv[1] == "--stats":
            print("Showing index usage statistics...")
            optimizer.analyze_index_usage()
        else:
            print("Usage: python add_performance_indexes.py [--check|--stats]")
            print("  (no arguments): Run full optimization")
            print("  --check: Check existing indexes only")
            print("  --stats: Show index usage statistics")
    else:
        optimizer.run_optimization()

if __name__ == "__main__":
    main()
