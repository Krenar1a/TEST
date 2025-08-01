"""
Bill scraper service
Handles scraping bills from OpenStates API and saving to database
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.bills import BillSummary, BillCache
from app.services.openstates_api import OpenStatesAPI
from app.services.openai_service import OpenAIService
from app.crud.bills import create_bill, get_bill, update_bill, clear_all_bills
import json
from datetime import datetime

class BillScraperService:
    """Service to scrape and store bills"""
    
    def __init__(self):
        self.openstates_api = OpenStatesAPI()
        self.openai_service = OpenAIService()
    
    def parse_date_safely(self, date_string: str) -> Optional[datetime]:
        """Safely parse date strings into datetime objects"""
        if not date_string:
            return None
        
        try:
            # Try ISO format first (most common from APIs)
            if 'T' in date_string:
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                # Try date-only format
                return datetime.strptime(date_string, '%Y-%m-%d')
        except (ValueError, AttributeError):
            try:
                # Try other common formats
                return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logging.warning(f"Could not parse date: {date_string}")
                return None
        
    def clear_all_bills_from_database(self) -> Dict:
        """Clear all bills from database"""
        try:
            db = SessionLocal()
            deleted_count = clear_all_bills(db)
            db.close()
            
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "message": f"Cleared {deleted_count} bills from database"
            }
        except Exception as e:
            logging.error(f"Error clearing bills from database: {str(e)}")
            return {
                "status": "error", 
                "deleted_count": 0,
                "message": f"Failed to clear bills: {str(e)}"
            }

    def scrape_all_bills(self, year: Optional[str] = None) -> Dict:
        """Scrape all bills and save to database
        
        Args:
            year: Optional year to scrape (e.g., "2024", "2025", "all")
                  If None, scrapes current session
        """
        try:
            db = SessionLocal()
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_errors = 0
            
            # Determine sessions to scrape based on year parameter
            sessions_to_scrape = self._get_sessions_for_year(year)
            
            for session in sessions_to_scrape:
                logging.info(f"Scraping bills for session: {session}")
                session_result = self._scrape_session_bills(db, session)
                
                total_processed += session_result.get('processed', 0)
                total_created += session_result.get('created', 0)
                total_updated += session_result.get('updated', 0)
                total_errors += session_result.get('errors', 0)
            
            db.close()
            
            return {
                "processed": total_processed,
                "created": total_created,
                "updated": total_updated,
                "errors": total_errors,
                "sessions_scraped": sessions_to_scrape
            }
            
        except Exception as e:
            logging.error(f"Error in scrape_all_bills: {str(e)}")
            raise e
    
    def _get_sessions_for_year(self, year: Optional[str]) -> List[str]:
        """Get session identifiers for the specified year(s)"""
        if year == "all":
            # All sessions from 2011 to current
            sessions = []
            for y in range(2011, 2026):  # Up to 2025
                if y % 2 == 1:  # Odd years start new sessions
                    sessions.append(f"{y}{y+1}")  # No hyphen format: "20232024", "20252026"
            return sessions
        elif year == "2024":
            return ["20232024"]  # 2024 is part of 2023-2024 session
        elif year == "2025":
            return ["20252026"]  # 2025 is part of 2025-2026 session
        elif year and year.isdigit():
            # Handle other specific years
            y = int(year)
            if y % 2 == 0:  # Even year
                return [f"{y-1}{y}"]  # No hyphen format
            else:  # Odd year
                return [f"{y}{y+1}"]  # No hyphen format
        else:
            # Default to current session (2025-2026)
            return ["20252026"]  # No hyphen format
    
    def _scrape_session_bills(self, db: Session, session: str) -> Dict:
        """Scrape bills for a specific session"""
        try:
            processed = 0
            created = 0
            updated = 0
            errors = 0
            
            # Scrape bills in batches
            page = 1
            per_page = 20  # Reduced from 50 - OpenStates API v3 has lower limits
            
            while True:
                logging.info(f"Scraping bills page {page} for session {session}")
                
                # Get bills from API for specific session
                bills_data = self.openstates_api.get_california_bills_by_session(
                    session=session,
                    page=page, 
                    per_page=per_page
                )
                
                if not bills_data or not bills_data.get('results'):
                    logging.info(f"No more bills to process for session {session}")
                    break
                    
                bills = bills_data.get('results', [])
                
                for bill_data in bills:
                    try:
                        result = self.process_single_bill(db, bill_data)
                        processed += 1
                        
                        if result == "created":
                            created += 1
                        elif result == "updated":
                            updated += 1
                            
                    except Exception as e:
                        errors += 1
                        logging.error(f"Error processing bill: {str(e)}")
                        continue
                
                page += 1
                
                # Limit to prevent infinite loops
                if page > 1000:
                    logging.warning(f"Reached page limit for session {session}")
                    break
            
            return {
                "processed": processed,
                "created": created,
                "updated": updated,
                "errors": errors
            }
            
        except Exception as e:
            logging.error(f"Error scraping session {session}: {str(e)}")
            return {
                "processed": 0,
                "created": 0,
                "updated": 0,
                "errors": 1
            }

    def process_single_bill(self, db: Session, bill_data: Dict) -> str:
        """Process a single bill with comprehensive data extraction and AI analysis"""
        bill_id = bill_data.get('id')
        if not bill_id:
            raise ValueError("Bill ID is required")
            
        # Check if bill already exists with comprehensive data
        existing_bill = get_bill(db, bill_id)
        
        # Extract comprehensive bill information
        bill_identifier = bill_data.get('identifier', '')
        title = bill_data.get('title', '')
        classification = bill_data.get('classification', [])
        subject = bill_data.get('subject', [])
        
        # Extract session and jurisdiction info
        session = bill_data.get('session', '')
        jurisdiction = bill_data.get('jurisdiction', {})
        jurisdiction_name = jurisdiction.get('name', '') if jurisdiction else ''
        
        # Extract organization info (Assembly/Senate)
        from_organization = bill_data.get('from_organization', {})
        chamber = from_organization.get('name', '') if from_organization else ''
        
        # Extract dates and convert to datetime objects
        created_at = self.parse_date_safely(bill_data.get('created_at', ''))
        updated_at = self.parse_date_safely(bill_data.get('updated_at', ''))
        first_action_date = self.parse_date_safely(bill_data.get('first_action_date', ''))
        latest_action_date = self.parse_date_safely(bill_data.get('latest_action_date', ''))
        latest_action_description = bill_data.get('latest_action_description', '')
        latest_passage_date = self.parse_date_safely(bill_data.get('latest_passage_date', ''))
        
        # Extract abstracts and summaries
        abstracts = bill_data.get('abstracts', [])
        existing_summary = bill_data.get('summary', '')
        
        # Extract sponsorships (authors/sponsors)
        sponsorships = bill_data.get('sponsorships', [])
        sponsors = []
        for sponsorship in sponsorships:
            sponsor_info = {
                'name': sponsorship.get('name', ''),
                'classification': sponsorship.get('classification', ''),
                'primary': sponsorship.get('primary', False)
            }
            sponsors.append(sponsor_info)
        
        # Extract actions history
        actions = bill_data.get('actions', [])
        action_history = []
        for action in actions:
            action_info = {
                'date': action.get('date', ''),
                'description': action.get('description', ''),
                'organization': action.get('organization', {}).get('name', '') if action.get('organization') else '',
                'classification': action.get('classification', [])
            }
            action_history.append(action_info)
        
        # Extract sources and URLs
        sources = bill_data.get('sources', [])
        openstates_url = bill_data.get('openstates_url', '')
        
        # Extract extras (tags, impact clause, etc.)
        extras = bill_data.get('extras', {})
        tags = extras.get('tags', []) if extras else []
        impact_clause = extras.get('impact_clause', '') if extras else ''
        
        # Prepare text for AI analysis (combine available text sources)
        text_for_ai = []
        if title:
            text_for_ai.append(f"Title: {title}")
        if abstracts:
            for abstract in abstracts:
                if isinstance(abstract, dict):
                    text_for_ai.append(f"Abstract: {abstract.get('abstract', '')}")
                else:
                    text_for_ai.append(f"Abstract: {abstract}")
        if impact_clause:
            text_for_ai.append(f"Impact Clause: {impact_clause}")
        if latest_action_description:
            text_for_ai.append(f"Latest Action: {latest_action_description}")
            
        full_text = "\n\n".join(text_for_ai)
        
        # Generate comprehensive AI summary if we don't have one or if this is a new bill
        ai_summary_data = {}
        if not existing_bill or not existing_bill.summary:
            try:
                logging.info(f"Generating AI summary for bill {bill_identifier} ({bill_id})")
                ai_summary_data = self.openai_service.generate_bill_summary(
                    title=title,
                    bill_text=full_text,
                    bill_id=bill_identifier
                )
                if ai_summary_data:
                    logging.info(f"Successfully generated AI summary for {bill_identifier}")
                else:
                    logging.warning(f"AI summary generation returned empty for {bill_identifier}")
            except Exception as e:
                logging.error(f"Failed to generate AI summary for {bill_identifier}: {str(e)}")
                ai_summary_data = {}
        
        # Prepare comprehensive bill data for database
        bill_summary_data = {
            "bill_id": bill_id,
            "identifier": bill_identifier,
            "title": title,
            "summary": ai_summary_data.get('summary', existing_summary),
            "status": self.extract_detailed_status(bill_data),
            "classification": classification,
            "subject": subject,
            "session": session,
            "jurisdiction": jurisdiction_name,
            "chamber": chamber,
            "sponsors": sponsors,
            "action_history": action_history,
            "created_at": created_at,
            "updated_at": updated_at,
            "first_action_date": first_action_date,
            "latest_action_date": latest_action_date,
            "latest_action_description": latest_action_description,
            "latest_passage_date": latest_passage_date,
            "sources": sources,
            "openstates_url": openstates_url,
            "tags": tags,
            "impact_clause": impact_clause,
            # AI-generated fields
            "key_provisions": ai_summary_data.get('key_provisions', []),
            "impact": ai_summary_data.get('impact', ''),
            "ai_analysis": {
                "title": ai_summary_data.get('title', ''),
                "summary": ai_summary_data.get('summary', ''),
                "key_provisions": ai_summary_data.get('key_provisions', []),
                "impact": ai_summary_data.get('impact', ''),
                "status": ai_summary_data.get('status', ''),
                "generated_at": datetime.now().isoformat() if ai_summary_data else None
            }
        }
        
        if existing_bill:
            # Update existing bill with new comprehensive data
            update_bill(db, bill_id, bill_summary_data)
            logging.info(f"Updated bill {bill_identifier} with comprehensive data")
            return "updated"
        else:
            # Create new bill with comprehensive data
            create_bill(db, bill_summary_data)
            logging.info(f"Created new bill {bill_identifier} with comprehensive data")
            return "created"
    
    def extract_detailed_status(self, bill_data: Dict) -> str:
        """Extract detailed bill status from bill data"""
        # First try the direct latest action description
        latest_action = bill_data.get('latest_action_description', '')
        if latest_action:
            return latest_action[:200]  # Limit length but keep more detail
            
        # Fallback to actions array
        actions = bill_data.get('actions', [])
        if not actions:
            return "unknown"
            
        # Get the latest action
        try:
            latest_action_obj = max(actions, key=lambda x: x.get('date', ''))
            description = latest_action_obj.get('description', 'unknown')
            date = latest_action_obj.get('date', '')
            org = latest_action_obj.get('organization', {}).get('name', '') if latest_action_obj.get('organization') else ''
            
            # Combine information for more detailed status
            status_parts = []
            if description:
                status_parts.append(description)
            if date:
                status_parts.append(f"on {date}")
            if org:
                status_parts.append(f"in {org}")
                
            return " ".join(status_parts)[:200]
        except Exception as e:
            logging.warning(f"Error extracting status: {str(e)}")
            return "unknown"
    
    def scrape_bill_on_demand(self, bill_id: str) -> Optional[Dict]:
        """Scrape a specific bill if it doesn't exist in database"""
        try:
            db = SessionLocal()
            
            # Check if bill exists in database
            existing_bill = get_bill(db, bill_id)
            if existing_bill:
                db.close()
                return existing_bill.to_dict()
            
            # Fetch from API
            bill_data = self.openstates_api.get_bill_by_id(bill_id)
            if not bill_data:
                db.close()
                return None
                
            # Process and save
            self.process_single_bill(db, bill_data)
            
            # Return the saved bill
            saved_bill = get_bill(db, bill_id)
            db.close()
            
            return saved_bill.to_dict() if saved_bill else None
            
        except Exception as e:
            logging.error(f"Error in scrape_bill_on_demand for {bill_id}: {str(e)}")
            return None
