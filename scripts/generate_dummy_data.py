#!/usr/bin/env python3
"""
PostgreSQL Dummy Data Generator for Legal Case File Manager

This script generates realistic dummy data directly into PostgreSQL database.
Useful for development, testing, and fresh database setups.

Usage:
    python generate_dummy_data.py [--clear] [--count N]
    
Options:
    --clear     Clear existing data before generating new data
    --count N   Number of clients to generate (default: 50)
"""

import os
import sys
import argparse
import random
from datetime import datetime, timedelta
from faker import Faker
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()

class PostgreSQLDummyDataGenerator:
    def __init__(self, host='localhost', port=5432, database='legal_case_manager', 
                 user='postgres', password='postgres'):
        """Initialize the dummy data generator with database connection."""
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.conn = None
        self.cursor = None
        
        # Data generation configuration
        self.case_types = [
            'Civil Litigation', 'Criminal Defense', 'Family Law', 'Corporate Law',
            'Real Estate', 'Personal Injury', 'Immigration', 'Bankruptcy',
            'Employment Law', 'Intellectual Property', 'Tax Law', 'Estate Planning'
        ]
        
        self.case_statuses = ['Open', 'Closed', 'On Hold', 'Under Review', 'Settled']
        self.client_types = ['Individual', 'Corporation', 'Non-Profit']  # Match database constraint
        self.client_statuses = ['Active', 'Inactive', 'Suspended']
        self.payment_methods = ['Cash', 'Check', 'Credit Card', 'Bank Transfer', 'Wire Transfer']
        self.payment_statuses = ['Paid', 'Pending', 'Overdue', 'Cancelled']
        self.file_locations = ['Archive Room A', 'Archive Room B', 'Main Office', 'Storage Unit 1', 'Digital Only']
        self.access_types = ['View', 'Edit', 'Print', 'Download', 'Archive']
        
        # Lawyers for assignment
        self.lawyers = [
            'Sarah Johnson', 'Michael Chen', 'Emily Rodriguez', 'David Kim',
            'Jessica Williams', 'Robert Taylor', 'Amanda Davis', 'Christopher Lee',
            'Maria Gonzalez', 'James Wilson', 'Lisa Anderson', 'Daniel Martinez'
        ]

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to PostgreSQL database successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def clear_existing_data(self):
        """Clear all existing data from tables (in proper order to respect foreign keys)."""
        # Delete in order that respects foreign key constraints
        # Most dependent tables first, then parent tables
        tables = [
            'recent_searches',    # No dependencies
            'popular_searches',   # No dependencies  
            'file_accesses',      # References physical_files
            'user_comments',      # References entities but no FK constraint
            'payments',           # References clients and cases
            'physical_files',     # References clients and cases
            'cases',              # References clients
            'clients'             # No dependencies (parent table)
        ]
        
        try:
            logger.info("Clearing existing data...")
            
            # Disable foreign key checks temporarily for easier clearing
            self.cursor.execute("SET session_replication_role = replica;")
            
            for table in tables:
                try:
                    self.cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                    logger.info(f"Truncated table: {table}")
                except Exception as table_error:
                    logger.warning(f"Could not truncate table {table}: {table_error}")
                    try:
                        # Fallback to DELETE
                        self.cursor.execute(f"DELETE FROM {table}")
                        logger.info(f"Deleted from table: {table}")
                    except Exception as delete_error:
                        logger.warning(f"Could not delete from table {table}: {delete_error}")
            
            # Re-enable foreign key checks
            self.cursor.execute("SET session_replication_role = DEFAULT;")
            
            self.conn.commit()
            logger.info("All existing data cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing existing data: {e}")
            logger.error(f"Error type: {type(e)}")
            if hasattr(e, 'pgcode'):
                logger.error(f"PostgreSQL error code: {e.pgcode}")
            self.conn.rollback()
            raise

    def generate_clients(self, count=50):
        """Generate dummy client records."""
        logger.info(f"Generating {count} clients...")
        clients = []
        
        for i in range(count):
            # Generate client ID (CLI followed by 4 digits)
            client_id = f"CLI{i+1:04d}"
            
            # Generate client data
            first_name = fake.first_name()
            last_name = fake.last_name()
            client_type = random.choice(self.client_types)
            
            # Adjust name for corporations
            if client_type == 'Corporation':
                first_name = fake.company()
                last_name = random.choice(['LLC', 'Inc', 'Corp', 'Ltd'])
            elif client_type == 'Non-Profit':
                first_name = fake.company()
                last_name = random.choice(['Foundation', 'Trust', 'Association', 'Society'])
            
            client_data = {
                'client_id': client_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': fake.email(),
                'phone': fake.phone_number()[:20],  # Limit phone length
                'address': fake.address().replace('\n', ', '),
                'date_of_birth': fake.date_of_birth(minimum_age=18, maximum_age=90),
                'client_type': client_type,
                'registration_date': fake.date_between(start_date='-5y', end_date='today'),
                'status': random.choice(self.client_statuses)
            }
            clients.append(client_data)
            
            # Insert client
            insert_query = """
                INSERT INTO clients (client_id, first_name, last_name, email, phone, address, 
                                   date_of_birth, client_type, registration_date, status)
                VALUES (%(client_id)s, %(first_name)s, %(last_name)s, %(email)s, %(phone)s, 
                       %(address)s, %(date_of_birth)s, %(client_type)s, %(registration_date)s, %(status)s)
            """
            self.cursor.execute(insert_query, client_data)
        
        self.conn.commit()
        logger.info(f"Successfully generated {count} clients")
        return clients

    def generate_cases(self, clients):
        """Generate dummy case records for clients."""
        logger.info("Generating cases...")
        cases = []
        case_count = 0
        
        for client in clients:
            # Each client gets 1-4 cases
            num_cases = random.randint(1, 4)
            
            for j in range(num_cases):
                case_count += 1
                case_id = f"CASE{case_count:04d}"
                reference_number = f"REF{case_count:06d}"
                
                case_data = {
                    'case_id': case_id,
                    'reference_number': reference_number,
                    'client_id': client['client_id'],
                    'case_type': random.choice(self.case_types),
                    'case_status': random.choice(self.case_statuses),
                    'created_date': fake.date_between(start_date=client['registration_date'], end_date='today'),
                    'assigned_lawyer': random.choice(self.lawyers),
                    'priority': random.choice(['Low', 'Medium', 'High', 'Critical']),
                    'estimated_value': round(random.uniform(1000, 500000), 2),
                    'description': fake.text(max_nb_chars=200)
                }
                
                # Set last_updated to be after created_date
                case_data['last_updated'] = fake.date_between(
                    start_date=case_data['created_date'], 
                    end_date='today'
                )
                
                cases.append(case_data)
                
                # Insert case
                insert_query = """
                    INSERT INTO cases (case_id, reference_number, client_id, case_type, case_status,
                                     created_date, last_updated, assigned_lawyer, priority, estimated_value, description)
                    VALUES (%(case_id)s, %(reference_number)s, %(client_id)s, %(case_type)s, %(case_status)s,
                           %(created_date)s, %(last_updated)s, %(assigned_lawyer)s, %(priority)s, %(estimated_value)s, %(description)s)
                """
                self.cursor.execute(insert_query, case_data)
        
        self.conn.commit()
        logger.info(f"Successfully generated {len(cases)} cases")
        return cases

    def generate_physical_files(self, cases):
        """Generate dummy physical file records for cases."""
        logger.info("Generating physical files...")
        files = []
        file_count = 0
        
        for case in cases:
            # Each case gets 1-3 files
            num_files = random.randint(1, 3)
            
            for k in range(num_files):
                file_count += 1
                file_id = f"FILE{file_count:06d}"
                
                # Generate file keywords
                keywords = [
                    fake.word(), fake.word(), case['case_type'].lower().replace(' ', '_')
                ]
                if random.choice([True, False]):
                    keywords.append(fake.word())
                
                file_data = {
                    'file_id': file_id,
                    'reference_number': f"{case['reference_number']}-{k+1:02d}",
                    'client_id': case['client_id'],
                    'case_id': case['case_id'],
                    'file_type': random.choice(['Legal Document', 'Contract', 'Evidence', 'Correspondence', 'Court Filing']),
                    'document_category': random.choice(['Litigation', 'Corporate', 'Real Estate', 'Family', 'Criminal']),
                    'warehouse_location': random.choice(self.file_locations),
                    'shelf_number': f"S{random.randint(1,50):03d}",
                    'box_number': f"B{random.randint(1,100):03d}",
                    'file_size': f"{round(random.uniform(0.1, 50.0), 2)} MB",
                    'file_description': fake.sentence(nb_words=6),
                    'keywords': keywords,
                    'created_date': fake.date_between(start_date=case['created_date'], end_date='today'),
                    'confidentiality_level': random.choice(['Public', 'Internal', 'Confidential', 'Highly Confidential']),
                    'storage_status': random.choice(['Active', 'Archived', 'Pending Review'])
                }
                
                files.append(file_data)
                
                # Insert file
                insert_query = """
                    INSERT INTO physical_files (file_id, reference_number, client_id, case_id, file_type,
                                              document_category, warehouse_location, shelf_number, box_number,
                                              file_size, file_description, keywords, created_date,
                                              confidentiality_level, storage_status)
                    VALUES (%(file_id)s, %(reference_number)s, %(client_id)s, %(case_id)s, %(file_type)s,
                           %(document_category)s, %(warehouse_location)s, %(shelf_number)s, %(box_number)s,
                           %(file_size)s, %(file_description)s, %(keywords)s, %(created_date)s,
                           %(confidentiality_level)s, %(storage_status)s)
                """
                self.cursor.execute(insert_query, file_data)
        
        self.conn.commit()
        logger.info(f"Successfully generated {len(files)} physical files")
        return files

    def generate_payments(self, cases):
        """Generate dummy payment records for cases."""
        logger.info("Generating payments...")
        payments = []
        payment_count = 0
        
        for case in cases:
            # Each case gets 0-5 payments
            num_payments = random.randint(0, 5)
            
            for p in range(num_payments):
                payment_count += 1
                payment_id = f"PAY{payment_count:06d}"
                
                payment_data = {
                    'payment_id': payment_id,
                    'client_id': case['client_id'],
                    'case_id': case['case_id'],
                    'amount': round(random.uniform(100, 10000), 2),
                    'payment_date': fake.date_between(start_date=case['created_date'], end_date='today'),
                    'payment_method': random.choice(self.payment_methods),
                    'status': random.choice(['Paid', 'Pending', 'Overdue']),  # Match schema constraints
                    'description': fake.sentence(nb_words=4)
                }
                
                payments.append(payment_data)
                
                # Insert payment
                insert_query = """
                    INSERT INTO payments (payment_id, client_id, case_id, amount, payment_date,
                                        payment_method, status, description)
                    VALUES (%(payment_id)s, %(client_id)s, %(case_id)s, %(amount)s, %(payment_date)s,
                           %(payment_method)s, %(status)s, %(description)s)
                """
                self.cursor.execute(insert_query, payment_data)
        
        self.conn.commit()
        logger.info(f"Successfully generated {len(payments)} payments")
        return payments

    def generate_file_accesses(self, files):
        """Generate dummy file access records."""
        logger.info("Generating file accesses...")
        access_logs = []
        access_count = 0
        
        for file_data in files:
            # Each file gets 0-10 access records
            num_accesses = random.randint(0, 10)
            
            for a in range(num_accesses):
                access_count += 1
                access_id = f"ACC{access_count:06d}"
                
                access_data = {
                    'access_id': access_id,
                    'file_id': file_data['file_id'],
                    'user_name': random.choice(self.lawyers),
                    'user_role': random.choice(['Lawyer', 'Paralegal', 'Assistant', 'Admin']),
                    'access_timestamp': fake.date_time_between(start_date=file_data['created_date'], end_date='now'),
                    'access_type': random.choice(self.access_types),
                    'ip_address': fake.ipv4(),
                    'user_agent': fake.user_agent(),
                    'session_duration': random.randint(30, 3600)  # 30 seconds to 1 hour
                }
                
                access_logs.append(access_data)
                
                # Insert access log
                insert_query = """
                    INSERT INTO file_accesses (access_id, file_id, user_name, user_role, access_timestamp, 
                                             access_type, ip_address, user_agent, session_duration)
                    VALUES (%(access_id)s, %(file_id)s, %(user_name)s, %(user_role)s, %(access_timestamp)s,
                           %(access_type)s, %(ip_address)s, %(user_agent)s, %(session_duration)s)
                """
                self.cursor.execute(insert_query, access_data)
        
        self.conn.commit()
        logger.info(f"Successfully generated {len(access_logs)} file accesses")
        return access_logs

    def generate_user_comments(self, files):
        """Generate dummy user comment records."""
        logger.info("Generating user comments...")
        comments = []
        comment_count = 0
        
        for file_data in files:
            # Each file gets 0-5 comments
            num_comments = random.randint(0, 5)
            
            for c in range(num_comments):
                comment_count += 1
                comment_id = f"COM{comment_count:06d}"
                
                comment_data = {
                    'comment_id': comment_id,
                    'entity_type': 'file',
                    'entity_id': file_data['file_id'],
                    'user_name': random.choice(self.lawyers),
                    'user_role': random.choice(['Lawyer', 'Paralegal', 'Assistant', 'Admin']),
                    'comment_text': fake.paragraph(nb_sentences=random.randint(1, 3)),
                    'created_timestamp': fake.date_time_between(start_date=file_data['created_date'], end_date='now'),
                    'is_private': random.choice([True, False])
                }
                
                comments.append(comment_data)
                
                # Insert comment
                insert_query = """
                    INSERT INTO user_comments (comment_id, entity_type, entity_id, user_name, user_role,
                                             comment_text, created_timestamp, is_private)
                    VALUES (%(comment_id)s, %(entity_type)s, %(entity_id)s, %(user_name)s, %(user_role)s,
                           %(comment_text)s, %(created_timestamp)s, %(is_private)s)
                """
                self.cursor.execute(insert_query, comment_data)
        
        self.conn.commit()
        logger.info(f"Successfully generated {len(comments)} user comments")
        return comments

    def generate_statistics(self, clients, cases, files, payments, access_logs, comments):
        """Generate and display statistics about the generated data."""
        stats = {
            'clients': len(clients),
            'cases': len(cases),
            'files': len(files),
            'payments': len(payments),
            'access_logs': len(access_logs),
            'comments': len(comments)
        }
        
        # Calculate additional statistics
        total_case_value = sum(case.get('estimated_value', 0) for case in cases)
        total_payment_amount = sum(payment.get('amount', 0) for payment in payments)
        
        active_clients = len([c for c in clients if c['status'] == 'Active'])
        active_cases = len([c for c in cases if c['case_status'] == 'Open'])
        
        print("\n" + "="*60)
        print("DUMMY DATA GENERATION COMPLETE!")
        print("="*60)
        print(f"STATISTICS:")
        print(f"  - Clients:          {stats['clients']:,} ({active_clients} active)")
        print(f"  - Cases:            {stats['cases']:,} ({active_cases} active)")
        print(f"  - Physical Files:   {stats['files']:,}")
        print(f"  - Payments:         {stats['payments']:,}")
        print(f"  - Access Logs:      {stats['access_logs']:,}")
        print(f"  - Comments:         {stats['comments']:,}")
        print(f"\nFINANCIAL:")
        print(f"  - Total Case Value: ${total_case_value:,.2f}")
        print(f"  - Total Payments:   ${total_payment_amount:,.2f}")
        print(f"\nCASE TYPES:")
        case_type_counts = {}
        for case in cases:
            case_type = case['case_type']
            case_type_counts[case_type] = case_type_counts.get(case_type, 0) + 1
        
        for case_type, count in sorted(case_type_counts.items()):
            print(f"  - {case_type}: {count}")
        
        print("="*60)
        
        return stats

    def run(self, client_count=50, clear_existing=False):
        """Run the complete dummy data generation process."""
        try:
            if not self.connect():
                return False
            
            if clear_existing:
                self.clear_existing_data()
            
            # Generate data in proper order (respecting foreign keys)
            logger.info("Starting dummy data generation...")
            
            clients = self.generate_clients(client_count)
            cases = self.generate_cases(clients)
            files = self.generate_physical_files(cases)
            payments = self.generate_payments(cases)
            access_logs = self.generate_file_accesses(files)
            comments = self.generate_user_comments(files)
            
            # Generate statistics
            self.generate_statistics(clients, cases, files, payments, access_logs, comments)
            
            logger.info("Dummy data generation completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during data generation: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            self.disconnect()

def main():
    """Main function to handle command line arguments and run the generator."""
    parser = argparse.ArgumentParser(description='Generate dummy data for Legal Case File Manager PostgreSQL database')
    parser.add_argument('--clear', action='store_true', help='Clear existing data before generating new data')
    parser.add_argument('--count', type=int, default=50, help='Number of clients to generate (default: 50)')
    parser.add_argument('--host', default='localhost', help='Database host (default: localhost)')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('--database', default='legal_case_manager', help='Database name (default: legal_case_manager)')
    parser.add_argument('--user', default='postgres', help='Database user (default: postgres)')
    parser.add_argument('--password', default='postgres', help='Database password (default: postgres)')
    
    args = parser.parse_args()
    
    # Create generator instance
    generator = PostgreSQLDummyDataGenerator(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password
    )
    
    # Run generation
    success = generator.run(client_count=args.count, clear_existing=args.clear)
    
    if success:
        print(f"\n[SUCCESS] Successfully generated dummy data!")
        print(f"[INFO] You can now run: python app_postgresql.py")
        sys.exit(0)
    else:
        print(f"\n[ERROR] Failed to generate dummy data. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
