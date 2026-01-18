"""
FastAPI server for Galamsay analysis results.
Exposes the analysis data via RESTful endpoints.

Run this AFTER running analyze_data.py:
    uvicorn api:app --reload
    
Then visit: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Optional
from models import AnalysisRun, CityData, CityExceedsThreshold, get_database_url
from pydantic import BaseModel


# ============================================================================
# Pydantic Models (for API request/response validation)
# ============================================================================

class CityDataResponse(BaseModel):
    """Response model for city-level data."""
    city: str
    region: str
    galamsay_sites: int
    
    class Config:
        from_attributes = True


class CityExceedsThresholdResponse(BaseModel):
    """Response model for cities exceeding threshold."""
    city: str
    region: str
    galamsay_sites: int
    threshold: int
    
    class Config:
        from_attributes = True


class AnalysisRunResponse(BaseModel):
    """Response model for a single analysis run with summary."""
    id: int
    timestamp: datetime
    total_galamsay_sites: int
    region_with_highest_sites: str
    highest_sites_count: int
    average_sites_per_region: float
    status: str
    
    class Config:
        from_attributes = True


class AnalysisRunDetailResponse(AnalysisRunResponse):
    """Extended response with all related data."""
    city_data: List[CityDataResponse]
    cities_exceeding_threshold: List[CityExceedsThresholdResponse]


# ============================================================================
# Database Setup
# ============================================================================

engine = create_engine(get_database_url())
Session = sessionmaker(bind=engine)

def get_session():
    """Dependency for getting database session."""
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Galamsay Analysis API",
    description="RESTful API for accessing illegal small-scale mining (Galamsay) analysis results",
    version="1.0.0"
)


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Galamsay Analysis API",
        "endpoints": {
            "analyses": "GET /analyses - List all analysis runs",
            "latest_analysis": "GET /analyses/latest - Get most recent analysis",
            "analysis_detail": "GET /analyses/{id} - Get detailed analysis by ID",
            "total_sites": "GET /metrics/total-sites - Get total galamsay sites from latest run",
            "region_highest": "GET /metrics/region-highest - Get region with highest sites",
            "avg_per_region": "GET /metrics/average-per-region - Get average sites per region",
            "cities_exceeding": "GET /metrics/cities-exceeding-threshold - Get cities over threshold",
            "docs": "GET /docs - Interactive API documentation (Swagger UI)"
        }
    }


@app.get("/analyses", response_model=List[AnalysisRunResponse])
def list_analyses(
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List all analysis runs with pagination.
    
    Returns the most recent analyses first.
    """
    session = Session()
    try:
        analyses = session.query(AnalysisRun)\
            .order_by(desc(AnalysisRun.timestamp))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        if not analyses:
            raise HTTPException(status_code=404, detail="No analysis runs found")
        
        return analyses
    finally:
        session.close()


@app.get("/analyses/latest", response_model=AnalysisRunDetailResponse)
def get_latest_analysis():
    """
    Get the most recent (latest) analysis run with all details.
    
    This is the most commonly used endpoint for current data.
    """
    session = Session()
    try:
        latest = session.query(AnalysisRun)\
            .order_by(desc(AnalysisRun.timestamp))\
            .first()
        
        if not latest:
            raise HTTPException(status_code=404, detail="No analysis runs found in database. Run analyze_data.py first.")
        
        # IMPORTANT: Access relationships while session is still open
        # This forces SQLAlchemy to load the data before closing the session
        city_data = list(latest.city_data)
        cities_exceeding = list(latest.cities_exceeding_threshold)
        
        return latest
    finally:
        session.close()


@app.get("/analyses/{analysis_id}", response_model=AnalysisRunDetailResponse)
def get_analysis_detail(analysis_id: int):
    """
    Get detailed information about a specific analysis run.
    
    Includes all city-level data and cities exceeding threshold.
    """
    session = Session()
    try:
        analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis run with ID {analysis_id} not found")
        
        # IMPORTANT: Access relationships while session is still open
        # This forces SQLAlchemy to load the data before closing the session
        city_data = list(analysis.city_data)
        cities_exceeding = list(analysis.cities_exceeding_threshold)
        
        return analysis
    finally:
        session.close()


@app.get("/metrics/total-sites")
def get_total_sites(analysis_id: Optional[int] = None):
    """
    Get total galamsay sites.
    
    If analysis_id is provided, get that specific run.
    Otherwise, get from the latest analysis.
    """
    session = Session()
    try:
        if analysis_id:
            analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found")
        else:
            analysis = session.query(AnalysisRun).order_by(desc(AnalysisRun.timestamp)).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="No analysis runs found")
        
        return {
            "total_galamsay_sites": analysis.total_galamsay_sites,
            "analysis_id": analysis.id,
            "timestamp": analysis.timestamp
        }
    finally:
        session.close()


