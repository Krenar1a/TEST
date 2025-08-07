from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import get_db
from app.crud import bill_summary_crud, bill_cache_crud
from app.crud.bills import create_bill, get_bill, delete_bill, delete_bill_by_pk, get_stored_bills
from app.services.openstates_api import OpenStatesAPI
from app.services.openai_service import OpenAIService
from app.services.bill_scraper import BillScraperService
from pydantic import BaseModel
import json
import logging

router = APIRouter()

# Initialize services
bill_scraper = BillScraperService()

class BillResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: Optional[str] = None
    chamber: Optional[str] = None
    introduced_date: Optional[str] = None
    last_action_date: Optional[str] = None
    last_action: Optional[str] = None
    sponsors: List[dict] = []
    actions: List[dict] = []

class BillCreate(BaseModel):
    bill_id: str
    title: str
    summary: Optional[str] = None
    key_provisions: Optional[List[str]] = []
    impact: Optional[str] = None
    status: Optional[str] = None

class BillDetailResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    key_provisions: List[str] = []
    impact: Optional[str] = None
    status: Optional[str] = None
    chamber: Optional[str] = None
    introduced_date: Optional[str] = None
    last_action_date: Optional[str] = None
    last_action: Optional[str] = None
    sponsors: List[dict] = []
    actions: List[dict] = []
    full_text_url: Optional[str] = None

# ===============================
# Main Bills API Endpoints
# =============================== 

