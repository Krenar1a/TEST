from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from app.services.google_civic_api import GoogleCivicAPI
from app.services.representative_scraper import RepresentativeScraperService
from app.models import get_db
from app.crud.representatives import (
    create_representative, get_representative, delete_representative, 
    hard_delete_representative, get_stored_representatives
)
from pydantic import BaseModel
import logging

router = APIRouter()

# Initialize services
google_civic_api = GoogleCivicAPI()
representative_scraper = RepresentativeScraperService()

class RepresentativeResponse(BaseModel):
    name: str
    office: str
    party: Optional[str] = None
    phones: list = []
    emails: list = []
    urls: list = []
    photo_url: Optional[str] = None
    address: Optional[dict] = None

class RepresentativeCreate(BaseModel):
    name: str
    office: str
    party: Optional[str] = None
    level: Optional[str] = None  # federal, state, local
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    photo_url: Optional[str] = None

@router.get("/", response_model=dict)
async def get_representatives(
    address: str = Query(..., description="Address to lookup representatives for"),
    levels: Optional[str] = Query(None, description="Government levels (federal,state,local)")
):
    """
    Get elected representatives for a given address
    """
    try:
        # Parse levels parameter
        level_list = None
        if levels:
            level_list = [level.strip() for level in levels.split(',')]
        
        # First try to get representatives from database, or scrape if not found
        representatives_data = representative_scraper.get_or_scrape_representatives(address)
        
        if not representatives_data:
            representatives_data = []
        
        # Filter by levels if specified
        if level_list:
            representatives_data = [
                rep for rep in representatives_data 
                if rep.get('level', '').lower() in [l.lower() for l in level_list]
            ]
        
        # Format response to match expected structure
        response_data = {
            "address": address,
            "representatives": representatives_data
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching representatives: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", status_code=201)
async def create_representative_record(
    representative_data: RepresentativeCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new representative record in the database
    """
    try:
        # Create the representative
        new_representative = create_representative(db, representative_data.dict())
        logging.info(f"Created new representative: {representative_data.name}")
        
        return {
            "message": "Representative created successfully",
            "representative": new_representative.to_dict()
        }
    except Exception as e:
        logging.error(f"Error creating representative: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{representative_id}")
async def delete_representative_record(
    representative_id: int, 
    hard_delete: bool = Query(False, description="If true, permanently delete; if false, soft delete"),
    db: Session = Depends(get_db)
):
    """
    Delete a representative record
    """
    try:
        # Check if representative exists
        existing_representative = get_representative(db, representative_id)
        if not existing_representative:
            raise HTTPException(status_code=404, detail=f"Representative with ID {representative_id} not found")
        
        # Delete the representative
        if hard_delete:
            success = hard_delete_representative(db, representative_id)
            action = "permanently deleted"
        else:
            success = delete_representative(db, representative_id)
            action = "deactivated"
            
        if success:
            logging.info(f"Representative {representative_id} {action}")
            return {"message": f"Representative {action} successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete representative")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting representative: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stored", response_model=List[dict])
async def list_stored_representatives(
    skip: int = Query(0, ge=0, description="Number of representatives to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of representatives to return"),
    level: Optional[str] = Query(None, description="Filter by government level (federal, state, local)"),
    db: Session = Depends(get_db)
):
    """
    Get stored representatives from database
    """
    try:
        representatives = get_stored_representatives(db, skip=skip, limit=limit, level=level)
        return [rep.to_dict() for rep in representatives]
    except Exception as e:
        logging.error(f"Error fetching stored representatives: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
