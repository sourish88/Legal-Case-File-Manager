# Legal Case File Manager

A comprehensive web application designed for legal service providers to catalogue and manage physical files stored in warehouses. Built with Python Flask and Jinja2 templates.

## Features

### 🔍 Dynamic Search Functionality
- **Multi-criteria Search**: Search by reference number, client details, case type, keywords, and more
- **Advanced Filtering**: Filter by case type, file type, confidentiality level, warehouse location, and storage status
- **Real-time Results**: Instant search results with comprehensive file information

### 📊 Dashboard & Analytics
- **Overview Statistics**: Total files, clients, cases, and active cases at a glance
- **Recent Activity**: Recently accessed files with quick access links
- **Quick Search**: Fast search functionality directly from the dashboard

### 👥 Client Management
- **Client Profiles**: Comprehensive client information including personal details and contact information
- **Case History**: Complete case history for each client with status tracking
- **Payment Tracking**: Payment summaries with paid, pending, and overdue amounts
- **Document Associations**: Links to all related files and documents

### 📁 File Cataloging
- **Detailed File Records**: Complete file information including metadata and descriptions
- **Warehouse Location Tracking**: Precise location mapping with warehouse, shelf, and box numbers
- **Confidentiality Levels**: Security classification system for sensitive documents
- **Storage Status**: Track file lifecycle from active to archived

### 💡 Smart Recommendations
- **Related Cases**: Show other active and closed cases for the same client
- **Payment Insights**: Financial summary and payment history
- **Document Associations**: Related files and cross-references

## Technology Stack

- **Backend**: Python 3.7+ with Flask framework
- **Templates**: Jinja2 for server-side rendering
- **Frontend**: Bootstrap 5 with custom CSS and JavaScript
- **Data Generation**: Faker library for realistic sample data
- **Icons**: Font Awesome for consistent iconography

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Quick Start

1. **Clone the repository** (or use the provided files):
   ```bash
   cd "AI Architect Training"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database and generate sample data**:
   ```bash
   # Quick setup with default settings
   python setup_dev_environment.py
   
   # Or manual setup
   python database_setup.py
   python generate_dummy_data.py --count 50 --clear
   ```

4. **Run the application**:
   ```bash
   python app_postgresql.py
   ```

5. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## Application Structure

```
├── app_postgresql.py      # Main Flask application (PostgreSQL)
├── database.py           # Database connection and queries
├── database_setup.py     # Database schema creation
├── generate_dummy_data.py # Dummy data generator for development
├── setup_dev_environment.py # Complete development setup script
├── add_performance_indexes.py # Database performance optimization
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── templates/            # Jinja2 templates
│   ├── base.html        # Base template with common layout
│   ├── dashboard.html   # Main dashboard
│   ├── search.html      # Search interface and results
│   ├── file_detail.html # Individual file details
│   └── client_detail.html # Client profile and recommendations
└── static/              # Static assets
    ├── style.css        # Custom CSS styles
    └── script.js        # JavaScript functionality
```

## Data Models

### Client
- Personal information (name, email, phone, address)
- Client type (Individual, Corporation, Non-Profit)
- Registration date and status

### Case
- Reference numbers and case types
- Assigned lawyers and priority levels
- Status tracking and estimated values
- Creation and update timestamps

### Physical File
- Unique file identifiers and reference numbers
- Document categories and types
- Precise warehouse locations (warehouse, shelf, box)
- Storage status and confidentiality levels
- Keywords and descriptions for searchability

### Payment
- Payment amounts, dates, and methods
- Status tracking (Paid, Pending, Overdue)
- Links to specific cases and clients

## Key Features Explained

### Search Functionality
The application provides multiple search methods:
- **Text Search**: Searches across multiple fields including reference numbers, descriptions, client names, and keywords
- **Filter-based Search**: Dropdown filters for case types, file types, confidentiality levels, and warehouse locations
- **Combined Search**: Use both text and filters simultaneously for precise results

### Client Recommendations
When viewing a file or client, the system provides:
- **Active Cases**: All currently open cases for the client
- **Payment Summary**: Financial overview with totals and recent transactions
- **Related Files**: Recently accessed files for the client
- **Case History**: Complete history of all cases

### Warehouse Management
Physical file tracking includes:
- **Location Hierarchy**: Warehouse → Shelf → Box structure
- **Visual Location Display**: Easy-to-read location cards
- **Storage Status**: Track file lifecycle and accessibility
- **Size Classification**: File size categories for space planning

## Sample Data

The application automatically generates comprehensive sample data including:
- **50 Clients** with realistic personal information
- **100 Cases** across various legal practice areas
- **200 Physical Files** with complete metadata
- **150 Payment Records** with various statuses and amounts

Practice areas include:
- Personal Injury
- Corporate Law
- Criminal Defense
- Family Law
- Real Estate
- Employment Law
- Immigration
- Intellectual Property
- Tax Law
- Environmental Law
- Contract Disputes
- Bankruptcy

## API Endpoints

### Web Routes
- `GET /` - Main dashboard
- `GET /search` - Search interface and results
- `GET /file/<file_id>` - File detail view
- `GET /client/<client_id>` - Client profile and recommendations

### API Routes
- `GET /api/search` - JSON search API with query and filter parameters

## Customization

### Adding New Search Criteria
To add new search fields, modify the `search_files` method in `database.py`:
```python
def search_files(self, query: str, filters: Dict[str, Any] = None) -> List[PhysicalFile]:
    # Add new search logic here
```

### Extending Data Models
Add new fields to the dataclasses and update the sample data generation in the `generate_sample_data` method.

### Custom Styling
Modify `static/style.css` to customize the appearance. The application uses CSS custom properties for easy theme customization.

## Security Features

- **Confidentiality Levels**: Four-tier classification system (Public, Internal, Confidential, Highly Confidential)
- **Access Tracking**: Last accessed timestamps for audit trails
- **Client Privacy**: Sensitive information properly categorized and displayed

## Performance Considerations

- **Efficient Search**: Optimized search algorithms for quick results
- **Responsive Design**: Mobile-friendly interface
- **Minimal Dependencies**: Lightweight Flask application
- **Caching Ready**: Structure supports caching implementation

## Future Enhancements

Potential areas for expansion:
- Database integration (PostgreSQL, MySQL, SQLite)
- User authentication and role-based access
- Document upload and digital file management
- Barcode/QR code integration for physical files
- Advanced reporting and analytics
- Integration with legal practice management systems
- Mobile app for warehouse staff

## Contributing

This is a demonstration application. For production use, consider:
- Implementing proper data persistence
- Adding user authentication
- Implementing proper error handling
- Adding comprehensive logging
- Setting up proper deployment configuration

## License

This project is for demonstration purposes. Adapt as needed for your specific use case.

---

**Note**: This application uses sample data for demonstration purposes. In a production environment, you would integrate with your actual client database and implement proper data security measures.
