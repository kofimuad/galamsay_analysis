# Galamsay Analysis - OFWA Coding Test

A RESTful API for analyzing illegal small-scale mining (Galamsay) data in Ghana using FastAPI and PostgreSQL.

## Project Overview

This project implements a complete data analysis pipeline with a RESTful API:
1. **Data Analysis** (`analyze_data.py`) - Cleans raw CSV data and performs statistical analysis
2. **RESTful API** (`api.py`) - Exposes analysis results via HTTP endpoints
3. **Database** - Stores analysis records with full audit trail
4. **Tests** (`test_galamsay.py`) - Comprehensive test coverage

### Key Features
- ✅ Data cleaning and validation with error handling
- ✅ Multiple analysis metrics (total sites, regional averages, city rankings)
- ✅ RESTful API with detailed documentation
- ✅ Full audit trail (multiple analysis runs stored with timestamps)
- ✅ Comprehensive test suite
- ✅ PostgreSQL (or SQLite for development)

## Project Structure

```
galamsay-analysis/
├── models.py              # Database models (shared by analysis and API)
├── analyze_data.py        # Data analysis script (run first)
├── api.py                 # FastAPI server (run second)
├── test_galamsay.py       # Test suite
├── galamsay_data.csv      # Input data
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── .gitignore             # Git ignore file
```

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/galamsay-analysis.git
cd galamsay-analysis
```

### 2. Create Virtual Environment

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Prepare Your Data

Place your `galamsay_data.csv` file in the project root directory. Expected format:

```csv
City,Region,Number_of_Galamsay_Sites
Accra,Greater Accra,30
Kumasi,Ashanti,25
Takoradi,Western,18
...
```

## Usage

### Step 1: Run Data Analysis

The analysis script reads the CSV, cleans the data, and saves results to the database.

```bash
python analyze_data.py
```

**What it does:**
- Reads `galamsay_data.csv`
- Validates and cleans data (removes invalid records)
- Calculates metrics:
  - Total galamsay sites across all cities
  - Region with highest number of sites
  - Cities exceeding threshold (10 sites)
  - Average sites per region
- Saves results to database with timestamp
- Prints detailed analysis report and data quality summary

**Example Output:**
```
============================================================
GALAMSAY DATA ANALYSIS
============================================================
✓ Loaded 50 records from CSV
✓ Cleaned data: 48 valid records (removed 2 invalid records)

============================================================
ANALYSIS RESULTS
============================================================
Total Galamsay Sites: 485
Region with Highest Sites: Ashanti (95 sites)
Average Sites per Region: 19.40

Cities Exceeding Threshold (10 sites):
  - Accra (Greater Accra): 30 sites
  - Kumasi (Ashanti): 25 sites
  ...

Data Quality Report:
  Valid records: 48
  Data cleaning errors/warnings: 2
```

### Step 2: Run FastAPI Server

After analysis completes, start the API server:

```bash
uvicorn api:app --reload
```

The server starts at `http://localhost:8000`

**Key Endpoints:**

- **Root Info**: `GET /` - List all available endpoints
- **Latest Analysis**: `GET /analyses/latest` - Get most recent analysis with all details
- **All Analyses**: `GET /analyses` - List all analysis runs (paginated)
- **Analysis Detail**: `GET /analyses/{id}` - Get specific analysis by ID
- **Total Sites**: `GET /metrics/total-sites` - Total galamsay sites
- **Region with Most Sites**: `GET /metrics/region-highest` - Region with highest count
- **Average per Region**: `GET /metrics/average-per-region` - Average sites per region
- **Cities Exceeding Threshold**: `GET /metrics/cities-exceeding-threshold` - Cities > 10 sites
- **City Data**: `GET /city/{city_name}` - Get data for specific city
- **Region Data**: `GET /region/{region_name}` - Get all cities in a region
- **Health Check**: `GET /health` - Database connection status

### Step 3: Access Interactive Documentation

Open your browser and visit: **http://localhost:8000/docs**

This shows the Swagger UI where you can test all endpoints interactively.

### Example API Calls

```bash
# Get latest analysis
curl http://localhost:8000/analyses/latest

# Get total sites
curl http://localhost:8000/metrics/total-sites

# Get cities exceeding threshold
curl http://localhost:8000/metrics/cities-exceeding-threshold

# Get data for Ashanti region
curl http://localhost:8000/region/Ashanti

# Get data for Accra city
curl http://localhost:8000/city/Accra
```

## Running Tests

Run the complete test suite:

```bash
pytest test_galamsay.py -v
```

Run with coverage report:

```bash
pytest test_galamsay.py -v --cov=. --cov-report=html
```

Then open `htmlcov/index.html` to see coverage report.

### Test Coverage

