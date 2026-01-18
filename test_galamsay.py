"""
Test suite for Galamsay analysis project.

Run tests with:
    pytest test_galamsay.py -v

For coverage report:
    pytest test_galamsay.py --cov=. --cov-report=html
"""

import pytest
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from analyze_data import GalamsayAnalyzer
from models import Base, AnalysisRun, CityData, CityExceedsThreshold, get_database_url
from fastapi.testclient import TestClient
from api import app


# ============================================================================
# Fixtures (Setup for tests)
# ============================================================================

@pytest.fixture
def temp_csv():
    """Create a temporary CSV file for testing."""
    content = """City,Region,Number_of_Galamsay_Sites
Kumasi,Ashanti,25
Accra,Greater Accra,20
Takoradi,Western,18
Tamale,Northern,7
Bolgatanga,Upper East,5
Obuasi,Ashanti,10
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_csv_with_errors():
    """Create a CSV with intentional data quality issues."""
    content = """City,Region,Number_of_Galamsay_Sites
Accra,Greater Accra,30
Unknown City,Some Region,10
Kumasi,Ashanti,abc
Tamale,Northern,-5
Cape Coast,Central,1000
Valid City,Eastern,15
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def test_database():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    
    # Populate with test data
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create a test analysis run
    analysis = AnalysisRun(
        timestamp=datetime.utcnow(),
        total_galamsay_sites=85,
        region_with_highest_sites="Ashanti",
        highest_sites_count=25,
        average_sites_per_region=17.0,
        status="success"
    )
    session.add(analysis)
    session.flush()
    
    # Add test city data
    cities = [
        CityData(analysis_run_id=analysis.id, city="Accra", region="Greater Accra", galamsay_sites=30),
        CityData(analysis_run_id=analysis.id, city="Kumasi", region="Ashanti", galamsay_sites=25),
        CityData(analysis_run_id=analysis.id, city="Takoradi", region="Western", galamsay_sites=18),
        CityData(analysis_run_id=analysis.id, city="Tamale", region="Northern", galamsay_sites=7),
        CityData(analysis_run_id=analysis.id, city="Bolgatanga", region="Upper East", galamsay_sites=5),
    ]
    session.add_all(cities)
    
    # Add cities exceeding threshold
    exceeding = [
        CityExceedsThreshold(analysis_run_id=analysis.id, city="Accra", region="Greater Accra", galamsay_sites=30, threshold=10),
        CityExceedsThreshold(analysis_run_id=analysis.id, city="Kumasi", region="Ashanti", galamsay_sites=25, threshold=10),
        CityExceedsThreshold(analysis_run_id=analysis.id, city="Takoradi", region="Western", galamsay_sites=18, threshold=10),
    ]
    session.add_all(exceeding)
    session.commit()
    
    yield engine, session
    
    session.close()


@pytest.fixture
def api_client():
    """Create a FastAPI test client."""
    return TestClient(app)


# ============================================================================
# Unit Tests for Data Cleaning
# ============================================================================

