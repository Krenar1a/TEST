"""
Admin scraper endpoints - Simple CRUD operations
"""

from fastapi import APIRouter, HTTPException
from app.services.scheduler_service import scheduler_service
from app.services.bill_scraper import BillScraperService
from app.services.representative_scraper import RepresentativeScraperService
import logging

router = APIRouter()

# ===============================
# BILLS - CRUD Operations
# ===============================

@router.post("/bills")
async def scrape_bills():
    """POST: Start bill scraping"""
    try:
        bill_scraper = BillScraperService()
        result = bill_scraper.scrape_recent_bills(days=7)
        return {"status": "success", "data": result}
    except Exception as e:
        logging.error(f"Error scraping bills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bills/status")
async def get_bills_status():
    """GET: Get scraping status"""
    try:
        return {
            "scheduler_running": scheduler_service.running,
            "status": "active" if scheduler_service.running else "inactive"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/bills")
async def clear_bills():
    """DELETE: Clear all bills"""
    try:
        bill_scraper = BillScraperService()
        result = bill_scraper.clear_all_bills_from_database()
        return {"status": "success", "deleted": result["deleted_count"]}
    except Exception as e:
        logging.error(f"Error clearing bills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# REPRESENTATIVES - CRUD Operations  
# ===============================

@router.post("/representatives")
async def scrape_representatives():
    """POST: Start representative scraping"""
    try:
        rep_scraper = RepresentativeScraperService()
        result = rep_scraper.scrape_all_representatives()
        return {"status": "success", "data": result}
    except Exception as e:
        logging.error(f"Error scraping representatives: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# AI SUMMARIES - CRUD Operations
# ===============================

@router.post("/ai")
async def generate_ai_summaries():
    """POST: Generate AI summaries"""
    try:
        bill_scraper = BillScraperService()
        from app.models.database import SessionLocal
        from app.models.bills import BillSummary
        
        db = SessionLocal()
        bills = db.query(BillSummary).filter(
            (BillSummary.summary == None) | (BillSummary.summary == "")
        ).limit(20).all()
        
        success = 0
        for bill in bills:
            try:
                if bill_scraper.generate_ai_summary_for_bill(db, bill.bill_id):
                    success += 1
            except:
                continue
        
        db.close()
        return {"status": "success", "generated": success}
    except Exception as e:
        logging.error(f"Error generating AI summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/{bill_id}")
async def generate_single_ai_summary(bill_id: str):
    """POST: Generate AI for specific bill"""
    try:
        bill_scraper = BillScraperService()
        from app.models.database import SessionLocal
        
        db = SessionLocal()
        success = bill_scraper.generate_ai_summary_for_bill(db, bill_id)
        db.close()
        
        if success:
            return {"status": "success", "bill_id": bill_id}
        else:
            raise HTTPException(status_code=404, detail="Failed to generate summary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# SCHEDULER - Control Operations
# ===============================

@router.post("/scheduler/start")
async def start_scheduler():
    """POST: Start scheduler"""
    try:
        scheduler_service.start()
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scheduler/stop")
async def stop_scheduler():
    """POST: Stop scheduler"""
    try:
        scheduler_service.stop()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
