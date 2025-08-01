"""
Admin scraper endpoints for manual control and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import get_db
from app.services.scheduler_service import scheduler_service
from app.services.bill_scraper import BillScraperService
from app.services.representative_scraper import RepresentativeScraperService
from pydantic import BaseModel
import logging

router = APIRouter()

class ScrapeResponse(BaseModel):
    status: str
    message: str
    data: dict

@router.post("/scrape/bills/clear", response_model=ScrapeResponse)
async def clear_all_bills():
    """
    Clear all bills from database
    """
    try:
        bill_scraper = BillScraperService()
        result = bill_scraper.clear_all_bills_from_database()
        
        return ScrapeResponse(
            status=result["status"],
            message=result["message"],
            data={"deleted_count": result["deleted_count"]}
        )
    except Exception as e:
        logging.error(f"Error clearing bills: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear bills: {str(e)}")

@router.post("/scrape/bills/manual", response_model=ScrapeResponse)
async def manual_bill_scraping(year: str = None):
    """
    Manually trigger bill scraping
    
    Args:
        year: Optional year to scrape ("2024", "2025", "all", or None for current session)
    """
    try:
        bill_scraper = BillScraperService()
        result = bill_scraper.scrape_all_bills(year=year)
        
        return ScrapeResponse(
            status="success",
            message=f"Bill scraping completed for year: {year or 'current session'}",
            data=result
        )
    except Exception as e:
        logging.error(f"Error in manual bill scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@router.post("/scrape/representatives/manual", response_model=ScrapeResponse)
async def manual_representative_scraping():
    """
    Manually trigger representative scraping
    """
    try:
        rep_scraper = RepresentativeScraperService()
        result = rep_scraper.scrape_all_representatives()
        
        return ScrapeResponse(
            status="success",
            message="Representative scraping completed",
            data=result
        )
    except Exception as e:
        logging.error(f"Error in manual representative scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@router.post("/test/google-civic-api", response_model=dict)
async def test_google_civic_api(address: str = "San Francisco, CA"):
    """
    Test Google Civic API directly for debugging
    """
    try:
        rep_scraper = RepresentativeScraperService()
        result = rep_scraper.google_civic_api.get_representatives(address)
        
        return {
            "status": "success" if result else "failed",
            "address": address,
            "result": result,
            "has_data": bool(result and result.get('representatives')),
            "representative_count": len(result.get('representatives', [])) if result else 0
        }
    except Exception as e:
        logging.error(f"Google Civic API test failed: {str(e)}")
        return {
            "status": "error",
            "address": address,
            "error": str(e),
            "result": None,
            "representative_count": 0
        }

@router.post("/test/scrape-and-save", response_model=dict)
async def test_scrape_and_save(address: str = "San Francisco, CA"):
    """
    Test scraping representatives for a specific address and saving to database
    """
    try:
        rep_scraper = RepresentativeScraperService()
        result = rep_scraper.scrape_representatives_for_address(address)
        
        return {
            "status": "success",
            "address": address,
            "scraped_count": len(result),
            "representatives": result
        }
    except Exception as e:
        logging.error(f"Scrape and save test failed: {str(e)}")
        return {
            "status": "error",
            "address": address,
            "error": str(e),
            "scraped_count": 0,
            "representatives": []
        }

@router.post("/scrape/all/manual", response_model=ScrapeResponse)
async def manual_full_scraping():
    """
    Manually trigger both bill and representative scraping
    """
    try:
        result = scheduler_service.run_manual_scraping()
        
        return ScrapeResponse(
            status="success",
            message="Full scraping completed",
            data=result
        )
    except Exception as e:
        logging.error(f"Error in manual full scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@router.get("/scrape/status")
async def get_scrape_status():
    """
    Get the current status of the scheduler
    """
    try:
        return {
            "scheduler_running": scheduler_service.running,
            "next_bill_scraping": "Every Monday at 2:00 AM",
            "next_representative_scraping": "Every Monday at 3:00 AM",
            "status": "active" if scheduler_service.running else "inactive"
        }
    except Exception as e:
        logging.error(f"Error getting scrape status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")

@router.post("/scheduler/start")
async def start_scheduler():
    """
    Start the scheduler service
    """
    try:
        scheduler_service.start()
        return {"message": "Scheduler started successfully"}
    except Exception as e:
        logging.error(f"Error starting scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start scheduler")

@router.post("/scheduler/stop")
async def stop_scheduler():
    """
    Stop the scheduler service
    """
    try:
        scheduler_service.stop()
        return {"message": "Scheduler stopped successfully"}
    except Exception as e:
        logging.error(f"Error stopping scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stop scheduler")
