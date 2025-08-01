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
        """
        Scrape representatives for all California locations
        
        NOTE: As of 2025, Google Civic Information API v2 no longer supports
        representative lookups. This method will not fetch new data but will
        return existing database records.
        """
        logging.warning("Google Civic API representatives endpoint discontinued - using database only")
        
        try:
            db = SessionLocal()
            
            # Since API is discontinued, just return database summary
            existing_representatives = db.query(Representative).filter(
                Representative.is_active == True
            ).all()
            
            total_processed = len(existing_representatives)
            
            logging.info(f"Database contains {total_processed} existing representatives")
            
            return {
                "success": True,
                "message": "Google Civic API discontinued - returned existing database records",
                "total_processed": total_processed,
                "total_created": 0,
                "total_updated": 0,
                "total_errors": 0,
                "note": "Google Civic Information API v2 no longer supports representative lookups"
            }
            
        except Exception as e:
            logging.error(f"Error in scrape_all_representatives: {str(e)}")
            return {
                "success": False,
                "message": f"Error accessing database: {str(e)}",
                "total_processed": 0,
                "total_created": 0,
                "total_updated": 0,
                "total_errors": 1
            }
        finally:
            if 'db' in locals():
                db.close()

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
            "address": rep_data.get('address', location),  # Use rep address if available, otherwise location
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
        """
        Scrape representatives for a specific address on-demand
        
        NOTE: As of 2025, Google Civic Information API v2 no longer supports
        representative lookups. This method will only return existing database records.
        """
        logging.warning("Google Civic API representatives endpoint discontinued - using database only")
        
        try:
            db = SessionLocal()
            
            logging.info(f"Searching existing representatives for address: {address}")
            
            # Parse address components
            address_parts = [part.strip() for part in address.split(',')]
            city = address_parts[-2] if len(address_parts) >= 2 else None
            state = address_parts[-1] if address_parts else address
            
            # Check if we already have representatives for this specific city
            if city:
                existing_city_reps = db.query(Representative).filter(
                    Representative.address.ilike(f'%{city},%'),  # Match city followed by comma
                    Representative.is_active == True
                ).all()
                
                if existing_city_reps:
                    logging.info(f"Found {len(existing_city_reps)} existing representatives for {city}")
                    return [self._representative_to_dict(rep) for rep in existing_city_reps]
            
            # Fallback: return all available representatives
            all_representatives = db.query(Representative).filter(
                Representative.is_active == True
            ).all()
            
            logging.info(f"No city-specific representatives found. Returning {len(all_representatives)} general representatives")
            logging.info("Note: Google Civic API no longer supports fresh representative data scraping")
            
            return [self._representative_to_dict(rep) for rep in all_representatives]
            
        except Exception as e:
            logging.error(f"Error retrieving representatives for {address}: {str(e)}")
            return []
        finally:
            if 'db' in locals():
                db.close()
    
    def get_or_scrape_representatives(self, address: str) -> List[Dict]:
        """Get representatives from database or scrape if not found"""
        try:
            db = SessionLocal()
            
            # Parse the address to get city and state
            address_parts = [part.strip() for part in address.split(',')]
            state = address_parts[-1] if address_parts else address
            city = address_parts[-2] if len(address_parts) >= 2 else None
            
            # First try to find representatives for the specific city
            if city:
                # Look for exact city match first - be more precise
                city_reps = db.query(Representative).filter(
                    Representative.address.ilike(f'%{city},%'),  # Match city followed by comma
                    Representative.is_active == True
                ).all()
                
                if city_reps and len(city_reps) >= 3:
                    logging.info(f"Found {len(city_reps)} existing representatives for {city}")
                    return [self._representative_to_dict(rep) for rep in city_reps]
            
            # If no specific city reps found, return all available representatives
            # Since API is discontinued, we can't scrape fresh data
            all_reps = db.query(Representative).filter(
                Representative.is_active == True
            ).all()
            
            if all_reps:
                logging.info(f"No city-specific representatives found. Returning {len(all_reps)} general representatives")
                logging.info("Note: Google Civic API discontinued - cannot scrape fresh data")
                return [self._representative_to_dict(rep) for rep in all_reps]
            else:
                logging.warning(f"No representatives found in database for {address}")
                return []
            
        except Exception as e:
            logging.error(f"Error in get_or_scrape_representatives: {str(e)}")
            return []
        finally:
            if 'db' in locals():
                db.close()
    
    def _representative_to_dict(self, rep: Representative) -> Dict:
        """Convert Representative model to dictionary"""
        return {
            "id": rep.id,
            "name": rep.name,
            "office": rep.office,
            "party": rep.party,
            "level": rep.level,
            "address": rep.address,
            "phone": rep.phone,
            "email": rep.email,
            "website_url": rep.website_url,
            "photo_url": rep.photo_url,
            "is_active": rep.is_active,
            "created_at": rep.created_at.isoformat() if rep.created_at else None,
            "updated_at": rep.updated_at.isoformat() if rep.updated_at else None
        }
