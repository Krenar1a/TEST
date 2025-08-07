from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.crud import bill_summary_crud, bill_cache_crud
from pydantic import BaseModel
import logging
import os

router = APIRouter()

class AdminStatsResponse(BaseModel):
    total_summaries: int
    total_cached_bills: int
    cache_stats: dict
    api_keys_configured: dict

@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(db: Session = Depends(get_db)):
    """
    Get admin dashboard statistics using CRUD operations
    """
    try:
        # Use CRUD operations for better maintainability
        total_summaries = bill_summary_crud.count(db)
        total_cached_bills = bill_cache_crud.count(db)
        cache_stats = bill_cache_crud.get_cache_stats(db)
        
        # Check API key configuration (simplified)
        api_keys_configured = {
            "openstates": bool(os.environ.get("OPENSTATES_API_KEY", "") != "YOUR_API_KEY"),
            "openai": bool(os.environ.get("OPENAI_API_KEY", "") != "YOUR_API_KEY"),
            "google_civic": bool(os.environ.get("GOOGLE_CIVIC_API_KEY", "") != "YOUR_API_KEY"),
            "sendgrid": bool(os.environ.get("SENDGRID_API_KEY", "") != "YOUR_API_KEY")
        }
        
        return AdminStatsResponse(
            total_summaries=total_summaries,
            total_cached_bills=total_cached_bills,
            cache_stats=cache_stats,
            api_keys_configured=api_keys_configured
        )
        
    except Exception as e:
        logging.error(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/database")
def get_database_stats(db: Session = Depends(get_db)):
    """
    Get database management statistics using CRUD operations
    """
    try:
        # Get recent summaries using CRUD
        recent_summaries = bill_summary_crud.get_recent_summaries(db, limit=10)
        
        # Get recent cached bills using CRUD
        recent_cached = bill_cache_crud.get_recent_cached(db, limit=10)
        
        return {
            "total_summaries": bill_summary_crud.count(db),
            "total_cached": bill_cache_crud.count(db),
            "recent_summaries": [
                {
                    "id": s.id,
                    "bill_id": s.bill_id,
                    "title": s.title,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in recent_summaries
            ],
            "recent_cached": [
                {
                    "id": c.id,
                    "bill_id": c.bill_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None
                }
                for c in recent_cached
            ],
            "cache_stats": bill_cache_crud.get_cache_stats(db)
        }
        
    except Exception as e:
        logging.error(f"Error fetching database stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/clear-cache")
def clear_cache(request: dict, db: Session = Depends(get_db)):
    """
    Clear cached data using CRUD operations
    """
    try:
        cache_type = request.get('cache_type')
        
        if cache_type == "bill_cache":
            deleted = bill_cache_crud.clear_all_cache(db)
            return {"message": f"Cleared {deleted} cached bills", "deleted": deleted}
            
        elif cache_type == "expired":
            # Clear cache older than 24 hours
            deleted = bill_cache_crud.delete_expired_cache(db, hours=24)
            return {"message": f"Cleared {deleted} expired cache entries", "deleted": deleted}
            
        elif cache_type == "all":
            # Clear all cached data
            deleted_cache = bill_cache_crud.clear_all_cache(db)
            # Note: We typically don't delete summaries as they're valuable
            return {
                "message": f"Cleared {deleted_cache} cached bills",
                "deleted_cache": deleted_cache,
                "note": "Bill summaries preserved (they contain AI-generated content)"
            }
            
        else:
            raise HTTPException(status_code=400, detail="Invalid cache type")
            
    except Exception as e:
        logging.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/summaries/search")
def search_summaries(
    q: str = "",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Search bill summaries using CRUD operations
    """
    try:
        if q:
            summaries = bill_summary_crud.search_by_title(db, search_term=q, skip=skip, limit=limit)
        else:
            summaries = bill_summary_crud.get_multi(db, skip=skip, limit=limit)
        
        return {
            "summaries": [
                {
                    "id": s.id,
                    "bill_id": s.bill_id,
                    "title": s.title,
                    "summary": s.summary[:200] + "..." if len(s.summary) > 200 else s.summary,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in summaries
            ],
            "query": q,
            "skip": skip,
            "limit": limit,
            "total": bill_summary_crud.count(db)
        }
        
    except Exception as e:
        logging.error(f"Error searching summaries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