@app.get("/metrics/region-highest")
def get_region_with_highest_sites(analysis_id: Optional[int] = None):
    """
    Get region with the highest number of galamsay sites.
    """
    session = Session()
    try:
        if analysis_id:
            analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found")
        else:
            analysis = session.query(AnalysisRun).order_by(desc(AnalysisRun.timestamp)).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="No analysis runs found")
        
        return {
            "region": analysis.region_with_highest_sites,
            "galamsay_sites": analysis.highest_sites_count,
            "analysis_id": analysis.id,
            "timestamp": analysis.timestamp
        }
    finally:
        session.close()


@app.get("/metrics/average-per-region")
def get_average_per_region(analysis_id: Optional[int] = None):
    """
    Get average number of galamsay sites per region.
    """
    session = Session()
    try:
        if analysis_id:
            analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found")
        else:
            analysis = session.query(AnalysisRun).order_by(desc(AnalysisRun.timestamp)).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="No analysis runs found")
        
        return {
            "average_sites_per_region": analysis.average_sites_per_region,
            "analysis_id": analysis.id,
            "timestamp": analysis.timestamp
        }
    finally:
        session.close()


@app.get("/metrics/cities-exceeding-threshold", response_model=List[CityExceedsThresholdResponse])
def get_cities_exceeding_threshold(
    analysis_id: Optional[int] = None,
    threshold: Optional[int] = None
):
    """
    Get list of cities where galamsay sites exceed a threshold.
    
    Default threshold is 10 (from the analysis).
    You can optionally specify a different threshold for filtering client-side results.
    """
    session = Session()
    try:
        if analysis_id:
            analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found")
        else:
            analysis = session.query(AnalysisRun).order_by(desc(AnalysisRun.timestamp)).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="No analysis runs found")
        
        cities = session.query(CityExceedsThreshold)\
            .filter(CityExceedsThreshold.analysis_run_id == analysis.id)\
            .all()
        
        # Optional client-side filtering by threshold
        if threshold:
            cities = [c for c in cities if c.galamsay_sites > threshold]
        
        return cities
    finally:
        session.close()


@app.get("/city/{city_name}")
def get_city_data(city_name: str, analysis_id: Optional[int] = None):
    """
    Get galamsay data for a specific city.
    """
    session = Session()
    try:
        if analysis_id:
            analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found")
        else:
            analysis = session.query(AnalysisRun).order_by(desc(AnalysisRun.timestamp)).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="No analysis runs found")
        
        city_data = session.query(CityData)\
            .filter(CityData.analysis_run_id == analysis.id)\
            .filter(CityData.city.ilike(city_name))\
            .first()
        
        if not city_data:
            raise HTTPException(status_code=404, detail=f"City '{city_name}' not found in analysis")
        
        return {
            "city": city_data.city,
            "region": city_data.region,
            "galamsay_sites": city_data.galamsay_sites,
            "analysis_id": city_data.analysis_run_id,
            "timestamp": analysis.timestamp
        }
    finally:
        session.close()


@app.get("/region/{region_name}")
def get_region_data(region_name: str, analysis_id: Optional[int] = None):
    """
    Get all cities in a specific region from the latest or specified analysis.
    """
    session = Session()
    try:
        if analysis_id:
            analysis = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found")
        else:
            analysis = session.query(AnalysisRun).order_by(desc(AnalysisRun.timestamp)).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="No analysis runs found")
        
        region_cities = session.query(CityData)\
            .filter(CityData.analysis_run_id == analysis.id)\
            .filter(CityData.region.ilike(region_name))\
            .all()
        
        if not region_cities:
            raise HTTPException(status_code=404, detail=f"Region '{region_name}' not found in analysis")
        
        total_sites = sum(c.galamsay_sites for c in region_cities)
        
        return {
            "region": region_name,
            "total_sites": total_sites,
            "number_of_cities": len(region_cities),
            "average_per_city": total_sites / len(region_cities) if region_cities else 0,
            "cities": [
                {
                    "city": c.city,
                    "galamsay_sites": c.galamsay_sites
                }
                for c in sorted(region_cities, key=lambda x: x.galamsay_sites, reverse=True)
            ],
            "analysis_id": analysis.id,
            "timestamp": analysis.timestamp
        }
    finally:
        session.close()


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    session = Session()
    try:
        # Try to query the database
        count = session.query(AnalysisRun).count()
        return {
            "status": "healthy",
            "database": "connected",
            "analysis_runs": count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)