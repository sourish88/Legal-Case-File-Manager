"""
Data models and entities for the Legal Case File Manager.

This module defines the data structures used throughout the application.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Client:
    """Client entity model"""
    client_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    client_type: str = 'Individual'  # Individual, Corporation, Non-Profit
    status: str = 'Active'  # Active, Inactive, Archived
    registration_date: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None
    notes: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get the client's full name"""
        return f"{self.first_name} {self.last_name}"


@dataclass
class Case:
    """Case entity model"""
    case_id: str
    client_id: str
    reference_number: str
    case_type: str
    description: Optional[str] = None
    assigned_lawyer: Optional[str] = None
    case_status: str = 'Open'  # Open, Closed, On Hold, Under Review
    priority: str = 'Medium'  # Low, Medium, High, Urgent
    estimated_value: Optional[float] = None
    created_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class PhysicalFile:
    """Physical file entity model"""
    file_id: str
    client_id: str
    case_id: Optional[str]
    reference_number: str
    file_description: Optional[str] = None
    document_category: Optional[str] = None
    file_type: str = 'Legal Document'
    file_size: str = 'Medium'  # Small, Medium, Large, Extra Large
    warehouse_location: str = 'Warehouse A'
    shelf_number: Optional[str] = None
    box_number: Optional[str] = None
    storage_status: str = 'Active'  # Active, Archived, Disposed, Missing
    confidentiality_level: str = 'Internal'  # Public, Internal, Confidential, Highly Confidential
    keywords: Optional[List[str]] = None
    created_date: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    notes: Optional[str] = None


@dataclass
class Payment:
    """Payment entity model"""
    payment_id: str
    client_id: str
    case_id: Optional[str]
    amount: float
    payment_date: Optional[datetime] = None
    payment_method: str = 'Bank Transfer'  # Cash, Check, Bank Transfer, Credit Card, Other
    status: str = 'Pending'  # Paid, Pending, Overdue, Cancelled
    description: Optional[str] = None
    invoice_number: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class FileAccess:
    """File access tracking entity model"""
    access_id: str
    file_id: str
    user_name: str
    user_role: Optional[str] = None
    access_timestamp: Optional[datetime] = None
    access_type: str = 'view'  # view, download, edit, print
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_duration: Optional[int] = None  # in minutes
    notes: Optional[str] = None


@dataclass
class SearchQuery:
    """Search query tracking entity model"""
    query_id: str
    query_text: str
    session_id: str
    search_timestamp: Optional[datetime] = None
    results_count: int = 0
    filters_used: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None  # in milliseconds


@dataclass
class Comment:
    """Comment entity model"""
    comment_id: str
    file_id: Optional[str] = None
    client_id: Optional[str] = None
    case_id: Optional[str] = None
    user_name: str = 'System'
    comment_text: str = ''
    comment_type: str = 'General'  # General, Important, Private, System
    created_date: Optional[datetime] = None
    is_private: bool = False
    priority: str = 'Normal'  # Low, Normal, High, Critical


# Type aliases for common data structures
ClientDict = Dict[str, Any]
CaseDict = Dict[str, Any]
FileDict = Dict[str, Any]
PaymentDict = Dict[str, Any]
AccessDict = Dict[str, Any]
SearchDict = Dict[str, Any]
CommentDict = Dict[str, Any]

# Common constants
CLIENT_TYPES = ['Individual', 'Corporation', 'Non-Profit', 'Government', 'Other']
CLIENT_STATUSES = ['Active', 'Inactive', 'Archived', 'Suspended']
CASE_TYPES = [
    'Personal Injury', 'Corporate Law', 'Criminal Defense', 'Family Law',
    'Real Estate', 'Employment Law', 'Immigration', 'Intellectual Property',
    'Tax Law', 'Environmental Law', 'Contract Disputes', 'Bankruptcy'
]
CASE_STATUSES = ['Open', 'Closed', 'On Hold', 'Under Review', 'Pending']
PRIORITY_LEVELS = ['Low', 'Medium', 'High', 'Urgent']
FILE_TYPES = [
    'Legal Document', 'Contract', 'Court Filing', 'Evidence', 'Correspondence',
    'Financial Record', 'Medical Record', 'Other'
]
FILE_SIZES = ['Small', 'Medium', 'Large', 'Extra Large']
STORAGE_STATUSES = ['Active', 'Archived', 'Disposed', 'Missing', 'In Transit']
CONFIDENTIALITY_LEVELS = ['Public', 'Internal', 'Confidential', 'Highly Confidential']
PAYMENT_METHODS = ['Cash', 'Check', 'Bank Transfer', 'Credit Card', 'Other']
PAYMENT_STATUSES = ['Paid', 'Pending', 'Overdue', 'Cancelled', 'Refunded']
ACCESS_TYPES = ['view', 'download', 'edit', 'print', 'delete', 'create']
COMMENT_TYPES = ['General', 'Important', 'Private', 'System', 'Reminder']
