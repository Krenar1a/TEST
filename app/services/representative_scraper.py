"""
Representative scraper service
Handles scraping representatives from Google Civic API and saving to database
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.representatives import Representative
from app.services.google_civic_api import GoogleCivicAPI
from app.crud.representatives import create_representative, get_representative, get_stored_representatives
from datetime import datetime

class RepresentativeScraperService:
    """Service to scrape and store representatives"""
    
    def __init__(self):
        self.google_civic_api = GoogleCivicAPI()
        # List of major cities/areas in California to scrape representatives for
        self.california_locations = [
            "Los Angeles, CA",
            "San Francisco, CA", 
            "San Diego, CA",
            "Sacramento, CA",
            "Oakland, CA",
            "Fresno, CA",
            "Long Beach, CA",
            "Anaheim, CA",
            "Santa Ana, CA",
            "Riverside, CA",
            "Stockton, CA",
            "Bakersfield, CA",
            "San Jose, CA",
            "Berkeley, CA",
            "Pasadena, CA"
        ]
        
    def scrape_all_representatives(self) -> Dict:
        """Scrape representatives for all California locations"""
        try:
            db = SessionLocal()
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_errors = 0
            
            for location in self.california_locations:
                try:
                    logging.info(f"Scraping representatives for {location}")
                    
                    # Get representatives from API
                    representatives_data = self.google_civic_api.get_representatives(location)
                    
                    if not representatives_data or not representatives_data.get('representatives'):
                        logging.warning(f"No representatives found for {location}")
                        continue
                    
                    representatives = representatives_data.get('representatives', [])
                    
                    for rep_data in representatives:
                        try:
                            result = self.process_single_representative(db, rep_data, location)
                            total_processed += 1
                            
                            if result == "created":
                                total_created += 1
                            elif result == "updated":
                                total_updated += 1
                                
                        except Exception as e:
                            total_errors += 1
                            logging.error(f"Error processing representative {rep_data.get('name', 'unknown')}: {str(e)}")
                            
                except Exception as e:
                    total_errors += 1
                    logging.error(f"Error scraping representatives for {location}: {str(e)}")
            
            db.close()
            
            result = {
                "status": "completed",
                "total_processed": total_processed,
                "total_created": total_created,
                "total_updated": total_updated,
                "total_errors": total_errors,
                "locations_scraped": len(self.california_locations),
                "timestamp": datetime.now().isoformat()
            }
            
            logging.info(f"Representative scraping completed: {result}")
            return result
            
        except Exception as e:
            logging.error(f"Error in scrape_all_representatives: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def process_single_representative(self, db: Session, rep_data: Dict, location: str) -> str:
        """Process a single representative and save to database"""
        name = rep_data.get('name', '')
        office = rep_data.get('office', '')
        
        if not name or not office:
            raise ValueError("Representative name and office are required")
        
        # Check if representative already exists (by name and office)
        existing_rep = db.query(Representative).filter(
            Representative.name == name,
            Representative.office == office,
            Representative.is_active == True
        ).first()
        
        # Extract representative information
        party = rep_data.get('party', '')
        level = rep_data.get('level', 'unknown')
        phones = rep_data.get('phones', [])
        emails = rep_data.get('emails', [])
        urls = rep_data.get('urls', [])
        photo_url = rep_data.get('photo_url')
        
        rep_summary_data = {
            "name": name,
            "office": office,
            "party": party,
            "level": level,
            "address": location,
            "phone": phones[0] if phones else None,
            "email": emails[0] if emails else None,
            "website_url": urls[0] if urls else None,
            "photo_url": photo_url
        }
        
        if existing_rep:
            # Update existing representative
            for key, value in rep_summary_data.items():
                if value:  # Only update non-empty values
                    setattr(existing_rep, key, value)
            db.commit()
            return "updated"
        else:
            # Create new representative
            create_representative(db, rep_summary_data)
            return "created"
    
    def scrape_representatives_for_address(self, address: str) -> List[Dict]:
        """Scrape representatives for a specific address on-demand"""
        try:
            db = SessionLocal()
            
            # First check if we have representatives for this general area
            existing_reps = db.query(Representative).filter(
                Representative.address.contains(address.split(',')[-1].strip()),  # Check by state/city
                Representative.is_active == True
            ).all()
            
            if existing_reps:
                db.close()
                return [rep.to_dict() for rep in existing_reps]
            
            # If not found, fetch from API
            representatives_data = self.google_civic_api.get_representatives(address)
            
            if not representatives_data or not representatives_data.get('representatives'):
                db.close()
                return []
            
            # Process and save new representatives
            saved_reps = []
            representatives = representatives_data.get('representatives', [])
            
            for rep_data in representatives:
                try:
                    self.process_single_representative(db, rep_data, address)
                    
                    # Find the saved representative
                    name = rep_data.get('name', '')
                    office = rep_data.get('office', '')
                    saved_rep = db.query(Representative).filter(
                        Representative.name == name,
                        Representative.office == office,
                        Representative.is_active == True
                    ).first()
                    
                    if saved_rep:
                        saved_reps.append(saved_rep.to_dict())
                        
                except Exception as e:
                    logging.error(f"Error processing representative {rep_data.get('name', 'unknown')}: {str(e)}")
            
            db.close()
            return saved_reps
            
        except Exception as e:
            logging.error(f"Error in scrape_representatives_for_address for {address}: {str(e)}")
            return []
    
    def get_or_scrape_representatives(self, address: str) -> List[Dict]:
        """Get representatives from API with fresh detailed data"""
        try:
            # Always fetch fresh data from API for better user experience
            representatives_data = self.google_civic_api.get_representatives(address)
            
            if not representatives_data or not representatives_data.get('representatives'):
                return []
            
            # Return the enhanced API data directly
            return representatives_data.get('representatives', [])
            
        except Exception as e:
            logging.error(f"Error in get_or_scrape_representatives: {str(e)}")
            return []