@router.get("/detail/{bill_id}", response_model=BillDetailResponse)
def get_bill_detail(
    bill_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific bill
    """
    try:
        # Check if we have cached summary using CRUD
        cached_summary = bill_summary_crud.get_by_bill_id(db=db, bill_id=bill_id)
        
        # Create fresh API instance for each request
        openstates_api = OpenStatesAPI()
        
        # Fetch bill data from OpenStates API
        bill_data = openstates_api.get_bill_by_id(bill_id)
        
        if not bill_data:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        # Create bill detail object
        bill_detail = BillDetailResponse(
            id=bill_data.get('id', ''),
            title=bill_data.get('title', ''),
            status=get_latest_action(bill_data.get('actions', [])),
            chamber=bill_data.get('from_organization', {}).get('name', ''),
            introduced_date=bill_data.get('first_action_date', ''),
            last_action_date=bill_data.get('latest_action_date', ''),
            last_action=get_latest_action_description(bill_data.get('actions', [])),
            sponsors=[{
                'name': sponsor.get('person', {}).get('name', ''),
                'party': sponsor.get('person', {}).get('party', [{}])[0].get('name', '') if sponsor.get('person', {}).get('party') else ''
            } for sponsor in bill_data.get('sponsorships', [])],
            actions=bill_data.get('actions', []),
            full_text_url=bill_data.get('sources', [{}])[0].get('url', '') if bill_data.get('sources') else None
        )
        
        # Use cached summary if available
        if cached_summary:
            bill_detail.summary = cached_summary.summary
            try:
                bill_detail.key_provisions = bill_summary_crud.get_key_provisions_as_list(cached_summary)
            except:
                bill_detail.key_provisions = []
            bill_detail.impact = cached_summary.impact
        else:
            # Generate AI summary
            openai_service = OpenAIService()
            bill_text = bill_data.get('abstracts', [{}])[0].get('abstract', '') if bill_data.get('abstracts') else bill_data.get('title', '')
            ai_summary = openai_service.generate_bill_summary(
                title=bill_data.get('title', ''),
                text=bill_text,
                bill_id=bill_id
            )
            
            if ai_summary:
                bill_detail.summary = ai_summary.get('summary', '')
                bill_detail.key_provisions = ai_summary.get('key_provisions', [])
                bill_detail.impact = ai_summary.get('impact', '')
                
                # Cache the summary using CRUD
                bill_summary_crud.create_with_provisions(
                    db=db,
                    bill_id=bill_id,
                    title=ai_summary.get('title', bill_data.get('title', '')),
                    summary=ai_summary.get('summary', ''),
                    key_provisions=ai_summary.get('key_provisions', []),
                    impact=ai_summary.get('impact', ''),
                    status=ai_summary.get('status', get_latest_action(bill_data.get('actions', [])))
                )
        
        return bill_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching bill detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=dict)
def get_bills(
    search: Optional[str] = Query(None, description="Search query"),
    sort: str = Query("date", description="Sort by: date, chamber, status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get list of California legislative bills - Database first, API fallback
    """
    print("!!! BILLS ROUTE CALLED !!!")
    try:
        # Calculate offset for pagination
        offset = (page - 1) * per_page
        
        # First, try to get bills from database
        stored_bills = get_stored_bills(
            db, 
            skip=offset, 
            limit=per_page, 
            search=search,
            status=category
        )
        
        bills = []
        total_count = 0
        
        # If we have stored bills, use them
        if stored_bills:
            print(f"Found {len(stored_bills)} bills in database")
            
            # Convert stored bills to response format
            for stored_bill in stored_bills:
                try:
                    bill = BillResponse(
                        id=stored_bill.bill_id,
                        title=stored_bill.title,
                        summary=stored_bill.summary,
                        status=stored_bill.status or "Unknown",
                        chamber="California Legislature",  # Default since we don't store this
                        introduced_date="",  # We don't store dates in bill_summary
                        last_action_date="",
                        last_action="",
                        sponsors=[],  # We don't store sponsors in bill_summary
                        actions=[]
                    )
                    bills.append(bill)
                except Exception as bill_error:
                    logging.error(f"Error processing stored bill {stored_bill.bill_id}: {str(bill_error)}")
                    continue
            
            # Get total count for pagination (approximate)
            total_stored = len(get_stored_bills(db, skip=0, limit=1000, search=search, status=category))
            total_count = total_stored
            
        # If no stored bills or not enough results, fetch from API
        if len(bills) < per_page and not search:  # Only auto-fetch if no specific search
            print("Fetching additional bills from API...")
            try:
                # Create fresh API instance
                openstates_api = OpenStatesAPI()
                
                # Fetch bills from OpenStates API
                bills_data = openstates_api.get_california_bills(
                    search=search or "",
                    sort=sort,
                    category=category or "",
                    page=page,
                    per_page=per_page
                )
                
                if bills_data and isinstance(bills_data, dict):
                    results = bills_data.get('results', [])
                    
                    for i, bill_data in enumerate(results):
                        try:
                            if not isinstance(bill_data, dict):
                                continue
                            
                            # Check if this bill already exists in our results
                            bill_id = bill_data.get('id', '')
                            if any(b.id == bill_id for b in bills):
                                continue
                                
                            # Create bill response
                            bill = BillResponse(
                                id=bill_id,
                                title=bill_data.get('title', ''),
                                status=get_latest_action(bill_data.get('actions', [])),
                                chamber=bill_data.get('from_organization', {}).get('name', ''),
                                introduced_date=bill_data.get('first_action_date', ''),
                                last_action_date=bill_data.get('latest_action_date', ''),
                                last_action=get_latest_action_description(bill_data.get('actions', [])),
                                sponsors=[{
                                    'name': sponsor.get('person', {}).get('name', ''),
                                    'party': sponsor.get('person', {}).get('party', [{}])[0].get('name', '') if sponsor.get('person', {}).get('party') else ''
                                } for sponsor in bill_data.get('sponsorships', [])[:3]],
                                actions=bill_data.get('actions', [])[:5]
                            )
                            bills.append(bill)
                            
                            # Save new bill to database for future use
                            try:
                                bill_scraper.process_single_bill(db, bill_data)
                                logging.info(f"Saved bill {bill_id} to database")
                            except Exception as save_error:
                                logging.error(f"Error saving bill {bill_id}: {str(save_error)}")
                            
                        except Exception as bill_error:
                            logging.error(f"Error processing API bill at index {i}: {str(bill_error)}")
                            continue
                    
                    # Update total count if we got API results
                    api_total = bills_data.get('pagination', {}).get('total_count', 0)
                    if api_total > total_count:
                        total_count = api_total
                        
            except Exception as api_error:
                logging.error(f"Error fetching from API: {str(api_error)}")
                # Continue with database results only
        
        # Handle search-specific case
        if search and len(bills) == 0:
            print(f"No database results for search '{search}', trying API...")
            try:
                openstates_api = OpenStatesAPI()
                bills_data = openstates_api.get_california_bills(
                    search=search,
                    sort=sort,
                    category=category or "",
                    page=page,
                    per_page=per_page
                )
                
                if bills_data and isinstance(bills_data, dict):
                    results = bills_data.get('results', [])
                    
                    for bill_data in results:
                        try:
                            if not isinstance(bill_data, dict):
                                continue
                                
                            bill = BillResponse(
                                id=bill_data.get('id', ''),
                                title=bill_data.get('title', ''),
                                status=get_latest_action(bill_data.get('actions', [])),
                                chamber=bill_data.get('from_organization', {}).get('name', ''),
                                introduced_date=bill_data.get('first_action_date', ''),
                                last_action_date=bill_data.get('latest_action_date', ''),
                                last_action=get_latest_action_description(bill_data.get('actions', [])),
                                sponsors=[{
                                    'name': sponsor.get('person', {}).get('name', ''),
                                    'party': sponsor.get('person', {}).get('party', [{}])[0].get('name', '') if sponsor.get('person', {}).get('party') else ''
                                } for sponsor in bill_data.get('sponsorships', [])[:3]],
                                actions=bill_data.get('actions', [])[:5]
                            )
                            bills.append(bill)
                            
                            # Save searched bill to database
                            try:
                                bill_scraper.process_single_bill(db, bill_data)
                                logging.info(f"Saved searched bill {bill_data.get('id', 'unknown')} to database")
                            except Exception as save_error:
                                logging.error(f"Error saving searched bill: {str(save_error)}")
                            
                        except Exception as bill_error:
                            logging.error(f"Error processing search result: {str(bill_error)}")
                            continue
                    
                    # Update total for search results
                    total_count = bills_data.get('pagination', {}).get('total_count', len(bills))
                    
            except Exception as search_error:
                logging.error(f"Error searching API: {str(search_error)}")
        
        return {
            "bills": [bill.dict() for bill in bills],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "has_next": total_count > page * per_page,
                "has_prev": page > 1
            },
            "search_query": search or "",
            "sort_by": sort,
            "filter_category": category or "",
            "source": "database_first" if stored_bills else "api_only"
        }
        
    except Exception as e:
        logging.error(f"Error fetching bills: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

def get_latest_action(actions):
    """Get the latest action from actions list"""
    if not actions:
        return "No actions"
    
    # Sort by date and get the latest
    sorted_actions = sorted(actions, key=lambda x: x.get('date', ''), reverse=True)
    latest_action = sorted_actions[0] if sorted_actions else {}
    
    return latest_action.get('description', 'Unknown action')

def get_latest_action_description(actions):
    """Get the latest action description"""
    if not actions:
        return "No recent actions"
    
    sorted_actions = sorted(actions, key=lambda x: x.get('date', ''), reverse=True)
    latest_action = sorted_actions[0] if sorted_actions else {}
    
    return latest_action.get('description', 'No description available')


@router.post("/", status_code=201)
def create_bill_summary(bill_data: BillCreate, db: Session = Depends(get_db)):
    """
    Create a new bill summary
    """
    try:
        # Check if bill already exists
        existing_bill = get_bill(db, bill_data.bill_id)
        if existing_bill:
            raise HTTPException(status_code=409, detail=f"Bill with ID {bill_data.bill_id} already exists")
        
        # Create the bill
        new_bill = create_bill(db, bill_data.dict())
        logging.info(f"Created new bill summary: {bill_data.bill_id}")
        
        return {
            "message": "Bill summary created successfully",
            "bill": new_bill.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{bill_id}")
def delete_bill_summary(bill_id: str, db: Session = Depends(get_db)):
    """
    Delete a bill summary by bill_id
    """
    try:
        # Check if bill exists
        existing_bill = get_bill(db, bill_id)
        if not existing_bill:
            raise HTTPException(status_code=404, detail=f"Bill with ID {bill_id} not found")
        
        # Delete the bill
        success = delete_bill(db, bill_id)
        if success:
            logging.info(f"Deleted bill summary: {bill_id}")
            return {"message": f"Bill summary {bill_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete bill summary")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/by-pk/{pk_id}")
def delete_bill_by_primary_key(pk_id: int, db: Session = Depends(get_db)):
    """
    Delete a bill summary by primary key ID
    """
    try:
        # Delete the bill by primary key
        success = delete_bill_by_pk(db, pk_id)
        if success:
            logging.info(f"Deleted bill summary with ID: {pk_id}")
            return {"message": f"Bill summary with ID {pk_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Bill with ID {pk_id} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stored", response_model=List[dict])
def list_stored_bills(
    skip: int = Query(0, ge=0, description="Number of bills to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of bills to return"),
    status: Optional[str] = Query(None, description="Filter by bill status"),
    search: Optional[str] = Query(None, description="Search bills by title, summary, or ID"),
    db: Session = Depends(get_db)
):
    """
    Get stored bill summaries from database with search and filtering
    """
    try:
        bills = get_stored_bills(db, skip=skip, limit=limit, status=status, search=search)
        return [bill.to_dict() for bill in bills]
    except Exception as e:
        logging.error(f"Error fetching stored bills: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{bill_id}")
def get_bill_by_id(
    bill_id: str,
    db: Session = Depends(get_db)
):
    """
    Get bill information with separate bill and ai_summary objects (frontend compatible format)
    """
    try:
        # Try to get bill from database using the provided bill_id
        bill_data = get_bill(db, bill_id)
        
        # If not found, try with ocd-bill prefix (common format in database)
        if not bill_data and not bill_id.startswith("ocd-bill/"):
            bill_data = get_bill(db, f"ocd-bill/{bill_id}")
        
        if not bill_data:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        # Format the bill object
        bill = {
            "id": bill_data.bill_id,
            "identifier": getattr(bill_data, 'identifier', '') or '',
            "title": bill_data.title or '',
            "status": bill_data.status or '',
            "chamber": getattr(bill_data, 'chamber', '') or '',
            "updated_at": "",
            "introduced_date": "",
            "category": getattr(bill_data, 'classification', None),
            "abstract": getattr(bill_data, 'summary', None),
            "full_text_url": getattr(bill_data, 'openstates_url', None),
            "sponsors": []
        }
        
        # Safely handle datetime fields
        try:
            if hasattr(bill_data, 'updated_at') and bill_data.updated_at:
                if hasattr(bill_data.updated_at, 'isoformat'):
                    bill["updated_at"] = bill_data.updated_at.isoformat()
                else:
                    bill["updated_at"] = str(bill_data.updated_at)
        except Exception:
            pass
            
        try:
            if hasattr(bill_data, 'first_action_date') and bill_data.first_action_date:
                if hasattr(bill_data.first_action_date, 'isoformat'):
                    bill["introduced_date"] = bill_data.first_action_date.isoformat()
                else:
                    bill["introduced_date"] = str(bill_data.first_action_date)
        except Exception:
            pass
        
        # Safely parse sponsors JSON
        try:
            if hasattr(bill_data, 'sponsors') and bill_data.sponsors:
                bill["sponsors"] = json.loads(bill_data.sponsors)
        except (json.JSONDecodeError, TypeError):
            bill["sponsors"] = []
        
        # Format the AI summary object
        ai_summary = None
        if bill_data.summary or getattr(bill_data, 'key_provisions', None) or getattr(bill_data, 'impact', None):
            ai_summary = {
                "summary": bill_data.summary or "",
                "key_provisions": [],
                "impact": getattr(bill_data, 'impact', '') or ""
            }
            
            # Safely parse key_provisions JSON
            try:
                if hasattr(bill_data, 'key_provisions') and bill_data.key_provisions:
                    ai_summary["key_provisions"] = json.loads(bill_data.key_provisions)
            except (json.JSONDecodeError, TypeError):
                ai_summary["key_provisions"] = []
        
        return {
            "bill": bill,
            "ai_summary": ai_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching bill by ID: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
