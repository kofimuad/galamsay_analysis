"""
Database models for Galamsay analysis.
These are shared between the analysis script and the API.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class AnalysisRun(Base):
    """
    Stores metadata about each analysis run.
    This allows you to track multiple analysis runs over time.
    """
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_galamsay_sites = Column(Integer, nullable=False)
    region_with_highest_sites = Column(String, nullable=False)
    highest_sites_count = Column(Integer, nullable=False)
    average_sites_per_region = Column(Float, nullable=False)
    status = Column(String, default="success")  # "success" or "failed"
    error_message = Column(String, nullable=True)
    
    # Relationships
    city_data = relationship("CityData", back_populates="analysis_run", cascade="all, delete-orphan")
    cities_exceeding_threshold = relationship("CityExceedsThreshold", back_populates="analysis_run", cascade="all, delete-orphan")


class CityData(Base):
    """
    Stores the cleaned city-level data for each analysis run.
    This preserves exactly what data was analyzed.
    """
    __tablename__ = "city_data"

    id = Column(Integer, primary_key=True, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, index=True)
    city = Column(String, nullable=False)
    region = Column(String, nullable=False)
    galamsay_sites = Column(Integer, nullable=False)
    
    # Relationship
    analysis_run = relationship("AnalysisRun", back_populates="city_data")


class CityExceedsThreshold(Base):
    """
    Stores cities that exceed the threshold for each analysis run.
    This pre-computes one of your required outputs.
    """
    __tablename__ = "cities_exceeding_threshold"

    id = Column(Integer, primary_key=True, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, index=True)
    city = Column(String, nullable=False)
    region = Column(String, nullable=False)
    galamsay_sites = Column(Integer, nullable=False)
    threshold = Column(Integer, nullable=False)
    
    # Relationship
    analysis_run = relationship("AnalysisRun", back_populates="cities_exceeding_threshold")


def get_database_url():
    """
    Returns the database URL for SQLAlchemy.
    For Supabase, format is:
    postgresql://user:password@host:port/database
    
    Store sensitive credentials in a .env file, not in code!
    """
    # Example for Supabase:
    # DATABASE_URL = "postgresql://postgres:your_password@db.supabaseurl.com:5432/postgres"
    return "sqlite:///./galamsay.db"  # Using SQLite for local development


def create_tables():
    """Create all tables in the database."""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")