from flask import Flask, render_template, request, jsonify, url_for
from datetime import datetime, timedelta
import json
import random
from faker import Faker
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import re
from ai_migration import migration_bp

app = Flask(__name__)
fake = Faker()

# Register migration blueprint
app.register_blueprint(migration_bp)

@dataclass
class Client:
    client_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    date_of_birth: str
    client_type: str  # Individual, Corporation, Non-Profit
    registration_date: str
    status: str  # Active, Inactive, Suspended

@dataclass
class Payment:
    payment_id: str
    client_id: str
    case_id: str
    amount: float
    payment_date: str
    payment_method: str
    status: str  # Paid, Pending, Overdue
    description: str

@dataclass
class Case:
    case_id: str
    reference_number: str
    client_id: str
    case_type: str
    case_status: str
    created_date: str
    last_updated: str
    assigned_lawyer: str
    priority: str
    estimated_value: float
    description: str

@dataclass
class PhysicalFile:
    file_id: str
    reference_number: str
    case_id: str
    client_id: str
    file_type: str
    document_category: str
    warehouse_location: str
    shelf_number: str
    box_number: str
    file_size: str
    created_date: str
    last_accessed: str
    last_modified: str
    storage_status: str
    confidentiality_level: str
    keywords: List[str]
    file_description: str

@dataclass
class FileAccess:
    access_id: str
    file_id: str
    user_name: str
    user_role: str
    access_timestamp: str
    access_type: str  # 'view', 'search', 'export'
    ip_address: str
    user_agent: str
    session_duration: Optional[int] = None  # in seconds

@dataclass
class UserComment:
    comment_id: str
    entity_type: str  # 'file', 'client', 'case', 'payment'
    entity_id: str
    user_name: str
    user_role: str
    comment_text: str
    created_timestamp: str
    is_private: bool = False  # Private comments only visible to certain roles

