# Dummy Data Generator for Legal Case File Manager

This script generates realistic dummy data for the PostgreSQL database, making it easy to set up development and testing environments.

## Features

- **Realistic Data**: Uses Faker library to generate believable client names, addresses, emails, etc.
- **Proper Relationships**: Maintains foreign key relationships between clients, cases, files, and payments
- **Configurable**: Customizable number of clients and database connection parameters
- **Safe Operations**: Option to clear existing data or append to current data
- **Comprehensive**: Generates data for all tables including access logs and comments
- **Statistics**: Provides detailed summary of generated data

## Quick Start

### Basic Usage
```bash
# Generate 50 clients with associated data
python generate_dummy_data.py

# Generate 100 clients with associated data
python generate_dummy_data.py --count 100

# Clear existing data and generate fresh data
python generate_dummy_data.py --clear --count 75
```

### Advanced Usage
```bash
# Custom database connection
python generate_dummy_data.py \
    --host localhost \
    --port 5432 \
    --database legal_case_manager \
    --user postgres \
    --password your_password \
    --count 200 \
    --clear
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--count N` | Number of clients to generate | 50 |
| `--clear` | Clear existing data before generating | False |
| `--host` | Database host | localhost |
| `--port` | Database port | 5432 |
| `--database` | Database name | legal_case_manager |
| `--user` | Database username | postgres |
| `--password` | Database password | postgres |

## Generated Data Overview

### Data Relationships
```
Clients (1:N) → Cases (1:N) → Physical Files
                     ↓
Cases (1:N) → Payments
Physical Files (1:N) → Access Logs
Physical Files (1:N) → Comments
```

### Data Volume (per 50 clients)
- **Clients**: 50
- **Cases**: ~100-200 (1-4 per client)
- **Physical Files**: ~200-600 (1-3 per case)
- **Payments**: ~0-1000 (0-5 per case)
- **Access Logs**: ~0-6000 (0-10 per file)
- **Comments**: ~0-3000 (0-5 per file)

### Data Types Generated

#### Clients
- Individual persons with realistic names
- Corporations with company names + LLC/Inc/Corp
- Non-profits with foundation/trust names
- Government entities
- Complete contact information
- Registration dates spanning 5 years

#### Cases
- 12 different case types (Civil, Criminal, Family, etc.)
- 5 status types (Active, Pending, Closed, etc.)
- Assigned to 12 different lawyers
- Case values from $1,000 to $500,000
- Realistic descriptions

#### Physical Files
- Proper reference numbering system
- 5 different storage locations
- Keyword arrays for searchability
- Confidentiality levels
- Document counts and file sizes
- Retention dates

#### Payments
- 5 payment methods
- 4 payment statuses
- Invoice numbers
- Processing information
- Amounts from $100 to $10,000

#### Access Logs & Comments
- Realistic access patterns
- IP addresses
- Multiple access types
- Internal/external comments
- Priority levels

## Sample Output

```
============================================================
DUMMY DATA GENERATION COMPLETE!
============================================================
📊 STATISTICS:
  • Clients:          50 (42 active)
  • Cases:            127 (89 active)
  • Physical Files:   284
  • Payments:         387
  • Access Logs:      1,247
  • Comments:         623

💰 FINANCIAL:
  • Total Case Value: $12,847,392.45
  • Total Payments:   $1,923,847.23

🎯 CASE TYPES:
  • Bankruptcy: 8
  • Civil Litigation: 15
  • Corporate Law: 12
  • Criminal Defense: 9
  • Employment Law: 7
  • Estate Planning: 11
  • Family Law: 13
  • Immigration: 10
  • Intellectual Property: 6
  • Personal Injury: 14
  • Real Estate: 12
  • Tax Law: 10
============================================================
```

## Safety Features

1. **Foreign Key Respect**: Generates data in proper order to maintain referential integrity
2. **Transaction Safety**: Uses database transactions with rollback on errors
3. **Sequence Reset**: Optionally resets auto-increment sequences when clearing data
4. **Error Handling**: Comprehensive error handling with detailed logging
5. **Connection Management**: Proper database connection lifecycle management

## Development Tips

### Testing Different Scenarios
```bash
# Small dataset for quick testing
python generate_dummy_data.py --count 10 --clear

# Large dataset for performance testing
python generate_dummy_data.py --count 500 --clear

# Add more data to existing dataset
python generate_dummy_data.py --count 25
```

### Customizing Data Types
The script can be easily modified to add new:
- Case types
- Client types
- Payment methods
- File locations
- Lawyer names

Simply edit the arrays at the top of the `PostgreSQLDummyDataGenerator` class.

## Prerequisites

1. PostgreSQL database running
2. Database schema created (run `database_setup.py` first)
3. Required Python packages installed:
   ```bash
   pip install -r requirements.txt
   ```

## Integration with Development Workflow

1. **Fresh Setup**: `python database_setup.py` → `python generate_dummy_data.py --clear`
2. **Reset Data**: `python generate_dummy_data.py --clear --count 100`
3. **Add More Data**: `python generate_dummy_data.py --count 50`
4. **Performance Testing**: `python generate_dummy_data.py --clear --count 1000`

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check database is running and credentials are correct
2. **Foreign Key Errors**: Ensure database schema is properly created
3. **Permission Denied**: Check user has INSERT permissions on all tables
4. **Sequence Errors**: May occur if tables have existing data with higher IDs

### Debug Mode
Add logging level for more detailed output:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- Support for custom data templates
- Export/import of generated datasets
- Integration with testing frameworks
- Performance benchmarking tools
- Data anonymization features
