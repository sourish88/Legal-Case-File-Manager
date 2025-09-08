import json
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor


class PostgreSQLSetup:
    def __init__(
        self, host="localhost", port=5432, database="legal_case_manager", user="postgres", password="postgres"
    ):
        self.connection_params = {"host": host, "port": port, "database": database, "user": user, "password": password}

    def create_database_if_not_exists(self):
        """Create the database if it doesn't exist"""
        # Connect to default postgres database first
        temp_params = self.connection_params.copy()
        temp_params["database"] = "postgres"

        try:
            conn = psycopg2.connect(**temp_params)
            conn.autocommit = True
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.connection_params["database"],))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(f"CREATE DATABASE {self.connection_params['database']}")
                print(f"Database '{self.connection_params['database']}' created successfully")
            else:
                print(f"Database '{self.connection_params['database']}' already exists")

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            print(f"Error creating database: {e}")
            raise

    def drop_existing_triggers(self):
        """Drop existing triggers to avoid conflicts"""
        drop_triggers_sql = """
        DROP TRIGGER IF EXISTS update_clients_updated_at ON clients;
        DROP TRIGGER IF EXISTS update_cases_updated_at ON cases;
        DROP TRIGGER IF EXISTS update_files_updated_at ON physical_files;
        DROP TRIGGER IF EXISTS update_payments_updated_at ON payments;
        DROP TRIGGER IF EXISTS update_comments_updated_at ON user_comments;
        DROP TRIGGER IF EXISTS update_terraform_jobs_updated_at ON terraform_jobs;
        DROP TRIGGER IF EXISTS update_migration_jobs_updated_at ON migration_jobs;
        """

        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            cursor.execute(drop_triggers_sql)
            conn.commit()
            print("Existing triggers dropped successfully")
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            print(f"Note: Some triggers may not have existed: {e}")
            # This is not a critical error, continue

    def drop_existing_tables(self):
        """Drop existing tables to recreate with new schema"""
        drop_tables_sql = """
        DROP TABLE IF EXISTS terraform_jobs CASCADE;
        DROP TABLE IF EXISTS migration_jobs CASCADE;
        DROP TABLE IF EXISTS file_accesses CASCADE;
        DROP TABLE IF EXISTS user_comments CASCADE;
        DROP TABLE IF EXISTS payments CASCADE;
        DROP TABLE IF EXISTS physical_files CASCADE;
        DROP TABLE IF EXISTS cases CASCADE;
        DROP TABLE IF EXISTS clients CASCADE;
        DROP TABLE IF EXISTS recent_searches CASCADE;
        DROP TABLE IF EXISTS popular_searches CASCADE;
        """

        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            cursor.execute(drop_tables_sql)
            conn.commit()
            print("Existing tables dropped successfully")
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            print(f"Note: Some tables may not have existed: {e}")

    def create_tables(self):
        """Create all necessary tables"""

        create_tables_sql = """
        -- Clients table
        CREATE TABLE IF NOT EXISTS clients (
            client_id VARCHAR(20) PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(50),
            address TEXT,
            date_of_birth DATE,
            client_type VARCHAR(20) CHECK (client_type IN ('Individual', 'Corporation', 'Non-Profit')),
            registration_date DATE NOT NULL,
            status VARCHAR(20) CHECK (status IN ('Active', 'Inactive', 'Suspended')) DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Cases table
        CREATE TABLE IF NOT EXISTS cases (
            case_id VARCHAR(20) PRIMARY KEY,
            reference_number VARCHAR(50) UNIQUE NOT NULL,
            client_id VARCHAR(20) NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
            case_type VARCHAR(50) NOT NULL,
            case_status VARCHAR(20) CHECK (case_status IN ('Open', 'Closed', 'On Hold', 'Under Review', 'Settled')) DEFAULT 'Open',
            created_date DATE NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_lawyer VARCHAR(100),
            priority VARCHAR(20) CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')) DEFAULT 'Medium',
            estimated_value DECIMAL(15,2),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Physical Files table
        CREATE TABLE IF NOT EXISTS physical_files (
            file_id VARCHAR(20) PRIMARY KEY,
            reference_number VARCHAR(50) UNIQUE NOT NULL,
            case_id VARCHAR(20) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
            client_id VARCHAR(20) NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
            file_type VARCHAR(50),
            document_category VARCHAR(50),
            warehouse_location VARCHAR(50),
            shelf_number VARCHAR(20),
            box_number VARCHAR(20),
            file_size VARCHAR(50),
            created_date DATE NOT NULL,
            last_accessed TIMESTAMP,
            last_modified TIMESTAMP,
            storage_status VARCHAR(30) DEFAULT 'Active',
            confidentiality_level VARCHAR(30) CHECK (confidentiality_level IN ('Public', 'Internal', 'Confidential', 'Highly Confidential')),
            keywords TEXT[], -- PostgreSQL array for keywords
            file_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Payments table
        CREATE TABLE IF NOT EXISTS payments (
            payment_id VARCHAR(20) PRIMARY KEY,
            client_id VARCHAR(20) NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
            case_id VARCHAR(20) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
            amount DECIMAL(15,2) NOT NULL,
            payment_date DATE NOT NULL,
            payment_method VARCHAR(50),
            status VARCHAR(20) CHECK (status IN ('Paid', 'Pending', 'Overdue')) DEFAULT 'Pending',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- File Access History table
        CREATE TABLE IF NOT EXISTS file_accesses (
            access_id VARCHAR(20) PRIMARY KEY,
            file_id VARCHAR(20) NOT NULL REFERENCES physical_files(file_id) ON DELETE CASCADE,
            user_name VARCHAR(100) NOT NULL,
            user_role VARCHAR(50),
            access_timestamp TIMESTAMP NOT NULL,
            access_type VARCHAR(20) DEFAULT 'view',
            ip_address VARCHAR(45),
            user_agent TEXT,
            session_duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- User Comments table
        CREATE TABLE IF NOT EXISTS user_comments (
            comment_id VARCHAR(20) PRIMARY KEY,
            entity_type VARCHAR(20) NOT NULL,
            entity_id VARCHAR(20) NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            user_role VARCHAR(50),
            comment_text TEXT NOT NULL,
            created_timestamp TIMESTAMP NOT NULL,
            is_private BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Search Analytics tables
        CREATE TABLE IF NOT EXISTS recent_searches (
            id SERIAL PRIMARY KEY,
            search_query TEXT NOT NULL,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_session VARCHAR(100)
        );

        CREATE TABLE IF NOT EXISTS popular_searches (
            search_query TEXT PRIMARY KEY,
            search_count INTEGER DEFAULT 1,
            last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);
        CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
        CREATE INDEX IF NOT EXISTS idx_clients_type ON clients(client_type);

        -- Performance indexes for client name searches
        CREATE INDEX IF NOT EXISTS idx_clients_first_name ON clients(first_name);
        CREATE INDEX IF NOT EXISTS idx_clients_last_name ON clients(last_name);
        CREATE INDEX IF NOT EXISTS idx_clients_first_name_pattern ON clients(first_name varchar_pattern_ops);
        CREATE INDEX IF NOT EXISTS idx_clients_last_name_pattern ON clients(last_name varchar_pattern_ops);
        CREATE INDEX IF NOT EXISTS idx_clients_full_name ON clients(first_name, last_name);
        CREATE INDEX IF NOT EXISTS idx_clients_fulltext ON clients USING gin(to_tsvector('english', coalesce(first_name, '') || ' ' || coalesce(last_name, '')));

        CREATE INDEX IF NOT EXISTS idx_cases_client_id ON cases(client_id);
        CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(case_status);
        CREATE INDEX IF NOT EXISTS idx_cases_type ON cases(case_type);
        CREATE INDEX IF NOT EXISTS idx_cases_reference ON cases(reference_number);
        CREATE INDEX IF NOT EXISTS idx_cases_type_pattern ON cases(case_type varchar_pattern_ops);

        CREATE INDEX IF NOT EXISTS idx_files_case_id ON physical_files(case_id);
        CREATE INDEX IF NOT EXISTS idx_files_client_id ON physical_files(client_id);
        CREATE INDEX IF NOT EXISTS idx_files_warehouse ON physical_files(warehouse_location);
        CREATE INDEX IF NOT EXISTS idx_files_reference ON physical_files(reference_number);
        CREATE INDEX IF NOT EXISTS idx_files_keywords ON physical_files USING GIN(keywords);
        CREATE INDEX IF NOT EXISTS idx_files_description ON physical_files(file_description);

        CREATE INDEX IF NOT EXISTS idx_payments_client_id ON payments(client_id);
        CREATE INDEX IF NOT EXISTS idx_payments_case_id ON payments(case_id);
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
        CREATE INDEX IF NOT EXISTS idx_file_accesses_file_id ON file_accesses(file_id);
        CREATE INDEX IF NOT EXISTS idx_file_accesses_timestamp ON file_accesses(access_timestamp);
        CREATE INDEX IF NOT EXISTS idx_comments_entity ON user_comments(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_recent_searches_date ON recent_searches(search_date);

        -- Terraform Jobs table for data pipeline generation
        CREATE TABLE IF NOT EXISTS terraform_jobs (
            job_id VARCHAR(50) PRIMARY KEY,
            source_db_type VARCHAR(20) NOT NULL,
            target_cloud VARCHAR(20) NOT NULL,
            source_connection TEXT NOT NULL,
            target_tables TEXT[] NOT NULL, -- PostgreSQL array for table names
            status VARCHAR(20) CHECK (status IN ('pending', 'analyzing', 'generating', 'running', 'completed', 'failed')) DEFAULT 'pending',
            progress DECIMAL(5,2) DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            terraform_config JSONB NULL, -- Store terraform configuration as JSON
            field_mappings JSONB NULL, -- Store field mappings as JSON
            ai_analysis JSONB NULL, -- Store AI analysis results as JSON
            estimated_cost JSONB NULL, -- Store cost estimation as JSON
            errors TEXT[] NULL, -- Store error messages as array
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Migration Jobs table for data migration tracking
        CREATE TABLE IF NOT EXISTS migration_jobs (
            job_id VARCHAR(50) PRIMARY KEY,
            source_db_type VARCHAR(20) NOT NULL,
            source_connection TEXT NOT NULL,
            target_tables TEXT[] NOT NULL, -- PostgreSQL array for table names
            status VARCHAR(20) CHECK (status IN ('pending', 'analyzing', 'generating', 'running', 'completed', 'failed')) DEFAULT 'pending',
            progress DECIMAL(5,2) DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            table_count INTEGER DEFAULT 0,
            total_records INTEGER DEFAULT 0,
            migrated_records INTEGER DEFAULT 0,
            errors TEXT[] NULL, -- Store error messages as array
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for job tables for better performance
        CREATE INDEX IF NOT EXISTS idx_terraform_jobs_status ON terraform_jobs(status);
        CREATE INDEX IF NOT EXISTS idx_terraform_jobs_created_at ON terraform_jobs(created_at);
        CREATE INDEX IF NOT EXISTS idx_terraform_jobs_source_db ON terraform_jobs(source_db_type);
        CREATE INDEX IF NOT EXISTS idx_terraform_jobs_target_cloud ON terraform_jobs(target_cloud);

        CREATE INDEX IF NOT EXISTS idx_migration_jobs_status ON migration_jobs(status);
        CREATE INDEX IF NOT EXISTS idx_migration_jobs_created_at ON migration_jobs(created_at);
        CREATE INDEX IF NOT EXISTS idx_migration_jobs_source_db ON migration_jobs(source_db_type);
        """

        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            cursor.execute(create_tables_sql)
            conn.commit()
            print("All tables and indexes created successfully (including job persistence tables)")
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            print(f"Error creating tables: {e}")
            raise

    def create_triggers(self):
        """Create triggers separately with proper error handling"""

        trigger_function_sql = """
        -- Create function for updating timestamps
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """

        triggers = [
            "CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_files_updated_at BEFORE UPDATE ON physical_files FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON user_comments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_terraform_jobs_updated_at BEFORE UPDATE ON terraform_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            "CREATE TRIGGER update_migration_jobs_updated_at BEFORE UPDATE ON migration_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
        ]

        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()

            # Create the function first
            cursor.execute(trigger_function_sql)

            # Create each trigger individually
            for trigger in triggers:
                try:
                    cursor.execute(trigger)
                    print(f"Trigger created: {trigger.split()[2]}")
                except psycopg2.Error as e:
                    if "already exists" in str(e):
                        print(f"Trigger already exists: {trigger.split()[2]}")
                    else:
                        print(f"Error creating trigger: {e}")

            conn.commit()
            cursor.close()
            conn.close()
            print("Trigger setup completed")

        except psycopg2.Error as e:
            print(f"Error setting up triggers: {e}")
            # Don't raise - triggers are not critical for basic functionality

    def setup_database(self, reset_triggers=False, drop_tables=False):
        """Complete database setup"""
        self.create_database_if_not_exists()

        if reset_triggers:
            print("Dropping existing triggers...")
            self.drop_existing_triggers()

        if drop_tables:
            print("Dropping existing tables...")
            self.drop_existing_tables()

        self.create_tables()
        self.create_triggers()
        print("PostgreSQL database setup completed successfully!")

    def clear_all_data(self):
        """Clear all data from tables (useful for re-migration)"""
        clear_sql = """
        TRUNCATE TABLE terraform_jobs CASCADE;
        TRUNCATE TABLE migration_jobs CASCADE;
        TRUNCATE TABLE file_accesses CASCADE;
        TRUNCATE TABLE user_comments CASCADE;
        TRUNCATE TABLE payments CASCADE;
        TRUNCATE TABLE physical_files CASCADE;
        TRUNCATE TABLE cases CASCADE;
        TRUNCATE TABLE clients CASCADE;
        TRUNCATE TABLE recent_searches CASCADE;
        TRUNCATE TABLE popular_searches CASCADE;
        """

        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            cursor.execute(clear_sql)
            conn.commit()
            print("All data cleared successfully")
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            print(f"Error clearing data: {e}")
            raise


if __name__ == "__main__":
    import sys

    # You can modify these connection parameters as needed
    db_setup = PostgreSQLSetup(
        host="localhost",
        port=5432,
        database="legal_case_manager",
        user="postgres",
        password="postgres",  # Change this to your PostgreSQL password
    )

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            print("Resetting database with trigger cleanup...")
            db_setup.setup_database(reset_triggers=True, drop_tables=True)
        elif sys.argv[1] == "--clear-data":
            print("Clearing all data...")
            db_setup.clear_all_data()
        else:
            print("Usage: python database_setup.py [--reset|--clear-data]")
    else:
        db_setup.setup_database()