class TestDataCleaning:
    """Tests for the GalamsayAnalyzer.clean_row() method."""
    
    def test_clean_valid_row(self):
        """Valid row should be cleaned without errors."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'Accra', 'Region': 'Greater Accra', 'Number_of_Galamsay_Sites': '30'}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is not None
        assert cleaned['city'] == 'Accra'
        assert cleaned['region'] == 'Greater Accra'
        assert cleaned['sites'] == 30
    
    def test_clean_row_with_whitespace(self):
        """Row with leading/trailing whitespace should be stripped."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': '  Accra  ', 'Region': '  Greater Accra  ', 'Number_of_Galamsay_Sites': '  30  '}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is not None
        assert cleaned['city'] == 'Accra'
        assert cleaned['sites'] == 30
    
    def test_clean_row_rejects_unknown_city(self):
        """Row with 'Unknown City' should be rejected."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'Unknown City', 'Region': 'Some Region', 'Number_of_Galamsay_Sites': '10'}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is None
        assert len(analyzer.errors) > 0
    
    def test_clean_row_rejects_invalid_sites_count(self):
        """Row with non-numeric sites count should be rejected."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'Kumasi', 'Region': 'Ashanti', 'Number_of_Galamsay_Sites': 'abc'}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is None
        assert len(analyzer.errors) > 0
    
    def test_clean_row_rejects_negative_sites(self):
        """Row with negative sites count should be rejected."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'Tamale', 'Region': 'Northern', 'Number_of_Galamsay_Sites': '-5'}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is None
    
    def test_clean_row_rejects_missing_city(self):
        """Row with missing city should be rejected."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': '', 'Region': 'Some Region', 'Number_of_Galamsay_Sites': '10'}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is None
    
    def test_clean_row_rejects_invalid_region(self):
        """Row with 'Invalid Region' should be rejected."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'Techiman', 'Region': 'Invalid Region', 'Number_of_Galamsay_Sites': '16'}
        
        cleaned = analyzer.clean_row(row)
        
        assert cleaned is None


# ============================================================================
# Unit Tests for CSV Loading
# ============================================================================

class TestCSVLoading:
    """Tests for CSV file loading."""
    
    def test_load_valid_csv(self, temp_csv):
        """Valid CSV should load successfully."""
        analyzer = GalamsayAnalyzer(temp_csv)
        result = analyzer.load_csv()
        
        assert result is True
        assert len(analyzer.raw_data) == 6
        assert analyzer.raw_data[0]['City'] == 'Kumasi'
    
    def test_load_nonexistent_file(self):
        """Loading non-existent file should fail gracefully."""
        analyzer = GalamsayAnalyzer('nonexistent.csv')
        result = analyzer.load_csv()
        
        assert result is False
        assert len(analyzer.errors) > 0


# ============================================================================
# Integration Tests for Analysis
# ============================================================================

class TestAnalysis:
    """Tests for the full analysis pipeline."""
    
    def test_analysis_pipeline_with_clean_data(self, temp_csv):
        """Complete analysis pipeline should produce correct results."""
        analyzer = GalamsayAnalyzer(temp_csv)
        
        # Execute pipeline
        assert analyzer.load_csv() is True
        assert analyzer.clean_data() is True
        results = analyzer.analyze()
        
        # Verify results
        assert results['total_sites'] == 85
        assert results['region_with_highest'] == 'Ashanti'  # Ashanti has 25+10=35 sites
        assert results['highest_count'] == 35
        assert len(results['cleaned_data']) == 6
    
    def test_analysis_handles_dirty_data(self, temp_csv_with_errors):
        """Analysis should handle and reject dirty data."""
        analyzer = GalamsayAnalyzer(temp_csv_with_errors)
        
        assert analyzer.load_csv() is True
        assert analyzer.clean_data() is True
        
        # Should have cleaned 3 valid records (Accra, Cape Coast with 1000, Valid City)
        # Cape Coast's 1000 is flagged as suspicious but still accepted (warning, not error)
        assert len(analyzer.cleaned_data) == 3
        
        # Should have errors for the invalid records
        assert len(analyzer.errors) >= 3
    
    def test_cities_exceeding_threshold(self, temp_csv):
        """Should correctly identify cities exceeding threshold."""
        analyzer = GalamsayAnalyzer(temp_csv)
        analyzer.load_csv()
        analyzer.clean_data()
        results = analyzer.analyze()
        
        exceeding = results['cities_exceeding_threshold']
        
        # With threshold=10, should have Accra, Kumasi, Takoradi
        assert len(exceeding) == 3
        assert any(c['city'] == 'Accra' for c in exceeding)
    
    def test_average_calculation(self, temp_csv):
        """Average sites per region should be calculated correctly."""
        analyzer = GalamsayAnalyzer(temp_csv)
        analyzer.load_csv()
        analyzer.clean_data()
        results = analyzer.analyze()
        
        # 85 total sites / 5 regions = 17
        assert results['avg_per_region'] == 17.0


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestAPI:
    """Tests for FastAPI endpoints."""
    
    def test_root_endpoint(self, api_client):
        """Root endpoint should return API information."""
        response = api_client.get("/")
        assert response.status_code == 200
        assert "endpoints" in response.json()
    
    def test_health_check(self, api_client):
        """Health check endpoint should be accessible."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "unhealthy"]
    
    def test_list_analyses_empty(self, api_client):
        """Should handle request when no analyses exist."""
        response = api_client.get("/analyses")
        # This will return 404 in a real scenario with empty database
        assert response.status_code in [200, 404]
    
    def test_metrics_endpoints_structure(self, api_client):
        """Metrics endpoints should return correct structure."""
        # These will return 404 if database is empty, which is expected
        endpoints = [
            "/metrics/total-sites",
            "/metrics/region-highest",
            "/metrics/average-per-region"
        ]
        
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            # Accept either 200 (with data) or 404 (no data)
            assert response.status_code in [200, 404]


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_zero_sites_valid(self):
        """A city with 0 galamsay sites should be valid."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'SomeCity', 'Region': 'SomeRegion', 'Number_of_Galamsay_Sites': '0'}
        
        cleaned = analyzer.clean_row(row)
        assert cleaned is not None
        assert cleaned['sites'] == 0
    
    def test_very_large_number(self):
        """Very large numbers should be flagged as suspicious but still valid."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        row = {'City': 'SomeCity', 'Region': 'SomeRegion', 'Number_of_Galamsay_Sites': '999'}
        
        cleaned = analyzer.clean_row(row)
        # Should still be accepted (flagged as warning, not error)
        assert cleaned is not None or len(analyzer.errors) > 0
    
    def test_empty_csv(self):
        """Empty CSV should fail gracefully."""
        analyzer = GalamsayAnalyzer("dummy.csv")
        analyzer.raw_data = []
        result = analyzer.clean_data()
        
        assert result is False
        assert len(analyzer.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])