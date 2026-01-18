"""
Data analysis script for Galamsay data.
Reads CSV, cleans data, performs analysis, and stores results in database.

Run this BEFORE running the FastAPI server:
    python analyze_data.py
"""

import csv
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, AnalysisRun, CityData, CityExceedsThreshold, get_database_url


class GalamsayAnalyzer:
    """Handles data cleaning and analysis of Galamsay sites."""
    
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.raw_data = []
        self.cleaned_data = []
        self.errors = []
    
    def load_csv(self) -> bool:
        """
        Load CSV file and return raw data.
        Handles file not found errors gracefully.
        """
        try:
            if not os.path.exists(self.csv_file_path):
                self.errors.append(f"File not found: {self.csv_file_path}")
                return False
            
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.raw_data = list(reader)
            
            print(f"✓ Loaded {len(self.raw_data)} records from CSV")
            return True
        except Exception as e:
            self.errors.append(f"Error loading CSV: {str(e)}")
            return False
    
    def clean_row(self, row: dict) -> dict:
        """
        Clean a single row of data.
        Returns None if row is invalid, otherwise returns cleaned row.
        
        Cleaning rules:
        - City and Region must not be empty or "Unknown City"
        - Galamsay_Sites must be a valid positive integer (0 or greater)
        - Remove rows with invalid data
        """
        try:
            city = row.get('City', '').strip()
            region = row.get('Region', '').strip()
            sites_str = row.get('Number_of_Galamsay_Sites', '').strip()
            
            # Validation: Check if city is empty or unknown
            if not city or city.lower() == 'unknown city':
                self.errors.append(f"Invalid city: {city}")
                return None
            
            # Validation: Check if region is empty or invalid
            if not region or region.lower() == 'invalid region':
                self.errors.append(f"Invalid region for city {city}: {region}")
                return None
            
            # Validation: Try to convert sites to integer
            try:
                sites = int(sites_str)
            except ValueError:
                # If it's text like "abc" or "eleven", skip it
                self.errors.append(f"Invalid sites count for {city}: '{sites_str}' is not a number")
                return None
            
            # Validation: Sites must be non-negative (0 or positive)
            if sites < 0:
                self.errors.append(f"Negative sites count for {city}: {sites}")
                return None
            
            # Validation: Flag suspicious outliers (optional warning)
            if sites > 200:
                self.errors.append(f"WARNING: Possible outlier for {city}: {sites} sites")
            
            return {
                'city': city,
                'region': region,
                'sites': sites
            }
        except Exception as e:
            self.errors.append(f"Error cleaning row {row}: {str(e)}")
            return None
    
    def clean_data(self) -> bool:
        """
        Clean all rows in the dataset.
        """
        if not self.raw_data:
            self.errors.append("No data to clean. Load CSV first.")
            return False
        
        self.cleaned_data = []
        for row in self.raw_data:
            cleaned = self.clean_row(row)
            if cleaned:
                self.cleaned_data.append(cleaned)
        
        print(f"✓ Cleaned data: {len(self.cleaned_data)} valid records (removed {len(self.raw_data) - len(self.cleaned_data)} invalid records)")
        return True
    
    def analyze(self) -> dict:
        """
        Perform analysis on cleaned data.
        Returns a dictionary with all required metrics.
        """
        if not self.cleaned_data:
            self.errors.append("No cleaned data to analyze")
            return {}
        
        # Calculate total galamsay sites
        total_sites = sum(row['sites'] for row in self.cleaned_data)
        
        # Group by region and count sites
        region_totals = {}
        for row in self.cleaned_data:
            region = row['region']
            region_totals[region] = region_totals.get(region, 0) + row['sites']
        
        # Find region with highest sites
        region_with_highest = max(region_totals, key=region_totals.get)
        highest_count = region_totals[region_with_highest]
        
        # Calculate average sites per region
        avg_per_region = total_sites / len(region_totals) if region_totals else 0
        
        # Find cities exceeding threshold
        threshold = 10
        cities_exceeding = [row for row in self.cleaned_data if row['sites'] > threshold]
        
        return {
            'total_sites': total_sites,
            'region_with_highest': region_with_highest,
            'highest_count': highest_count,
            'avg_per_region': avg_per_region,
            'cities_exceeding_threshold': cities_exceeding,
            'region_totals': region_totals,
            'cleaned_data': self.cleaned_data
        }


def save_analysis_to_database(analysis_results: dict):
    """
    Save analysis results to database.
    This stores the analysis as a complete record with timestamp.
    """
    try:
        # Setup database
        engine = create_engine(get_database_url())
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create analysis run record
        analysis_run = AnalysisRun(
            timestamp=datetime.utcnow(),
            total_galamsay_sites=analysis_results['total_sites'],
            region_with_highest_sites=analysis_results['region_with_highest'],
            highest_sites_count=analysis_results['highest_count'],
            average_sites_per_region=round(analysis_results['avg_per_region'], 2),
            status='success'
        )
        session.add(analysis_run)
        session.flush()  # Get the ID without committing
        
        # Store cleaned city data
        for row in analysis_results['cleaned_data']:
            city_data = CityData(
                analysis_run_id=analysis_run.id,
                city=row['city'],
                region=row['region'],
                galamsay_sites=row['sites']
            )
            session.add(city_data)
        
        # Store cities exceeding threshold
        for row in analysis_results['cities_exceeding_threshold']:
            city_exceeds = CityExceedsThreshold(
                analysis_run_id=analysis_run.id,
                city=row['city'],
                region=row['region'],
                galamsay_sites=row['sites'],
                threshold=10
            )
            session.add(city_exceeds)
        
        session.commit()
        print(f"✓ Analysis saved to database with ID: {analysis_run.id}")
        print(f"  Timestamp: {analysis_run.timestamp}")
        
        session.close()
        return True
    except Exception as e:
        print(f"✗ Error saving to database: {str(e)}")
        return False


def main():
    """Main execution flow."""
    print("=" * 60)
    print("GALAMSAY DATA ANALYSIS")
    print("=" * 60)
    
    # Step 1: Load data
    analyzer = GalamsayAnalyzer('galamsay_data.csv')
    if not analyzer.load_csv():
        print("✗ Failed to load CSV")
        return
    
    # Step 2: Clean data
    if not analyzer.clean_data():
        print("✗ Failed to clean data")
        return
    
    # Step 3: Analyze
    results = analyzer.analyze()
    if not results:
        print("✗ Failed to analyze data")
        return
    
    # Step 4: Display results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print(f"Total Galamsay Sites: {results['total_sites']}")
    print(f"Region with Highest Sites: {results['region_with_highest']} ({results['highest_count']} sites)")
    print(f"Average Sites per Region: {results['avg_per_region']:.2f}")
    print(f"\nCities Exceeding Threshold (10 sites):")
    for city in sorted(results['cities_exceeding_threshold'], key=lambda x: x['sites'], reverse=True):
        print(f"  - {city['city']} ({city['region']}): {city['sites']} sites")
    
    print(f"\nData Quality Report:")
    print(f"  Valid records: {len(results['cleaned_data'])}")
    print(f"  Data cleaning errors/warnings: {len(analyzer.errors)}")
    if analyzer.errors[:5]:  # Show first 5 errors
        print(f"  Sample issues:")
        for error in analyzer.errors[:5]:
            print(f"    - {error}")
    
    # Step 5: Save to database
    print("\n" + "=" * 60)
    if save_analysis_to_database(results):
        print("✓ Analysis complete and saved successfully!")
    else:
        print("✗ Analysis complete but failed to save to database")


if __name__ == "__main__":
    main()