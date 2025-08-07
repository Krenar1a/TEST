import os
import requests
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.admin import APIKey

class OpenStatesAPI:
    """Service class for interacting with OpenStates API"""
    
    def __init__(self):
        self.base_url = "https://v3.openstates.org"
        # Get API key from database instead of environment
        self.api_key = self._get_api_key_from_db()
        if self.api_key:
            self.headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
        else:
            self.headers = {
                "Content-Type": "application/json"
            }
    
    def _get_api_key_from_db(self) -> Optional[str]:
        """Get OpenStates API key from database"""
        try:
            db = SessionLocal()
            api_key_record = db.query(APIKey).filter(
                APIKey.service_name == "openstates", 
                APIKey.is_active == True
            ).first()
            db.close()
            
            if api_key_record:
                logging.info("Found OpenStates API key in database")
                return api_key_record.key_value
            else:
                logging.info("No OpenStates API key found in database")
                return None
        except Exception as e:
            logging.error(f"Error getting API key from database: {str(e)}")
            return None
    
    def get_california_bills(self, search: str = "", sort: str = "date", 
                           category: str = "", page: int = 1, per_page: int = 20) -> Optional[Dict]:
        """
        Fetch California legislative bills from OpenStates API
        
        Args:
            search: Search query for bill title/content
            sort: Sort parameter (date, chamber, status)
            category: Filter by category
            page: Page number for pagination
            per_page: Number of results per page
        
        Returns:
            Dictionary containing bills data or None if error
        """
        # Require API key
        if not self.api_key:
            logging.error("No OpenStates API key found in database")
            return None
        
        try:
            # Build API endpoint
            endpoint = f"{self.base_url}/bills"
            
            # Build query parameters
            params = {
                "jurisdiction": "ca",  # California jurisdiction required by API
                "per_page": per_page,
                "page": page
                # Note: include parameter causing 422 errors, removing for compatibility
                # "include": "sponsorships,actions,sources"
            }

            # Add search if provided
            if search:
                params["q"] = search

            # Note: OpenStates API v3 is strict about sort parameters
            # Removing sort for now to ensure API compatibility
            # TODO: Verify valid sort options with OpenStates API v3
            
            # Make API request
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Successfully fetched {len(data.get('results', []))} bills")
                return data
            elif response.status_code == 401:
                logging.error("OpenStates API authentication failed")
                return None
            elif response.status_code == 429:
                logging.error("OpenStates API rate limit exceeded")
                return None
            else:
                logging.error(f"OpenStates API error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error("OpenStates API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"OpenStates API request failed: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in OpenStates API: {str(e)}")
            return None
    
    def get_bill_by_id(self, bill_id: str) -> Optional[Dict]:
        """
        Fetch a specific bill by ID from OpenStates API
        
        Args:
            bill_id: The bill identifier
            
        Returns:
            Dictionary containing bill data or None if error
        """
        # Require API key
        if not self.api_key:
            logging.error(f"No OpenStates API key found in database for bill {bill_id}")
            return None
        
        try:
            endpoint = f"{self.base_url}/bills/{bill_id}"
            params = {
                # Note: include parameter causing 422 errors, removing for compatibility
                # "include": "sponsorships,actions,sources,abstracts,other_titles"
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Successfully fetched bill {bill_id}")
                return data
            elif response.status_code == 404:
                logging.warning(f"Bill {bill_id} not found")
                return None
            elif response.status_code == 401:
                logging.error(f"OpenStates API authentication failed for bill {bill_id}")
                return None
            else:
                logging.error(f"OpenStates API error for bill {bill_id}: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"OpenStates API request timed out for bill {bill_id}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"OpenStates API request failed for bill {bill_id}: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching bill {bill_id}: {str(e)}")
            return None
    
    def get_california_bills_by_session(self, session: str, page: int = 1, per_page: int = 50) -> Optional[Dict]:
        """
        Fetch California bills for a specific session
        
        Args:
            session: Session identifier (e.g., "2023-2024", "2025-2026")
            page: Page number for pagination
            per_page: Number of results per page
            
        Returns:
            Dictionary containing bills data or None if error
        """
        if not self.api_key:
            logging.error(f"No OpenStates API key found in database for session {session}")
            return None
        
        try:
            endpoint = f"{self.base_url}/bills"
            params = {
                "jurisdiction": "ca",
                "session": session,
                "per_page": per_page,
                "page": page
                # Note: include parameter causing issues, removing for compatibility
                # "include": "sponsorships,actions,sources,abstracts"
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Successfully fetched {len(data.get('results', []))} bills for session {session}")
                return data
            elif response.status_code == 401:
                logging.error(f"OpenStates API authentication failed for session {session}")
                return None
            elif response.status_code == 429:
                logging.error(f"OpenStates API rate limit exceeded for session {session}")
                return None
            else:
                logging.error(f"OpenStates API error for session {session}: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"OpenStates API request timed out for session {session}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"OpenStates API request failed for session {session}: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching session {session}: {str(e)}")
            return None

    def search_bills(self, query: str, jurisdiction: str = "ca") -> Optional[List[Dict]]:
        """
        Search for bills by query
        
        Args:
            query: Search query
            jurisdiction: State jurisdiction (default: ca for California)
            
        Returns:
            List of bill dictionaries or None if error
        """
        try:
            endpoint = f"{self.base_url}/bills"
            params = {
                "jurisdiction": jurisdiction,
                "q": query,
                "session": "20232024",  # Fixed session format
                "per_page": 50
                # Note: include parameter causing issues, removing for compatibility
                # "include": "sponsorships,actions"
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                logging.error(f"OpenStates search API error: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error searching bills: {str(e)}")
            return None

    def get_california_legislators(self) -> Optional[Dict]:
        """
        Get current California legislators from OpenStates API
        
        Returns:
            Dictionary containing legislators data or None if error
        """
        # Require API key
        if not self.api_key:
            logging.error("No OpenStates API key found in database")
            return None
        
        try:
            # Build API endpoint for people (legislators)
            endpoint = f"{self.base_url}/people"
            
            # Build query parameters
            params = {
                "jurisdiction": "ca",  # California jurisdiction
                "per_page": 50,  # Max allowed by API
                "page": 1
                # Note: include parameter causing 422 errors, removing for compatibility
            }
            
            # Make API request
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Successfully fetched {len(data.get('results', []))} California legislators")
                return data
            elif response.status_code == 401:
                logging.error("OpenStates API authentication failed for legislators")
                return None
            elif response.status_code == 429:
                logging.error("OpenStates API rate limit exceeded for legislators")
                return None
            else:
                logging.error(f"OpenStates legislators API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error("OpenStates legislators API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"OpenStates legislators API request failed: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching California legislators: {str(e)}")
            return None
