import os
import json
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.admin import APIKey

# Try to import OpenAI, but handle if it's not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    logging.warning("OpenAI library not available")

class OpenAIService:
    """Service class for OpenAI API interactions"""
    
    def __init__(self):
        # Get API key from database instead of environment
        self.api_key = self._get_api_key_from_db()
        self.client = None
        
        if OPENAI_AVAILABLE and OpenAI and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        
        if not self.client:
            logging.info("OpenAI client not available - API key not configured or library not available")
    
    def _get_api_key_from_db(self) -> Optional[str]:
        """Get OpenAI API key from database"""
        try:
            db = SessionLocal()
            api_key_record = db.query(APIKey).filter(
                APIKey.service_name == "openai", 
                APIKey.is_active == True
            ).first()
            db.close()
            
            if api_key_record:
                logging.info("Found OpenAI API key in database")
                return api_key_record.key_value
            else:
                logging.info("No OpenAI API key found in database")
                return None
        except Exception as e:
            logging.error(f"Error getting OpenAI API key from database: {str(e)}")
            return None
    
    def generate_bill_summary(self, title: str, bill_text: str, bill_id: str) -> Optional[dict]:
        """
        Generate comprehensive AI summary for a legislative bill
        
        Args:
            title: Bill title
            bill_text: Full text or abstracts of the bill
            bill_id: Bill identifier (e.g., "AB 100")
        
        Returns:
            Dictionary containing AI-generated analysis or None if failed
        """
        if not self.client:
            logging.error("OpenAI API key not configured or client not available")
            return None
        
        try:
            # Construct enhanced prompt for comprehensive bill analysis
            prompt = f"""
            Analyze the following California legislative bill and provide a comprehensive structured analysis in JSON format.

            Bill ID: {bill_id}
            Title: {title}
            
            Full Text:
            {bill_text[:12000]}  # Increased limit for more comprehensive analysis
            
            Please provide a JSON response with the following structure:
            {{
                "title": "Clear, concise title (improved if needed)",
                "summary": "3-4 sentence plain English summary explaining what this bill does, why it matters, and its main goals",
                "key_provisions": [
                    "Detailed bullet point 1 (what it establishes/changes)",
                    "Detailed bullet point 2 (implementation details)",
                    "Detailed bullet point 3 (requirements/restrictions)",
                    "Detailed bullet point 4 (funding/timeline if applicable)"
                ],
                "impact": "Comprehensive description of who this affects (individuals, businesses, organizations), how it affects them, and potential benefits or concerns",
                "status": "Current legislative status and what it means in plain English",
                "fiscal_impact": "Description of any costs, savings, or financial implications mentioned",
                "effective_date": "When this would take effect if passed",
                "urgency": "Whether this is marked as urgent legislation and why"
            }}
            
            Guidelines:
            - Use plain English that any citizen can understand
            - Explain technical terms when necessary
            - Focus on practical implications for real people
            - Include specific details about implementation
            - Mention any controversial or notable aspects
            - If information is not available in the text, use "Not specified" rather than guessing
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing legislative bills and creating clear, "
                                 "accessible summaries for the general public. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse the JSON response
            result = json.loads(response.choices[0].message.content)
            
            # Validate required fields
            required_fields = ['title', 'summary', 'key_provisions', 'impact']
            for field in required_fields:
                if field not in result:
                    logging.warning(f"Missing field {field} in OpenAI response")
                    result[field] = "Information not available"
            
            # Ensure key_provisions is a list
            if not isinstance(result.get('key_provisions'), list):
                result['key_provisions'] = [str(result.get('key_provisions', ''))]
            
            logging.info(f"Successfully generated summary for bill {bill_id}")
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse OpenAI JSON response: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Error generating bill summary with OpenAI: {str(e)}")
            return None
    
    def analyze_bill_category(self, title: str, abstract: str = "") -> Optional[str]:
        """
        Use AI to categorize a bill
        
        Args:
            title: Bill title
            abstract: Bill abstract/summary
            
        Returns:
            Category string or None if error
        """
        try:
            prompt = f"""
            Categorize this California legislative bill into one of these categories:
            - Housing
            - Health
            - Crime
            - Education
            - Environment
            - Transportation
            - Budget
            - Other
            
            Title: {title}
            Abstract: {abstract}
            
            Respond with just the category name.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at categorizing legislative bills. "
                                 "Respond with only the category name."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=20,
                temperature=0.1
            )
            
            category = response.choices[0].message.content.strip()
            return category
            
        except Exception as e:
            logging.error(f"Error categorizing bill with OpenAI: {str(e)}")
            return "Other"