Tests cover:
- **Data Cleaning**: Valid/invalid rows, whitespace handling, edge cases
- **CSV Loading**: File reading, error handling
- **Analysis**: Pipeline integration, calculation accuracy
- **API Endpoints**: Response structure and status codes
- **Edge Cases**: Zero values, very large numbers, empty data

**Example Test Output:**
```
test_galamsay.py::TestDataCleaning::test_clean_valid_row PASSED
test_galamsay.py::TestDataCleaning::test_clean_row_rejects_unknown_city PASSED
test_galamsay.py::TestAnalysis::test_analysis_handles_dirty_data PASSED
test_galamsay.py::TestAPI::test_root_endpoint PASSED

======================== 25 passed in 0.45s ========================
```

## Database Configuration

### For Local Development (SQLite)

Default configuration uses SQLite. No additional setup needed.

```python
# In models.py
DATABASE_URL = "sqlite:///./galamsay.db"
```

### For Production (PostgreSQL/Supabase)

Update `get_database_url()` in `models.py`:

```python
def get_database_url():
    return "postgresql://user:password@host:5432/database"
```

Or use environment variables:

```python
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./galamsay.db")
```

Create tables before first run:

```python
from models import create_tables
create_tables()
```

## Data Cleaning Logic

The analysis script validates data with the following rules:

✅ **Valid Record**
- City name is not empty and not "Unknown City"
- Region name is not empty and not "Invalid Region"
- Number of sites is a valid integer (no text like "abc", "eleven")
- Number of sites is non-negative (≥ 0)

❌ **Invalid Record** (will be removed)
- Missing or unknown city: `Unknown City`
- Invalid region: `Invalid Region`
- Non-numeric sites: `abc`, `eleven`, `1.5`
- Negative sites: `-5`
- Empty fields

⚠️ **Flagged as Warning** (included but noted)
- Suspiciously high values: `> 200 sites`

## Project Architecture

### Separation of Concerns

The project follows the principle of **separation of concerns**:

```
CSV Data
   ↓
[analyze_data.py] ← Data cleaning & validation
   ↓
Database ← Stores analysis results (audit trail)
   ↓
[api.py] ← Serves data via HTTP
   ↓
Client/Browser
```

**Why separate files?**
- Analysis logic is independent of HTTP requests
- Can run analysis on schedule (cron) while API runs 24/7
- Each component is testable in isolation
- Clear, modular code structure

### Database Schema

**analysis_runs**
- Stores metadata about each analysis run
- One row per execution
- Contains calculated metrics and timestamp

**city_data**
- Stores cleaned city-level data
- Linked to parent analysis run
- Preserves the exact data that was analyzed

**cities_exceeding_threshold**
- Pre-computed list of cities over threshold
- Linked to parent analysis run
- Enables fast API queries

## Git Workflow

### Initial Setup

```bash
git init
git add .
git commit -m "Initial commit: Project structure and core files"
```

### Meaningful Commit Messages

```bash
# After adding data cleaning logic
git add models.py analyze_data.py
git commit -m "feat: Add data cleaning with validation rules"

# After implementing API endpoints
git add api.py
git commit -m "feat: Implement RESTful API endpoints with FastAPI"

# After writing tests
git add test_galamsay.py
git commit -m "test: Add comprehensive test suite with edge cases"
```

### Push to GitHub

```bash
git remote add origin https://github.com/yourusername/galamsay-analysis.git
git branch -M main
git push -u origin main
```

## Technologies Used

- **FastAPI** - Web framework for building APIs
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL/SQLite** - Relational database
- **Pydantic** - Data validation and serialization
- **Pytest** - Testing framework

## Requirements

See `requirements.txt`:

```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pytest==7.4.3
pytest-cov==4.1.0
```

## Submission Checklist

Before submitting, ensure:

- ✅ `analyze_data.py` runs without errors
- ✅ `api.py` starts and serves documentation at `/docs`
- ✅ All tests pass: `pytest test_galamsay.py -v`
- ✅ Git history has at least 3 meaningful commits
- ✅ README explains setup and usage
- ✅ Data is properly cleaned (invalid records removed)
- ✅ All required metrics are calculated and exposed via API

## Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
Install dependencies: `pip install -r requirements.txt`

### "FileNotFoundError: galamsay_data.csv"
Ensure `galamsay_data.csv` is in the project root directory.

### API returns "No analysis runs found"
Run `python analyze_data.py` first to populate the database.

### Port 8000 already in use
Use a different port: `uvicorn api:app --port 8001`

### PostgreSQL connection errors
Check your connection string in `models.py` and database credentials.

## Future Enhancements

Potential improvements:
- Add city-level filtering and search
- Implement region-level aggregations
- Add export to CSV/Excel
- Create admin dashboard
- Add authentication/authorization
- Implement caching for large datasets
- Add data visualization endpoints

## License

This project is for OFWA coding test evaluation.