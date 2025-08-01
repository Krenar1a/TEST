"""
Google Civic Information API Service
Retrieves elected officials based on user address
"""

import os
import requests
import logging
from typing import Dict, List, Optional
from app.models.database import SessionLocal
from app.models.admin import APIKey

class GoogleCivicAPI:
    """Service class for Google Civic Information API interactions"""
    
    def __init__(self):
        self.base_url = "https://www.googleapis.com/civicinfo/v2"
    
    def _get_api_key_from_db(self) -> Optional[str]:
        """Get Google Civic API key from database"""
        try:
            db = SessionLocal()
            api_key_record = db.query(APIKey).filter(
                APIKey.service_name == "google_civic", 
                APIKey.is_active == True
            ).first()
            db.close()
            
            if api_key_record:
                logging.info("Found Google Civic API key in database")
                return api_key_record.key_value
            else:
                logging.info("No Google Civic API key found in database")
                return None
        except Exception as e:
            logging.error(f"Error getting Google Civic API key from database: {str(e)}")
            return None
    
    def get_representatives(self, address: str, levels: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Get elected officials for a given address
        
        NOTE: As of 2025, Google Civic Information API v2 no longer supports
        representative lookups. This method will fallback to OpenStates API.
        
        Args:
            address: Street address, city, state, or zip code
            levels: List of government levels ('federal', 'state', 'local')
            
        Returns:
            Dictionary containing representatives data from OpenStates API
        """
        logging.warning(f"Google Civic Information API representatives endpoint is discontinued")
        logging.info(f"Falling back to OpenStates API for representatives lookup: {address}")
        
        try:
            # Import here to avoid circular imports
            from app.services.openstates_api import OpenStatesAPI
            
            openstates_api = OpenStatesAPI()
            
            # Get California legislators from OpenStates
            representatives_data = {
                "address": address,
                "representatives": [],
                "source": "OpenStates API (California legislators)",
                "note": "Showing California state legislators"
            }
            
            # Fetch current California legislators
            try:
                # Get current session California legislators
                legislators_response = openstates_api.get_california_legislators()
                
                if legislators_response and isinstance(legislators_response, dict):
                    legislators = legislators_response.get('results', [])
                    
                    # Process legislators into representatives format
                    for legislator in legislators[:20]:  # Limit to first 20 for performance
                        try:
                            current_role = legislator.get('current_role', {})
                            
                            # Extract contact information directly from legislator object
                            email = legislator.get('email', '')
                            phone = ""
                            website = ""
                            
                            # Check for additional contact details in extras or other fields
                            extras = legislator.get('extras', {})
                            if not email and 'email' in extras:
                                email = extras.get('email', '')
                            
                            # Extract additional details
                            links = legislator.get('links', [])
                            if not website and links:
                                website = links[0].get('url', '')
                            
                            # Check OpenStates URL as backup
                            if not website:
                                website = legislator.get('openstates_url', '')
                            
                            # Format office title with more detail
                            chamber = current_role.get('org_classification', 'legislature')
                            title = current_role.get('title', 'Legislator')
                            district = current_role.get('district', 'Unknown District')
                            
                            if chamber == 'upper':
                                chamber_name = "State Senate"
                            elif chamber == 'lower':
                                chamber_name = "State Assembly"
                            else:
                                chamber_name = "Legislature"
                            
                            office_title = f"{title}, District {district} ({chamber_name})"
                            
                            # Extract party information - fix the party lookup
                            party = current_role.get('party', legislator.get('party', 'Unknown'))
                            if party == 'Democratic':
                                party_full = 'Democratic (D)'
                            elif party == 'Republican':
                                party_full = 'Republican (R)'
                            elif party == 'Independent':
                                party_full = 'Independent (I)'
                            else:
                                party_full = party if party != 'Unknown' else 'Unknown'
                            
                            rep_data = {
                                "name": legislator.get('name', 'Unknown'),
                                "office": office_title,
                                "party": party_full,
                                "level": "state",
                                "chamber": chamber_name,
                                "district": district,
                                "title": title,
                                "phone": phone,
                                "email": email,
                                "website": website,
                                "photo_url": legislator.get('image', ''),
                                "openstates_id": legislator.get('id', ''),
                                "biography": legislator.get('biography', ''),
                                "birth_date": legislator.get('birth_date', ''),
                                "gender": legislator.get('gender', ''),
                                "given_name": legislator.get('given_name', ''),
                                "family_name": legislator.get('family_name', ''),
                                "sort_name": legislator.get('sort_name', ''),
                                "extras": legislator.get('extras', {}),
                                "sources": legislator.get('sources', []),
                                "created_at": legislator.get('created_at', ''),
                                "updated_at": legislator.get('updated_at', ''),
                                "openstates_url": legislator.get('openstates_url', '')
                            }
                            representatives_data["representatives"].append(rep_data)
                        except Exception as rep_error:
                            logging.error(f"Error processing legislator: {rep_error}")
                            continue
                
                logging.info(f"Found {len(representatives_data['representatives'])} California legislators for address: {address}")
                
            except Exception as api_error:
                logging.error(f"Error fetching from OpenStates API: {api_error}")
            
            return representatives_data
            
        except Exception as e:
            logging.error(f"Error in OpenStates fallback for representatives: {str(e)}")
            return None
    
    def _process_representatives_data(self, data: Dict) -> Dict:
        """Process and structure representatives data"""
        processed = {
            "address": data.get("normalizedInput", {}).get("line1", ""),
            "representatives": []
        }
        
        offices = data.get("offices", [])
        officials = data.get("officials", [])
        
        for office in offices:
            office_name = office.get("name", "")
            level = office.get("levels", ["unknown"])[0]
            
            for official_index in office.get("officialIndices", []):
                if official_index < len(officials):
                    official = officials[official_index]
                    
                    representative = {
                        "name": official.get("name", ""),
                        "office": office_name,
                        "level": level,
                        "party": official.get("party", ""),
                        "phones": official.get("phones", []),
                        "emails": official.get("emails", []),
                        "urls": official.get("urls", []),
                        "photo_url": official.get("photoUrl", "")
                    }
                    
                    processed["representatives"].append(representative)
        
        return processed
    
    def get_elections(self, address: Optional[str] = None) -> Optional[Dict]:
        """
        Get upcoming elections for a given address
        
        Args:
            address: Street address, city, state, or zip code (optional)
            
        Returns:
            Dictionary containing elections data or None if error
        """
        # Get API key from database
        api_key = self._get_api_key_from_db()
        
        if not api_key:
            logging.warning("No Google Civic API key configured")
            return None
            
        try:
            endpoint = f"{self.base_url}/elections"
            
            params = {"key": api_key}
            
            if address:
                params["address"] = address
            
            response = requests.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logging.info("Successfully retrieved elections data")
                return data
            else:
                logging.error(f"Google Civic API elections error: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error retrieving elections: {str(e)}")
            return None