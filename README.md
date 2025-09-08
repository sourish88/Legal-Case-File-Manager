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

### 🔄 Data Pipeline Generation & Migration
- **Terraform Infrastructure**: Generate cloud infrastructure code (AWS, Azure) for data migration
- **AI-Powered Schema Analysis**: Intelligent database schema analysis and field mapping recommendations
- **Custom Field Mappings**: Configure custom field transformations for data migration
- **Persistent Job History**: Complete audit trail of all data pipeline generation jobs with status tracking
- **Real-time Progress Monitoring**: Track job progress and status updates
- **Cost Estimation**: Estimate cloud infrastructure costs for migration projects

## Technology Stack

- **Backend**: Python 3.8+ with Flask framework
- **Database**: PostgreSQL with psycopg2 driver
- **Templates**: Jinja2 for server-side rendering
- **Frontend**: Bootstrap 5 with custom CSS and JavaScript
- **Data Generation**: Faker library for realistic sample data
- **Icons**: Font Awesome for consistent iconography

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12+ database server
- pip (Python package installer)

### Database Setup

1. **Install PostgreSQL**:
   - **Windows**: Download from [postgresql.org](https://www.postgresql.org/download/)
   - **macOS**: `brew install postgresql`
   - **Ubuntu**: `sudo apt-get install postgresql postgresql-contrib`

2. **Create Database**:
   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql
   
   # Create database and user
   CREATE DATABASE legal_case_manager;
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE legal_case_manager TO postgres;
   \q
   ```

3. **Configure Environment**:
   ```bash
   cp env_template.txt .env
   # Edit .env with your database credentials
   ```

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd "Legal Case File Manager"
   ```

2. **Set up PostgreSQL** (if not already installed):
   - Install PostgreSQL 12+ on your system
   - Create database: `legal_case_manager`
   - Ensure PostgreSQL service is running

3. **Configure environment**:
   ```bash
   cp env_template.txt .env
   # Edit .env with your database credentials
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up database and generate sample data**:
   ```bash
   # Complete setup with default settings
   python scripts/setup_dev_environment.py
   
   # Or manual setup
   python scripts/database_setup.py
   python scripts/generate_dummy_data.py --count 50 --clear
   ```

6. **Run the application**:
   ```bash
   python run.py
   ```
   
   Or use the Makefile:
   ```bash
   make run
   ```

7. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## Environment Configuration

### Setting Up Environment Variables

1. **Copy environment template**:
   ```bash
   cp env_template.txt .env
   ```

2. **Configure your settings** in `.env`:
   ```bash
   # Database Configuration
   DB_HOST=localhost          # PostgreSQL server host
   DB_PORT=5432              # PostgreSQL server port
   DB_NAME=legal_case_manager # Database name
   DB_USER=postgres          # Database username
   DB_PASSWORD=your_password_here # Database password
   
   # Application Configuration
   SECRET_KEY=your-secret-key-here # Flask secret key for sessions
   FLASK_ENV=development     # Environment (development/production)
   FLASK_DEBUG=True         # Enable debug mode
   
   # Optional: Application Settings
   APP_HOST=0.0.0.0         # Host to bind the application
   APP_PORT=5000            # Port to run the application
   ```

### Environment Variables Explained

- **DB_HOST**: PostgreSQL database server hostname or IP address
- **DB_PORT**: PostgreSQL server port (default: 5432)
- **DB_NAME**: Name of the database to connect to
- **DB_USER**: PostgreSQL username for authentication
- **DB_PASSWORD**: PostgreSQL password for authentication
- **SECRET_KEY**: Flask secret key for session management and security
- **FLASK_ENV**: Application environment (development/production)
- **FLASK_DEBUG**: Enable/disable debug mode for development
- **APP_HOST**: Network interface to bind the application (0.0.0.0 for all interfaces)
- **APP_PORT**: Port number for the web application

## Application Structure

```
├── app/                    # Main application package
│   ├── __init__.py        # Application factory
│   ├── config/            # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py    # Environment-specific settings
│   ├── models/            # Data models and entities
│   │   ├── __init__.py
│   │   └── entities.py    # Data classes and constants
│   ├── services/          # Business logic layer
│   │   ├── __init__.py
│   │   ├── database.py    # Database connection and queries
│   │   ├── client_service.py # Client-related business logic
│   │   └── search_service.py # Search functionality
│   ├── utils/             # Utility functions
│   │   ├── __init__.py
│   │   └── helpers.py     # Helper functions
│   └── views/             # Web routes and API endpoints
│       ├── __init__.py
│       ├── main.py        # Main web routes
│       ├── api.py         # API endpoints
│       ├── errors.py      # Error handlers
│       └── migration.py   # Migration routes (optional)
├── scripts/               # Setup and utility scripts
│   ├── database_setup.py     # Database schema creation
│   ├── generate_dummy_data.py # Dummy data generator
│   ├── setup_dev_environment.py # Development environment setup
│   └── add_performance_indexes.py # Database optimization
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Test configuration
│   └── test_basic.py      # Basic tests
├── templates/             # Jinja2 templates
│   ├── base.html         # Base template
│   ├── dashboard.html    # Main dashboard
│   ├── search.html       # Search interface
│   ├── file_detail.html  # File details
│   └── client_detail.html # Client profile
├── static/               # Static assets
│   ├── style.css        # Custom CSS styles
│   └── script.js        # JavaScript functionality
├── run.py               # Application entry point
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development dependencies
├── Makefile            # Development commands
├── pyproject.toml      # Tool configuration
├── .flake8            # Linting configuration
├── .pre-commit-config.yaml # Pre-commit hooks
└── README.md          # This file
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

The application generates comprehensive sample data including:
- **Clients**: Configurable number (default: 50) with realistic personal information
- **Cases**: Approximately 2x client count across various legal practice areas
- **Physical Files**: Approximately 4x client count with complete metadata
- **Payment Records**: Approximately 3x client count with various statuses and amounts
- **Access History**: Generated based on file interactions

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
- `GET /health` - Health check endpoint

### API Routes
- `GET /api/search` - JSON search API with query and filter parameters
- `GET /api/unified-search` - Unified search across all data types
- `GET /api/intelligent-suggestions` - Smart search suggestions
- `GET /api/stats` - Dashboard statistics
- `GET /api/filters` - Available filter options
- `GET /api/recent-activity` - Recent file access activity
- `GET /api/access-history/<file_id>` - File access history

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
- User authentication and role-based access control
- Document upload and digital file management
- Barcode/QR code integration for physical files
- Advanced reporting and analytics dashboard
- Integration with legal practice management systems
- Mobile app for warehouse staff
- Multi-tenant support for law firms
- Automated backup and disaster recovery
- Advanced search with natural language processing

## Development

### Development Setup

For development, use the comprehensive setup command:

```bash
make dev-setup
```

This will:
- Install all dependencies (production + development)
- Set up pre-commit hooks for code quality
- Initialize the database with sample data

### Development Commands

```bash
# Install dependencies
make install-dev

# Run the application in development mode
make run

# Run tests
make test

# Format code
make format

# Run linting
make lint

# Clean up cache files
make clean

# Set up database with sample data
make setup-db
```

### Code Quality

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing
- **pre-commit**: Git hooks for automatic checks

### Project Structure

The application follows Flask best practices with a clear separation of concerns:

- **`app/`**: Main application package using the application factory pattern
- **`app/config/`**: Configuration management with environment-specific settings
- **`app/models/`**: Data models and entity definitions
- **`app/services/`**: Business logic layer (database, search, client services)
- **`app/utils/`**: Utility functions and helpers
- **`app/views/`**: Web routes and API endpoints organized by functionality
- **`scripts/`**: Setup and utility scripts
- **`tests/`**: Test suite with pytest configuration

## Troubleshooting

### Common Issues

#### Database Connection Error
```bash
Error: Failed to connect to database
psycopg2.OperationalError: could not connect to server
```
**Solutions**:
- Ensure PostgreSQL service is running: `sudo service postgresql start`
- Verify database credentials in `.env` file
- Check if database `legal_case_manager` exists
- Confirm PostgreSQL is listening on the correct port (default: 5432)

#### Port Already in Use
```bash
Error: [Errno 48] Address already in use
```
**Solutions**:
- Change the port in `.env`: `APP_PORT=5001`
- Kill the process using the port: `lsof -ti:5000 | xargs kill -9`
- Stop other Flask applications running on the same port

#### Missing Dependencies
```bash
ModuleNotFoundError: No module named 'psycopg2'
```
**Solutions**:
- Install dependencies: `pip install -r requirements.txt`
- For development: `make install-dev`
- On macOS, you may need: `brew install postgresql`
- On Ubuntu, you may need: `sudo apt-get install python3-dev libpq-dev`

#### Permission Denied (Database)
```bash
psycopg2.OperationalError: FATAL: permission denied for database
```
**Solutions**:
- Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE legal_case_manager TO postgres;`
- Check PostgreSQL user permissions
- Ensure the database user exists and has correct password

#### Sample Data Generation Fails
```bash
Error during sample data generation
```
**Solutions**:
- Ensure database tables are created: `python scripts/database_setup.py`
- Clear existing data: `python scripts/generate_dummy_data.py --clear`
- Check database connection and permissions

## Production Deployment

### Environment Setup
1. Set `FLASK_ENV=production` in your environment
2. Use a strong, unique `SECRET_KEY`
3. Configure proper PostgreSQL connection settings with secure credentials
4. Set up reverse proxy (nginx/Apache) for static files and SSL termination
5. Use a WSGI server (Gunicorn/uWSGI) instead of Flask development server
6. Enable PostgreSQL connection pooling for better performance
7. Set up proper logging and monitoring
8. Configure automated backups for the database

### Example Production Deployment with Gunicorn
```bash
# Install Gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:8000 run:app

# With better configuration
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 --keep-alive 5 run:app
```

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure secure database credentials
- [ ] Set up SSL/HTTPS
- [ ] Configure proper logging
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Test error handling and recovery
- [ ] Set up log rotation
- [ ] Configure firewall rules

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
