from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.services.openstates_api import OpenStatesAPI
from app.services.openai_service import OpenAIService
from app.services.google_civic_api import GoogleCivicAPI
from pydantic import BaseModel
import logging

router = APIRouter()

# Initialize services
openstates_api = OpenStatesAPI()
openai_service = OpenAIService()
google_civic_api = GoogleCivicAPI()

class WidgetBillResponse(BaseModel):
    id: str
    title: str
    summary: str
    key_provisions: list = []
    impact: str
    status: str
    chamber: str
    sponsors: list = []

@router.get("/bill/{bill_id}", response_model=WidgetBillResponse)
async def get_widget_bill_data(bill_id: str):
    """
    Get bill data for widget display
    """
    try:
        # Try to get real bill data first
        bill_data = openstates_api.get_bill_by_id(bill_id)
        
        if not bill_data:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        # Try to get AI summary
        summary = None
        if bill_data.get('title') and bill_data.get('abstract'):
            summary = openai_service.generate_bill_summary(
                title=bill_data.get('title', ''),
                text=bill_data.get('abstract', ''),
                bill_id=bill_id
            )
        
        # If no summary available, return error instead of mock data
        if not summary:
            raise HTTPException(
                status_code=503, 
                detail="AI summary service is currently unavailable. Please try again later."
            )
        
        # Format response
        response = WidgetBillResponse(
            id=bill_data.get('id', bill_id),
            title=bill_data.get('title', 'Unknown Bill'),
            summary=summary.get('summary', 'Summary not available'),
            key_provisions=summary.get('key_provisions', []),
            impact=summary.get('impact', 'Impact information not available'),
            status=bill_data.get('status', 'Unknown status'),
            chamber=bill_data.get('from_organization', {}).get('name', 'Unknown chamber'),
            sponsors=[{
                'name': sponsor.get('person', {}).get('name', 'Unknown'),
                'party': sponsor.get('person', {}).get('party', [{}])[0].get('name', 'Unknown') if sponsor.get('person', {}).get('party') else 'Unknown'
            } for sponsor in bill_data.get('sponsorships', [])[:3]]
        )
        
        return response
        
    except Exception as e:
        logging.error(f"Error fetching widget bill data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/representatives")
async def get_widget_representatives(
    address: str = Query(..., description="Address to lookup representatives for"),
    levels: Optional[str] = Query(None, description="Government levels (federal,state,local)")
):
    """
    Get representatives for widget display
    """
    try:
        # Parse levels parameter
        level_list = None
        if levels:
            level_list = [level.strip() for level in levels.split(',')]
        
        # Fetch representatives data
        representatives_data = google_civic_api.get_representatives(address, level_list)
        
        if not representatives_data:
            raise HTTPException(
                status_code=404, 
                detail="No representatives found for the provided address. Please check the address and try again."
            )
        
        return representatives_data
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching widget representatives: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
