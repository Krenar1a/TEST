from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.database import get_db
from app.crud import bill_summary_crud, bill_cache_crud
from app.schemas import BillSummary, BillSummaryCreate, BillSummaryUpdate
from pydantic import BaseModel
import logging

router = APIRouter()

class BillSummaryResponse(BaseModel):
    id: int
    bill_id: str
    title: str
    summary: str
    key_provisions: List[str]
    impact: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@router.get("/summaries", response_model=List[BillSummaryResponse])
async def get_bill_summaries(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search in bill titles"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    Get bill summaries with pagination and filtering using CRUD operations
    """
    try:
        if search:
            summaries = bill_summary_crud.search_by_title(
                db=db, search_term=search, skip=skip, limit=limit
            )
        elif status:
            summaries = bill_summary_crud.get_by_status(
                db=db, status=status, skip=skip, limit=limit
            )
        else:
            summaries = bill_summary_crud.get_multi(db=db, skip=skip, limit=limit)
        
        # Convert to response format
        response_data = []
        for summary in summaries:
            response_data.append(BillSummaryResponse(
                id=summary.id,
                bill_id=summary.bill_id,
                title=summary.title,
                summary=summary.summary,
                key_provisions=bill_summary_crud.get_key_provisions_as_list(summary),
                impact=summary.impact,
                status=summary.status,
                created_at=summary.created_at.isoformat() if summary.created_at else None,
                updated_at=summary.updated_at.isoformat() if summary.updated_at else None
            ))
        
        return response_data
        
    except Exception as e:
        logging.error(f"Error fetching bill summaries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/summaries/{bill_id}", response_model=BillSummaryResponse)
async def get_bill_summary(bill_id: str, db: Session = Depends(get_db)):
    """
    Get a specific bill summary by bill_id using CRUD operations
    """
    try:
        summary = bill_summary_crud.get_by_bill_id(db=db, bill_id=bill_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Bill summary not found")
        
        return BillSummaryResponse(
            id=summary.id,
            bill_id=summary.bill_id,
            title=summary.title,
            summary=summary.summary,
            key_provisions=bill_summary_crud.get_key_provisions_as_list(summary),
            impact=summary.impact,
            status=summary.status,
            created_at=summary.created_at.isoformat() if summary.created_at else None,
            updated_at=summary.updated_at.isoformat() if summary.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/summaries/{bill_id}", response_model=BillSummaryResponse)
async def update_bill_summary(
    bill_id: str,
    update_data: BillSummaryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a bill summary using CRUD operations
    """
    try:
        # Get existing summary
        existing_summary = bill_summary_crud.get_by_bill_id(db=db, bill_id=bill_id)
        if not existing_summary:
            raise HTTPException(status_code=404, detail="Bill summary not found")
        
        # Update the summary
        updated_summary = bill_summary_crud.update(
            db=db, db_obj=existing_summary, obj_in=update_data
        )
        
        return BillSummaryResponse(
            id=updated_summary.id,
            bill_id=updated_summary.bill_id,
            title=updated_summary.title,
            summary=updated_summary.summary,
            key_provisions=bill_summary_crud.get_key_provisions_as_list(updated_summary),
            impact=updated_summary.impact,
            status=updated_summary.status,
            created_at=updated_summary.created_at.isoformat() if updated_summary.created_at else None,
            updated_at=updated_summary.updated_at.isoformat() if updated_summary.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/summaries/{bill_id}")
async def delete_bill_summary(bill_id: str, db: Session = Depends(get_db)):
    """
    Delete a bill summary using CRUD operations
    """
    try:
        deleted_summary = bill_summary_crud.delete_by_bill_id(db=db, bill_id=bill_id)
        if not deleted_summary:
            raise HTTPException(status_code=404, detail="Bill summary not found")
        
        return {"message": f"Bill summary for {bill_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/cache/stats")
async def get_cache_stats(db: Session = Depends(get_db)):
    """
    Get cache statistics using CRUD operations
    """
    try:
        return bill_cache_crud.get_cache_stats(db)
        
    except Exception as e:
        logging.error(f"Error fetching cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cache/cleanup")
async def cleanup_cache(
    hours: int = Query(24, ge=1, description="Delete cache older than X hours"),
    db: Session = Depends(get_db)
):
    """
    Clean up expired cache entries using CRUD operations
    """
    try:
        deleted_count = bill_cache_crud.delete_expired_cache(db=db, hours=hours)
        
        return {
            "message": f"Cleaned up {deleted_count} cache entries older than {hours} hours",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logging.error(f"Error cleaning up cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