class LegalFileManager:
    def __init__(self):
        self.clients: List[Client] = []
        self.cases: List[Case] = []
        self.files: List[PhysicalFile] = []
        self.payments: List[Payment] = []
        self.file_accesses: List[FileAccess] = []
        self.comments: List[UserComment] = []
        self.recent_searches: List[str] = []  # Store recent searches
        self.popular_searches: Dict[str, int] = {}  # Track search frequency
        self.generate_sample_data()
        self.generate_sample_access_history()
        self.generate_sample_comments()
        self.initialize_popular_searches()

    def generate_sample_data(self):
        """Generate comprehensive sample data for demonstration"""
        
        # Generate clients
        client_types = ['Individual', 'Corporation', 'Non-Profit']
        statuses = ['Active', 'Inactive', 'Suspended']
        
        for i in range(50):
            client = Client(
                client_id=f"CLI{i+1:04d}",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=fake.phone_number(),
                address=fake.address().replace('\n', ', '),
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
                client_type=random.choice(client_types),
                registration_date=fake.date_between(start_date='-5y', end_date='today').isoformat(),
                status=random.choice(statuses)
            )
            self.clients.append(client)

        # Generate cases
        case_types = [
            'Personal Injury', 'Corporate Law', 'Criminal Defense', 'Family Law',
            'Real Estate', 'Employment Law', 'Immigration', 'Intellectual Property',
            'Tax Law', 'Environmental Law', 'Contract Dispute', 'Bankruptcy'
        ]
        case_statuses = ['Open', 'Closed', 'On Hold', 'Under Review', 'Settled']
        priorities = ['Low', 'Medium', 'High', 'Critical']
        lawyers = [
            'John Smith', 'Sarah Johnson', 'Michael Brown', 'Emily Davis',
            'Robert Wilson', 'Jennifer Miller', 'David Anderson', 'Lisa Taylor'
        ]

        for i in range(100):
            client = random.choice(self.clients)
            case = Case(
                case_id=f"CASE{i+1:04d}",
                reference_number=f"REF-{random.randint(100000, 999999)}",
                client_id=client.client_id,
                case_type=random.choice(case_types),
                case_status=random.choice(case_statuses),
                created_date=fake.date_between(start_date='-2y', end_date='today').isoformat(),
                last_updated=fake.date_between(start_date='-1y', end_date='today').isoformat(),
                assigned_lawyer=random.choice(lawyers),
                priority=random.choice(priorities),
                estimated_value=round(random.uniform(1000, 500000), 2),
                description=fake.text(max_nb_chars=200)
            )
            self.cases.append(case)

        # Generate physical files
        file_types = ['Contract', 'Evidence', 'Correspondence', 'Court Filing', 'Research', 'Client Records']
        document_categories = [
            'Legal Documents', 'Financial Records', 'Personal Documents', 'Court Records',
            'Evidence Files', 'Correspondence', 'Research Materials', 'Administrative'
        ]
        storage_statuses = ['Active', 'Archived', 'Pending Review', 'Scheduled for Destruction']
        confidentiality_levels = ['Public', 'Internal', 'Confidential', 'Highly Confidential']
        file_sizes = ['Small (< 1 inch)', 'Medium (1-3 inches)', 'Large (3-6 inches)', 'Extra Large (6+ inches)']

        for i in range(200):
            case = random.choice(self.cases)
            client_id = case.client_id
            
            # Generate relevant keywords
            keywords = []
            keywords.append(case.case_type.lower().replace(' ', '_'))
            keywords.extend(fake.words(nb=random.randint(2, 5)))
            
            created_date = fake.date_between(start_date='-2y', end_date='today')
            last_accessed_date = fake.date_between(start_date='-6m', end_date='today')
            last_modified_date = fake.date_between(start_date=created_date, end_date='today')
            
            file_record = PhysicalFile(
                file_id=f"FILE{i+1:05d}",
                reference_number=case.reference_number,
                case_id=case.case_id,
                client_id=client_id,
                file_type=random.choice(file_types),
                document_category=random.choice(document_categories),
                warehouse_location=f"Warehouse {random.choice(['A', 'B', 'C'])}",
                shelf_number=f"S{random.randint(1, 50):02d}",
                box_number=f"B{random.randint(1, 200):03d}",
                file_size=random.choice(file_sizes),
                created_date=created_date.isoformat(),
                last_accessed=last_accessed_date.isoformat(),
                last_modified=last_modified_date.isoformat(),
                storage_status=random.choice(storage_statuses),
                confidentiality_level=random.choice(confidentiality_levels),
                keywords=keywords,
                file_description=fake.text(max_nb_chars=150)
            )
            self.files.append(file_record)

        # Generate payments
        payment_methods = ['Check', 'Credit Card', 'Bank Transfer', 'Cash', 'Money Order']
        payment_statuses = ['Paid', 'Pending', 'Overdue']

        for i in range(150):
            case = random.choice(self.cases)
            payment = Payment(
                payment_id=f"PAY{i+1:05d}",
                client_id=case.client_id,
                case_id=case.case_id,
                amount=round(random.uniform(100, 50000), 2),
                payment_date=fake.date_between(start_date='-1y', end_date='today').isoformat(),
                payment_method=random.choice(payment_methods),
                status=random.choice(payment_statuses),
                description=f"Payment for {case.case_type} - {fake.sentence()}"
            )
            self.payments.append(payment)

    def generate_sample_access_history(self):
        """Generate sample file access history for demonstration"""
        
        # Sample users with roles
        users = [
            ('John Smith', 'Partner'), ('Sarah Johnson', 'Associate'), 
            ('Michael Brown', 'Paralegal'), ('Emily Davis', 'Partner'),
            ('Robert Wilson', 'Associate'), ('Jennifer Miller', 'Clerk'),
            ('David Anderson', 'Paralegal'), ('Lisa Taylor', 'Partner'),
            ('James Wilson', 'Associate'), ('Maria Garcia', 'Paralegal')
        ]
        
        access_types = ['view', 'search', 'export']
        ip_addresses = ['192.168.1.100', '192.168.1.101', '192.168.1.102', '192.168.1.103', '10.0.0.50']
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0'
        ]
        
        # Generate access history for each file
        access_id = 1
        for file in self.files:
            # Generate 3-8 access records per file
            num_accesses = random.randint(3, 8)
            
            for _ in range(num_accesses):
                user_name, user_role = random.choice(users)
                access_date = fake.date_time_between(start_date='-6m', end_date='now')
                
                access = FileAccess(
                    access_id=f"ACC{access_id:06d}",
                    file_id=file.file_id,
                    user_name=user_name,
                    user_role=user_role,
                    access_timestamp=access_date.isoformat(),
                    access_type=random.choice(access_types),
                    ip_address=random.choice(ip_addresses),
                    user_agent=random.choice(user_agents),
                    session_duration=random.randint(30, 900) if random.random() > 0.3 else None
                )
                self.file_accesses.append(access)
                access_id += 1

    def generate_sample_comments(self):
        """Generate sample user comments for demonstration"""
        
        # Sample users with roles
        users = [
            ('John Smith', 'Partner'), ('Sarah Johnson', 'Associate'), 
            ('Michael Brown', 'Paralegal'), ('Emily Davis', 'Partner'),
            ('Robert Wilson', 'Associate'), ('Jennifer Miller', 'Clerk'),
            ('David Anderson', 'Paralegal'), ('Lisa Taylor', 'Partner'),
            ('James Wilson', 'Associate'), ('Maria Garcia', 'Paralegal')
        ]
        
        comment_templates = [
            "Reviewed this {entity_type}. Everything looks in order.",
            "Need to follow up on this {entity_type} next week.",
            "Client requested additional information regarding this {entity_type}.",
            "Updated status after discussion with client.",
            "Important: This {entity_type} requires urgent attention.",
            "Excellent progress on this {entity_type}. Client very satisfied.",
            "Meeting scheduled to discuss this {entity_type} further.",
            "Documents are complete and ready for review.",
            "Billing inquiry resolved for this {entity_type}.",
            "Priority level upgraded due to complexity.",
            "All requirements met. Proceeding to next phase.",
            "Client provided additional documentation.",
            "Review completed. No issues found.",
            "Deadline extended per client request.",
            "Conference call scheduled with opposing counsel."
        ]
        
        # Generate comments for files
        comment_id = 1
        for file in self.files[:100]:  # Comments on first 100 files
            num_comments = random.randint(1, 4)
            for _ in range(num_comments):
                user_name, user_role = random.choice(users)
                comment_text = random.choice(comment_templates).format(entity_type='file')
                created_time = fake.date_time_between(start_date='-3m', end_date='now')
                
                comment = UserComment(
                    comment_id=f"COM{comment_id:06d}",
                    entity_type='file',
                    entity_id=file.file_id,
                    user_name=user_name,
                    user_role=user_role,
                    comment_text=comment_text,
                    created_timestamp=created_time.isoformat(),
                    is_private=random.random() > 0.8  # 20% private comments
                )
                self.comments.append(comment)
                comment_id += 1
        
        # Generate comments for clients
        for client in self.clients[:30]:  # Comments on first 30 clients
            num_comments = random.randint(0, 2)
            for _ in range(num_comments):
                user_name, user_role = random.choice(users)
                comment_text = random.choice(comment_templates).format(entity_type='client')
                created_time = fake.date_time_between(start_date='-6m', end_date='now')
                
                comment = UserComment(
                    comment_id=f"COM{comment_id:06d}",
                    entity_type='client',
                    entity_id=client.client_id,
                    user_name=user_name,
                    user_role=user_role,
                    comment_text=comment_text,
                    created_timestamp=created_time.isoformat(),
                    is_private=random.random() > 0.7  # 30% private comments
                )
                self.comments.append(comment)
                comment_id += 1
        
        # Generate comments for cases
        for case in self.cases[:50]:  # Comments on first 50 cases
            num_comments = random.randint(1, 3)
            for _ in range(num_comments):
                user_name, user_role = random.choice(users)
                comment_text = random.choice(comment_templates).format(entity_type='case')
                created_time = fake.date_time_between(start_date='-4m', end_date='now')
                
                comment = UserComment(
                    comment_id=f"COM{comment_id:06d}",
                    entity_type='case',
                    entity_id=case.case_id,
                    user_name=user_name,
                    user_role=user_role,
                    comment_text=comment_text,
                    created_timestamp=created_time.isoformat(),
                    is_private=random.random() > 0.85  # 15% private comments
                )
                self.comments.append(comment)
                comment_id += 1

    def initialize_popular_searches(self):
        """Initialize with some popular search terms"""
        popular_terms = [
            "contract", "personal injury", "corporate law", "john smith", "sarah johnson",
            "evidence", "correspondence", "court filing", "family law", "real estate",
            "payment", "overdue", "confidential", "warehouse a", "active cases",
            "criminal defense", "immigration", "bankruptcy", "tax law", "employment law"
        ]
        
        for term in popular_terms:
            self.popular_searches[term] = random.randint(5, 50)

    def log_search(self, query: str):
        """Log a search query for intelligent suggestions"""
        if not query or len(query.strip()) < 2:
            return
        
        query = query.lower().strip()
        
        # Add to recent searches
        if query in self.recent_searches:
            self.recent_searches.remove(query)
        self.recent_searches.insert(0, query)
        
        # Keep only last 50 recent searches
        self.recent_searches = self.recent_searches[:50]
        
        # Update popular searches
        self.popular_searches[query] = self.popular_searches.get(query, 0) + 1

    def get_intelligent_suggestions(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Generate intelligent suggestions based on query, context, and user behavior
        """
        if len(query) < 1:
            return {
                'suggestions': [],
                'categories': {},
                'popular': list(sorted(self.popular_searches.items(), key=lambda x: x[1], reverse=True)[:5])
            }
        
        query_lower = query.lower()
        suggestions = {
            'contextual': [],
            'clients': [],
            'cases': [],
            'files': [],
            'payments': [],
            'recent': [],
            'popular': [],
            'completions': []
        }
        
        # 1. Contextual suggestions based on query patterns
        suggestions['contextual'] = self._get_contextual_suggestions(query_lower)
        
        # 2. Client name suggestions
        for client in self.clients:
            full_name = f"{client.first_name} {client.last_name}".lower()
            if query_lower in full_name or query_lower in client.email.lower():
                suggestions['clients'].append({
                    'text': f"{client.first_name} {client.last_name}",
                    'type': 'client',
                    'email': client.email,
                    'status': client.status
                })
        
        # 3. Case type and reference suggestions
        case_types = set()
        for case in self.cases:
            if query_lower in case.case_type.lower():
                case_types.add(case.case_type)
            if query_lower in case.reference_number.lower():
                suggestions['cases'].append({
                    'text': case.reference_number,
                    'type': 'case_reference',
                    'case_type': case.case_type,
                    'status': case.case_status
                })
        
        for case_type in sorted(case_types):
            suggestions['cases'].append({
                'text': case_type,
                'type': 'case_type',
                'case_type': case_type
            })
        
        # 4. File-related suggestions
        file_types = set()
        categories = set()
        references = []
        
        for file in self.files:
            if query_lower in file.file_type.lower():
                file_types.add(file.file_type)
            if query_lower in file.document_category.lower():
                categories.add(file.document_category)
            if query_lower in file.reference_number.lower():
                references.append({
                    'text': file.reference_number,
                    'type': 'file_reference',
                    'file_type': file.file_type,
                    'client': self.get_client_name(file.client_id)
                })
            # Check keywords
            for keyword in file.keywords:
                if query_lower in keyword.lower():
                    suggestions['files'].append({
                        'text': keyword,
                        'type': 'keyword',
                        'keyword': keyword
                    })
        
        for file_type in sorted(file_types):
            suggestions['files'].append({
                'text': file_type,
                'type': 'file_type',
                'file_type': file_type
            })
        
        for category in sorted(categories):
            suggestions['files'].append({
                'text': category,
                'type': 'document_category',
                'category': category
            })
        
        suggestions['files'].extend(references[:3])  # Limit file references
        
        # 5. Payment-related suggestions
        payment_methods = set()
        for payment in self.payments:
            if query_lower in payment.payment_method.lower():
                payment_methods.add(payment.payment_method)
            if query_lower in str(payment.amount):
                suggestions['payments'].append({
                    'text': f"${payment.amount}",
                    'type': 'payment_amount',
                    'amount': payment.amount
                })
        
        for method in sorted(payment_methods):
            suggestions['payments'].append({
                'text': method,
                'type': 'payment_method',
                'method': method
            })
        
        # 6. Recent search suggestions
        for recent in self.recent_searches[:5]:
            if query_lower in recent and recent != query_lower:
                suggestions['recent'].append({
                    'text': recent,
                    'type': 'recent_search'
                })
        
        # 7. Popular search suggestions
        for popular, count in sorted(self.popular_searches.items(), key=lambda x: x[1], reverse=True)[:5]:
            if query_lower in popular and popular != query_lower:
                suggestions['popular'].append({
                    'text': popular,
                    'type': 'popular_search',
                    'count': count
                })
        
        # 8. Smart completions
        suggestions['completions'] = self._get_smart_completions(query_lower)
        
        # 9. Typo corrections (if no exact matches found)
        if not any(suggestions.values()) or len([s for category in suggestions.values() for s in category]) < 3:
            typo_corrections = self.get_typo_corrections(query)
            if typo_corrections:
                suggestions['corrections'] = typo_corrections
        
        # Combine and rank all suggestions
        all_suggestions = []
        priority_order = ['contextual', 'clients', 'recent', 'completions', 'corrections', 'cases', 'files', 'payments', 'popular']
        
        for category in priority_order:
            if category in suggestions and suggestions[category]:  # Check if category exists
                for suggestion in suggestions[category][:3]:  # Limit per category
                    all_suggestions.append(suggestion)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in all_suggestions:
            text = suggestion['text'].lower()
            if text not in seen:
                seen.add(text)
                unique_suggestions.append(suggestion)
        
        return {
            'suggestions': unique_suggestions[:limit],
            'categories': {k: v for k, v in suggestions.items() if v},
            'recent_searches': self.recent_searches[:5],
            'popular_searches': sorted(self.popular_searches.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    def _get_contextual_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Generate contextual suggestions based on query patterns"""
        suggestions = []
        
        # Legal document types
        if any(word in query for word in ['contract', 'agreement', 'legal']):
            suggestions.extend([
                {'text': 'contract documents', 'type': 'contextual', 'context': 'legal_docs'},
                {'text': 'legal agreements', 'type': 'contextual', 'context': 'legal_docs'},
                {'text': 'confidential contracts', 'type': 'contextual', 'context': 'legal_docs'}
            ])
        
        # Case types
        if any(word in query for word in ['injury', 'accident', 'personal']):
            suggestions.extend([
                {'text': 'Personal Injury cases', 'type': 'contextual', 'context': 'case_type'},
                {'text': 'accident reports', 'type': 'contextual', 'context': 'documents'}
            ])
        
        # Financial terms
        if any(word in query for word in ['payment', 'money', 'billing', 'invoice']):
            suggestions.extend([
                {'text': 'overdue payments', 'type': 'contextual', 'context': 'payments'},
                {'text': 'pending invoices', 'type': 'contextual', 'context': 'payments'},
                {'text': 'payment history', 'type': 'contextual', 'context': 'payments'}
            ])
        
        # Location-based
        if any(word in query for word in ['warehouse', 'location', 'storage']):
            suggestions.extend([
                {'text': 'Warehouse A files', 'type': 'contextual', 'context': 'location'},
                {'text': 'Warehouse B files', 'type': 'contextual', 'context': 'location'},
                {'text': 'archived documents', 'type': 'contextual', 'context': 'storage'}
            ])
        
        # Status-based
        if any(word in query for word in ['active', 'closed', 'pending']):
            suggestions.extend([
                {'text': 'active cases', 'type': 'contextual', 'context': 'status'},
                {'text': 'closed files', 'type': 'contextual', 'context': 'status'},
                {'text': 'pending reviews', 'type': 'contextual', 'context': 'status'}
            ])
        
        return suggestions[:3]

    def _get_smart_completions(self, query: str) -> List[Dict[str, Any]]:
        """Generate smart completions for partial queries"""
        completions = []
        
        # Complete client names
        for client in self.clients:
            full_name = f"{client.first_name} {client.last_name}"
            if full_name.lower().startswith(query) and len(query) >= 2:
                completions.append({
                    'text': full_name,
                    'type': 'name_completion',
                    'client_id': client.client_id,
                    'email': client.email
                })
        
        # Complete case types
        case_types = list(set(case.case_type for case in self.cases))
        for case_type in case_types:
            if case_type.lower().startswith(query) and len(query) >= 2:
                completions.append({
                    'text': case_type,
                    'type': 'case_type_completion',
                    'case_type': case_type
                })
        
        # Complete file types
        file_types = list(set(file.file_type for file in self.files))
        for file_type in file_types:
            if file_type.lower().startswith(query) and len(query) >= 2:
                completions.append({
                    'text': file_type,
                    'type': 'file_type_completion',
                    'file_type': file_type
                })
        
        return completions[:5]

    def _calculate_edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._calculate_edit_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def _find_similar_terms(self, query: str, candidates: List[str], max_distance: int = 2) -> List[str]:
        """Find terms similar to query using edit distance"""
        similar = []
        query_lower = query.lower()
        
        for candidate in candidates:
            candidate_lower = candidate.lower()
            
            # Exact match or contains
            if query_lower in candidate_lower:
                similar.append((candidate, 0))  # Exact match gets priority
            elif len(query) >= 3:  # Only do fuzzy matching for longer queries
                distance = self._calculate_edit_distance(query_lower, candidate_lower[:len(query_lower)])
                if distance <= max_distance:
                    similar.append((candidate, distance))
        
        # Sort by distance (lower is better)
        similar.sort(key=lambda x: x[1])
        return [term for term, distance in similar[:5]]

    def get_typo_corrections(self, query: str) -> List[Dict[str, Any]]:
        """Get typo correction suggestions"""
        if len(query) < 3:
            return []
        
        corrections = []
        
        # Get all potential correction candidates
        candidates = []
        
        # Client names
        for client in self.clients:
            candidates.append(f"{client.first_name} {client.last_name}")
            candidates.append(client.first_name)
            candidates.append(client.last_name)
        
        # Case types
        for case in self.cases:
            candidates.append(case.case_type)
        
        # File types and categories
        for file in self.files:
            candidates.append(file.file_type)
            candidates.append(file.document_category)
            candidates.extend(file.keywords)
        
        # Popular search terms
        candidates.extend(self.popular_searches.keys())
        
        # Remove duplicates and find similar terms
        unique_candidates = list(set(candidates))
        similar_terms = self._find_similar_terms(query, unique_candidates, max_distance=2)
        
        for term in similar_terms[:3]:  # Limit corrections
            corrections.append({
                'text': term,
                'type': 'typo_correction',
                'original': query
            })
        
        return corrections

    def log_file_access(self, file_id: str, user_name: str = "Anonymous User", 
                       user_role: str = "Visitor", access_type: str = "view",
                       ip_address: str = "127.0.0.1", user_agent: str = "Unknown"):
        """Log a new file access"""
        from datetime import datetime
        
        access_id = len(self.file_accesses) + 1
        access = FileAccess(
            access_id=f"ACC{access_id:06d}",
            file_id=file_id,
            user_name=user_name,
            user_role=user_role,
            access_timestamp=datetime.now().isoformat(),
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.file_accesses.append(access)
        
        # Update file's last_accessed timestamp
        file = next((f for f in self.files if f.file_id == file_id), None)
        if file:
            file.last_accessed = datetime.now().date().isoformat()

    def get_file_access_history(self, file_id: str) -> List[FileAccess]:
        """Get access history for a specific file"""
        return [access for access in self.file_accesses if access.file_id == file_id]

    def get_recent_file_accesses(self, limit: int = 10) -> List[FileAccess]:
        """Get recent file accesses across all files"""
        return sorted(self.file_accesses, key=lambda x: x.access_timestamp, reverse=True)[:limit]

    def get_user_file_accesses(self, user_name: str) -> List[FileAccess]:
        """Get all file accesses by a specific user"""
        return [access for access in self.file_accesses if access.user_name == user_name]

    def get_file_access_stats(self, file_id: str) -> Dict[str, Any]:
        """Get access statistics for a specific file"""
        accesses = self.get_file_access_history(file_id)
        
        if not accesses:
            return {
                'total_accesses': 0,
                'unique_users': 0,
                'last_accessed': None,
                'most_frequent_user': None,
                'access_types': {}
            }
        
        # Calculate statistics
        unique_users = len(set(access.user_name for access in accesses))
        last_access = max(accesses, key=lambda x: x.access_timestamp)
        
        # Count access types
        access_type_counts = {}
        user_access_counts = {}
        
        for access in accesses:
            access_type_counts[access.access_type] = access_type_counts.get(access.access_type, 0) + 1
            user_access_counts[access.user_name] = user_access_counts.get(access.user_name, 0) + 1
        
        most_frequent_user = max(user_access_counts.items(), key=lambda x: x[1])[0] if user_access_counts else None
        
        return {
            'total_accesses': len(accesses),
            'unique_users': unique_users,
            'last_accessed': last_access,
            'most_frequent_user': most_frequent_user,
            'access_types': access_type_counts,
            'user_access_counts': user_access_counts
        }

    def search_files(self, query: str, filters: Dict[str, Any] = None) -> List[PhysicalFile]:
        """Dynamic search functionality with multiple criteria"""
        results = self.files.copy()
        
        if not query and not filters:
            return results

        # Text-based search across multiple fields
        if query:
            query = query.lower()
            results = [
                file for file in results
                if (query in file.reference_number.lower() or
                    query in file.file_description.lower() or
                    query in file.document_category.lower() or
                    query in file.file_type.lower() or
                    any(query in keyword.lower() for keyword in file.keywords) or
                    query in self.get_client_name(file.client_id).lower() or
                    query in self.get_case_type(file.case_id).lower())
            ]

        # Apply filters
        if filters:
            if filters.get('case_type'):
                case_type = filters['case_type']
                results = [f for f in results if self.get_case_type(f.case_id) == case_type]
            
            if filters.get('file_type'):
                results = [f for f in results if f.file_type == filters['file_type']]
            
            if filters.get('confidentiality_level'):
                results = [f for f in results if f.confidentiality_level == filters['confidentiality_level']]
            
            if filters.get('storage_status'):
                results = [f for f in results if f.storage_status == filters['storage_status']]
            
            if filters.get('warehouse_location'):
                results = [f for f in results if f.warehouse_location == filters['warehouse_location']]
            
            # Date range filters
            results = self._apply_date_filters(results, filters)

        return results

    def unified_search(self, query: str, filters: Dict[str, Any] = None, include_private_comments: bool = False) -> Dict[str, Any]:
        """
        Unified search across all data types: files, clients, cases, payments, access history, and comments
        Returns categorized results with relevance scoring
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
        
        # Search Files (enhanced from existing search_files)
        if query:
            for file in self.files:
                score = 0
                matches = []
                
                # Check various file fields with different weights
                if query_lower in file.reference_number.lower():
                    score += 10
                    matches.append(f"Reference: {file.reference_number}")
                if query_lower in file.file_description.lower():
                    score += 8
                    matches.append(f"Description: {file.file_description[:100]}...")
                if query_lower in file.document_category.lower():
                    score += 6
                    matches.append(f"Category: {file.document_category}")
                if query_lower in file.file_type.lower():
                    score += 6
                    matches.append(f"Type: {file.file_type}")
                if any(query_lower in keyword.lower() for keyword in file.keywords):
                    score += 7
                    matching_keywords = [kw for kw in file.keywords if query_lower in kw.lower()]
                    matches.append(f"Keywords: {', '.join(matching_keywords)}")
                if query_lower in self.get_client_name(file.client_id).lower():
                    score += 9
                    matches.append(f"Client: {self.get_client_name(file.client_id)}")
                if query_lower in self.get_case_type(file.case_id).lower():
                    score += 7
                    matches.append(f"Case Type: {self.get_case_type(file.case_id)}")
                
                if score > 0:
                    file_result = asdict(file)
                    file_result['client_name'] = self.get_client_name(file.client_id)
                    file_result['case_type'] = self.get_case_type(file.case_id)
                    file_result['relevance_score'] = score
                    file_result['match_details'] = matches
                    results['files'].append(file_result)
        
        # Search Clients
        if query:
            for client in self.clients:
                score = 0
                matches = []
                
                full_name = f"{client.first_name} {client.last_name}".lower()
                if query_lower in full_name:
                    score += 10
                    matches.append(f"Name: {client.first_name} {client.last_name}")
                if query_lower in client.email.lower():
                    score += 9
                    matches.append(f"Email: {client.email}")
                if query_lower in client.phone.lower():
                    score += 8
                    matches.append(f"Phone: {client.phone}")
                if query_lower in client.address.lower():
                    score += 6
                    matches.append(f"Address: {client.address[:100]}...")
                if query_lower in client.client_type.lower():
                    score += 5
                    matches.append(f"Type: {client.client_type}")
                if query_lower in client.status.lower():
                    score += 4
                    matches.append(f"Status: {client.status}")
                
                if score > 0:
                    client_result = asdict(client)
                    client_result['relevance_score'] = score
                    client_result['match_details'] = matches
                    results['clients'].append(client_result)
        
        # Search Cases
        if query:
            for case in self.cases:
                score = 0
                matches = []
                
                if query_lower in case.reference_number.lower():
                    score += 10
                    matches.append(f"Reference: {case.reference_number}")
                if query_lower in case.case_type.lower():
                    score += 9
                    matches.append(f"Case Type: {case.case_type}")
                if query_lower in case.description.lower():
                    score += 8
                    matches.append(f"Description: {case.description[:100]}...")
                if query_lower in case.assigned_lawyer.lower():
                    score += 7
                    matches.append(f"Lawyer: {case.assigned_lawyer}")
                if query_lower in case.case_status.lower():
                    score += 6
                    matches.append(f"Status: {case.case_status}")
                if query_lower in case.priority.lower():
                    score += 5
                    matches.append(f"Priority: {case.priority}")
                
                # Include client name in case search
                client_name = self.get_client_name(case.client_id)
                if query_lower in client_name.lower():
                    score += 8
                    matches.append(f"Client: {client_name}")
                
                if score > 0:
                    case_result = asdict(case)
                    case_result['client_name'] = client_name
                    case_result['relevance_score'] = score
                    case_result['match_details'] = matches
                    results['cases'].append(case_result)
        
        # Search Payments
        if query:
            for payment in self.payments:
                score = 0
                matches = []
                
                if query_lower in payment.description.lower():
                    score += 8
                    matches.append(f"Description: {payment.description}")
                if query_lower in payment.payment_method.lower():
                    score += 6
                    matches.append(f"Payment Method: {payment.payment_method}")
                if query_lower in payment.status.lower():
                    score += 5
                    matches.append(f"Status: {payment.status}")
                if query_lower in str(payment.amount):
                    score += 7
                    matches.append(f"Amount: ${payment.amount}")
                
                # Include client and case information
                client_name = self.get_client_name(payment.client_id)
                case_type = self.get_case_type(payment.case_id)
                if query_lower in client_name.lower():
                    score += 8
                    matches.append(f"Client: {client_name}")
                if query_lower in case_type.lower():
                    score += 6
                    matches.append(f"Case Type: {case_type}")
                
                if score > 0:
                    payment_result = asdict(payment)
                    payment_result['client_name'] = client_name
                    payment_result['case_type'] = case_type
                    payment_result['relevance_score'] = score
                    payment_result['match_details'] = matches
                    results['payments'].append(payment_result)
        
        # Search Access History
        if query:
            for access in self.file_accesses:
                score = 0
                matches = []
                
                if query_lower in access.user_name.lower():
                    score += 8
                    matches.append(f"User: {access.user_name}")
                if query_lower in access.user_role.lower():
                    score += 6
                    matches.append(f"Role: {access.user_role}")
                if query_lower in access.access_type.lower():
                    score += 5
                    matches.append(f"Access Type: {access.access_type}")
                if query_lower in access.file_id.lower():
                    score += 7
                    matches.append(f"File ID: {access.file_id}")
                if query_lower in access.ip_address:
                    score += 4
                    matches.append(f"IP: {access.ip_address}")
                
                # Include file information
                file_info = next((f for f in self.files if f.file_id == access.file_id), None)
                if file_info:
                    if query_lower in file_info.reference_number.lower():
                        score += 9
                        matches.append(f"File Reference: {file_info.reference_number}")
                    client_name = self.get_client_name(file_info.client_id)
                    if query_lower in client_name.lower():
                        score += 7
                        matches.append(f"Client: {client_name}")
                
                if score > 0:
                    access_result = asdict(access)
                    access_result['file_reference'] = file_info.reference_number if file_info else 'Unknown'
                    access_result['client_name'] = self.get_client_name(file_info.client_id) if file_info else 'Unknown'
                    access_result['relevance_score'] = score
                    access_result['match_details'] = matches
                    results['access_history'].append(access_result)
        
        # Search Comments
        if query:
            for comment in self.comments:
                # Skip private comments unless specifically requested
                if comment.is_private and not include_private_comments:
                    continue
                
                score = 0
                matches = []
                
                if query_lower in comment.comment_text.lower():
                    score += 10
                    matches.append(f"Comment: {comment.comment_text[:150]}...")
                if query_lower in comment.user_name.lower():
                    score += 7
                    matches.append(f"User: {comment.user_name}")
                if query_lower in comment.user_role.lower():
                    score += 5
                    matches.append(f"Role: {comment.user_role}")
                if query_lower in comment.entity_type.lower():
                    score += 4
                    matches.append(f"Entity Type: {comment.entity_type}")
                
                # Include entity-specific information
                entity_info = ""
                if comment.entity_type == 'file':
                    file_info = next((f for f in self.files if f.file_id == comment.entity_id), None)
                    if file_info:
                        entity_info = f"File: {file_info.reference_number}"
                        if query_lower in file_info.reference_number.lower():
                            score += 8
                            matches.append(entity_info)
                elif comment.entity_type == 'client':
                    client_info = next((c for c in self.clients if c.client_id == comment.entity_id), None)
                    if client_info:
                        entity_info = f"Client: {client_info.first_name} {client_info.last_name}"
                        if query_lower in entity_info.lower():
                            score += 8
                            matches.append(entity_info)
                elif comment.entity_type == 'case':
                    case_info = next((c for c in self.cases if c.case_id == comment.entity_id), None)
                    if case_info:
                        entity_info = f"Case: {case_info.reference_number}"
                        if query_lower in case_info.reference_number.lower():
                            score += 8
                            matches.append(entity_info)
                
                if score > 0:
                    comment_result = asdict(comment)
                    comment_result['entity_info'] = entity_info
                    comment_result['relevance_score'] = score
                    comment_result['match_details'] = matches
                    results['comments'].append(comment_result)
        
        # Sort results by relevance score
        for category in ['files', 'clients', 'cases', 'payments', 'access_history', 'comments']:
            results[category].sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Calculate total results
        results['total_results'] = sum(len(results[category]) for category in ['files', 'clients', 'cases', 'payments', 'access_history', 'comments'])
        
        # Apply filters to files (existing functionality)
        if filters and results['files']:
            files_for_filtering = [PhysicalFile(**{k: v for k, v in file_result.items() if k in [field.name for field in PhysicalFile.__dataclass_fields__.values()]}) for file_result in results['files']]
            filtered_files = self._apply_filters_to_files(files_for_filtering, filters)
            results['files'] = [file_result for file_result in results['files'] if any(ff.file_id == file_result['file_id'] for ff in filtered_files)]
        
        return results

    def _apply_filters_to_files(self, files: List[PhysicalFile], filters: Dict[str, Any]) -> List[PhysicalFile]:
        """Helper method to apply filters to a list of files"""
        results = files.copy()
        
        if filters.get('case_type'):
            case_type = filters['case_type']
            results = [f for f in results if self.get_case_type(f.case_id) == case_type]
        
        if filters.get('file_type'):
            results = [f for f in results if f.file_type == filters['file_type']]
        
        if filters.get('confidentiality_level'):
            results = [f for f in results if f.confidentiality_level == filters['confidentiality_level']]
        
        if filters.get('storage_status'):
            results = [f for f in results if f.storage_status == filters['storage_status']]
        
        if filters.get('warehouse_location'):
            results = [f for f in results if f.warehouse_location == filters['warehouse_location']]
        
        # Date range filters
        results = self._apply_date_filters(results, filters)
        
        return results

    def _apply_date_filters(self, files: List[PhysicalFile], filters: Dict[str, Any]) -> List[PhysicalFile]:
        """Apply date range filters to file results"""
        from datetime import datetime
        
        filtered_files = files.copy()
        
        # Created date filter
        if filters.get('created_from') or filters.get('created_to'):
            created_from = self._parse_date(filters.get('created_from'))
            created_to = self._parse_date(filters.get('created_to'))
            
            filtered_files = [
                f for f in filtered_files
                if self._date_in_range(f.created_date, created_from, created_to)
            ]
        
        # Last accessed date filter
        if filters.get('accessed_from') or filters.get('accessed_to'):
            accessed_from = self._parse_date(filters.get('accessed_from'))
            accessed_to = self._parse_date(filters.get('accessed_to'))
            
            filtered_files = [
                f for f in filtered_files
                if self._date_in_range(f.last_accessed, accessed_from, accessed_to)
            ]
        
        # Last modified date filter
        if filters.get('modified_from') or filters.get('modified_to'):
            modified_from = self._parse_date(filters.get('modified_from'))
            modified_to = self._parse_date(filters.get('modified_to'))
            
            filtered_files = [
                f for f in filtered_files
                if self._date_in_range(f.last_modified, modified_from, modified_to)
            ]
        
        return filtered_files

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        try:
            from datetime import datetime
            # Handle both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS formats
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            return None

    def _date_in_range(self, date_str: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> bool:
        """Check if a date string falls within the given range"""
        if not date_str:
            return True
        
        file_date = self._parse_date(date_str)
        if not file_date:
            return True
        
        # Convert to date for comparison (ignore time)
        file_date_only = file_date.date()
        
        if start_date and file_date_only < start_date.date():
            return False
        
        if end_date and file_date_only > end_date.date():
            return False
        
        return True

    def get_client_name(self, client_id: str) -> str:
        """Get client full name by ID"""
        client = next((c for c in self.clients if c.client_id == client_id), None)
        return f"{client.first_name} {client.last_name}" if client else "Unknown"

    def get_case_type(self, case_id: str) -> str:
        """Get case type by case ID"""
        case = next((c for c in self.cases if c.case_id == case_id), None)
        return case.case_type if case else "Unknown"

    def get_client_recommendations(self, client_id: str) -> Dict[str, Any]:
        """Get recommended client details including other cases, payments, etc."""
        client = next((c for c in self.clients if c.client_id == client_id), None)
        if not client:
            return {}

        # Get all cases for this client
        client_cases = [c for c in self.cases if c.client_id == client_id]
        
        # Get all payments for this client
        client_payments = [p for p in self.payments if p.client_id == client_id]
        
        # Calculate payment statistics
        total_paid = sum(p.amount for p in client_payments if p.status == 'Paid')
        total_pending = sum(p.amount for p in client_payments if p.status == 'Pending')
        total_overdue = sum(p.amount for p in client_payments if p.status == 'Overdue')

        # Get all files for this client
        client_files = [f for f in self.files if f.client_id == client_id]

        return {
            'client': asdict(client),
            'active_cases': [asdict(c) for c in client_cases if c.case_status == 'Open'],
            'all_cases': [asdict(c) for c in client_cases],
            'payment_summary': {
                'total_paid': total_paid,
                'total_pending': total_pending,
                'total_overdue': total_overdue,
                'recent_payments': [asdict(p) for p in sorted(client_payments, key=lambda x: x.payment_date, reverse=True)[:5]]
            },
            'file_count': len(client_files),
            'recent_files': [asdict(f) for f in sorted(client_files, key=lambda x: x.last_accessed, reverse=True)[:5]],
            'all_files': [asdict(f) for f in sorted(client_files, key=lambda x: x.last_accessed, reverse=True)]
        }

# Initialize the file manager
file_manager = LegalFileManager()

@app.route('/')
def index():
    """Main dashboard"""
    total_files = len(file_manager.files)
    total_clients = len(file_manager.clients)
    total_cases = len(file_manager.cases)
    active_cases = len([c for c in file_manager.cases if c.case_status == 'Open'])
    
    recent_files = sorted(file_manager.files, key=lambda x: x.last_accessed, reverse=True)[:10]
    
    # Get recent file accesses for activity feed
    recent_accesses = file_manager.get_recent_file_accesses(limit=15)
    
    return render_template('dashboard.html', 
                         total_files=total_files,
                         total_clients=total_clients,
                         total_cases=total_cases,
                         active_cases=active_cases,
                         recent_files=recent_files,
                         recent_accesses=recent_accesses,
                         get_client_name=file_manager.get_client_name,
                         get_case_type=file_manager.get_case_type)

@app.route('/search')
def search():
    """Search page and results"""
    query = request.args.get('q', '')
    filters = {}
    
    # Extract filters from request
    for key in ['case_type', 'file_type', 'confidentiality_level', 'storage_status', 'warehouse_location']:
        value = request.args.get(key)
        if value:
            filters[key] = value
    
    results = file_manager.search_files(query, filters) if query or filters else []
    
    # Get unique values for filter dropdowns
    case_types = list(set(file_manager.get_case_type(f.case_id) for f in file_manager.files))
    file_types = list(set(f.file_type for f in file_manager.files))
    confidentiality_levels = list(set(f.confidentiality_level for f in file_manager.files))
    storage_statuses = list(set(f.storage_status for f in file_manager.files))
    warehouse_locations = list(set(f.warehouse_location for f in file_manager.files))
    
    return render_template('search.html',
                         query=query,
                         results=results,
                         filters=filters,
                         case_types=sorted(case_types),
                         file_types=sorted(file_types),
                         confidentiality_levels=sorted(confidentiality_levels),
                         storage_statuses=sorted(storage_statuses),
                         warehouse_locations=sorted(warehouse_locations),
                         get_client_name=file_manager.get_client_name,
                         get_case_type=file_manager.get_case_type)

@app.route('/file/<file_id>')
def file_detail(file_id):
    """File detail view"""
    file_record = next((f for f in file_manager.files if f.file_id == file_id), None)
    if not file_record:
        return "File not found", 404
    
    # Log file access
    user_agent = request.headers.get('User-Agent', 'Unknown')
    ip_address = request.remote_addr or '127.0.0.1'
    
    # For demo purposes, simulate different users based on session/time
    demo_users = [
        ('John Smith', 'Partner'), ('Sarah Johnson', 'Associate'), 
        ('Michael Brown', 'Paralegal'), ('Current User', 'Demo User')
    ]
    import hashlib
    user_hash = int(hashlib.md5(f"{ip_address}{user_agent}".encode()).hexdigest()[:8], 16)
    current_user_name, current_user_role = demo_users[user_hash % len(demo_users)]
    
    file_manager.log_file_access(
        file_id=file_id,
        user_name=current_user_name,
        user_role=current_user_role,
        access_type='view',
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    recommendations = file_manager.get_client_recommendations(file_record.client_id)
    
    # Get access history and stats
    access_history = file_manager.get_file_access_history(file_id)
    access_stats = file_manager.get_file_access_stats(file_id)
    
    # Sort access history by timestamp (most recent first)
    access_history.sort(key=lambda x: x.access_timestamp, reverse=True)
    
    return render_template('file_detail.html',
                         file=file_record,
                         recommendations=recommendations,
                         access_history=access_history,
                         access_stats=access_stats,
                         get_client_name=file_manager.get_client_name,
                         get_case_type=file_manager.get_case_type)

@app.route('/client/<client_id>')
def client_detail(client_id):
    """Client detail view with recommendations"""
    recommendations = file_manager.get_client_recommendations(client_id)
    if not recommendations:
        return "Client not found", 404
    
    return render_template('client_detail.html',
                         recommendations=recommendations)

@app.route('/api/search')
def api_search():
    """API endpoint for file-only search functionality (backward compatibility)"""
    query = request.args.get('q', '')
    filters = {}
    
    # Standard filters
    for key in ['case_type', 'file_type', 'confidentiality_level', 'storage_status', 'warehouse_location']:
        value = request.args.get(key)
        if value:
            filters[key] = value
    
    # Date range filters
    date_filters = ['created_from', 'created_to', 'accessed_from', 'accessed_to', 'modified_from', 'modified_to']
    for key in date_filters:
        value = request.args.get(key)
        if value:
            filters[key] = value
    
    results = file_manager.search_files(query, filters)
    
    # Format results for JSON response with additional client and case info
    formatted_results = []
    for file in results:
        file_dict = asdict(file)
        file_dict['client_name'] = file_manager.get_client_name(file.client_id)
        file_dict['case_type'] = file_manager.get_case_type(file.case_id)
        formatted_results.append(file_dict)
    
    return jsonify({
        'results': formatted_results,
        'count': len(results),
        'query': query,
        'filters': filters
    })

@app.route('/api/unified-search')
def api_unified_search():
    """API endpoint for unified search across all data types"""
    query = request.args.get('q', '')
    include_private = request.args.get('include_private', 'false').lower() == 'true'
    limit_per_category = int(request.args.get('limit', 10))  # Limit results per category
    
    filters = {}
    
    # Standard filters (apply only to file results)
    for key in ['case_type', 'file_type', 'confidentiality_level', 'storage_status', 'warehouse_location']:
        value = request.args.get(key)
        if value:
            filters[key] = value
    
    # Date range filters
    date_filters = ['created_from', 'created_to', 'accessed_from', 'accessed_to', 'modified_from', 'modified_to']
    for key in date_filters:
        value = request.args.get(key)
        if value:
            filters[key] = value
    
    # Log the search for intelligent suggestions
    if query:
        file_manager.log_search(query)
    
    # Get unified search results
    results = file_manager.unified_search(query, filters, include_private)
    
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

@app.route('/api/suggestions')
def api_suggestions():
    """API endpoint for intelligent search suggestions"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))
    
    # Get intelligent suggestions
    intelligent_suggestions = file_manager.get_intelligent_suggestions(query, limit)
    
    # Format for backward compatibility
    simple_suggestions = [s['text'] for s in intelligent_suggestions['suggestions']]
    
    return jsonify({
        'suggestions': simple_suggestions,
        'intelligent': intelligent_suggestions,
        'query': query
    })

@app.route('/api/intelligent-suggestions')
def api_intelligent_suggestions():
    """API endpoint for advanced intelligent suggestions with categories"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 12))
    include_categories = request.args.get('categories', 'true').lower() == 'true'
    
    suggestions_data = file_manager.get_intelligent_suggestions(query, limit)
    
    if include_categories:
        return jsonify(suggestions_data)
    else:
        return jsonify({
            'suggestions': suggestions_data['suggestions'],
            'query': query
        })

@app.route('/api/filter-options')
def api_filter_options():
    """API endpoint to get available filter options"""
    case_types = list(set(file_manager.get_case_type(f.case_id) for f in file_manager.files))
    file_types = list(set(f.file_type for f in file_manager.files))
    confidentiality_levels = list(set(f.confidentiality_level for f in file_manager.files))
    storage_statuses = list(set(f.storage_status for f in file_manager.files))
    warehouse_locations = list(set(f.warehouse_location for f in file_manager.files))
    
    return jsonify({
        'case_types': sorted(case_types),
        'file_types': sorted(file_types),
        'confidentiality_levels': sorted(confidentiality_levels),
        'storage_statuses': sorted(storage_statuses),
        'warehouse_locations': sorted(warehouse_locations)
    })

@app.route('/api/access-history/<file_id>')
def api_access_history(file_id):
    """API endpoint to get access history for a specific file"""
    access_history = file_manager.get_file_access_history(file_id)
    access_stats = file_manager.get_file_access_stats(file_id)
    
    return jsonify({
        'file_id': file_id,
        'access_history': [asdict(access) for access in access_history],
        'access_stats': access_stats
    })

@app.route('/api/recent-activity')
def api_recent_activity():
    """API endpoint to get recent file access activity"""
    limit = int(request.args.get('limit', 20))
    recent_accesses = file_manager.get_recent_file_accesses(limit)
    
    return jsonify({
        'recent_accesses': [asdict(access) for access in recent_accesses],
        'count': len(recent_accesses)
    })

if __name__ == '__main__':
    app.run(debug=True)
