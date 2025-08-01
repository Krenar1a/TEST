"""
SendGrid Email Service
Send email messages on behalf of users for bill notifications and updates
"""

import os
import logging
from typing import Dict, List, Optional
import requests
import json

class SendGridService:
    """Service class for SendGrid email API interactions"""
    
    def __init__(self):
        self.api_key = os.environ.get("SENDGRID_API_KEY", "YOUR_API_KEY")
        self.base_url = "https://api.sendgrid.com/v3"
        self.from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@redbird.app")
        self.from_name = "Redbird - California Legislation Tracker"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def send_bill_notification(self, to_email: str, user_name: str, bill_data: Dict) -> bool:
        """
        Send notification about a new or updated bill
        
        Args:
            to_email: Recipient email address
            user_name: Recipient name
            bill_data: Dictionary containing bill information
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = f"New Bill Alert: {bill_data.get('identifier', 'Unknown Bill')}"
            
            html_content = self._generate_bill_notification_html(user_name, bill_data)
            text_content = self._generate_bill_notification_text(user_name, bill_data)
            
            return self._send_email(
                to_email=to_email,
                to_name=user_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logging.error(f"Error sending bill notification: {str(e)}")
            return False
    
    def send_weekly_digest(self, to_email: str, user_name: str, bills: List[Dict]) -> bool:
        """
        Send weekly digest of new and updated bills
        
        Args:
            to_email: Recipient email address
            user_name: Recipient name
            bills: List of bill dictionaries
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = "Your Weekly California Legislation Digest"
            
            html_content = self._generate_weekly_digest_html(user_name, bills)
            text_content = self._generate_weekly_digest_text(user_name, bills)
            
            return self._send_email(
                to_email=to_email,
                to_name=user_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logging.error(f"Error sending weekly digest: {str(e)}")
            return False
    
    def send_representative_contact(self, to_email: str, user_name: str, 
                                  user_email: str, message: str, bill_id: str) -> bool:
        """
        Send message to elected representative on behalf of user
        
        Args:
            to_email: Representative's email address
            user_name: User's name
            user_email: User's email address
            message: User's message
            bill_id: Bill identifier being discussed
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = f"Constituent Message Regarding {bill_id}"
            
            html_content = self._generate_representative_contact_html(
                user_name, user_email, message, bill_id
            )
            text_content = self._generate_representative_contact_text(
                user_name, user_email, message, bill_id
            )
            
            return self._send_email(
                to_email=to_email,
                to_name="Representative",
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                reply_to_email=user_email,
                reply_to_name=user_name
            )
            
        except Exception as e:
            logging.error(f"Error sending representative contact: {str(e)}")
            return False
    
    def _send_email(self, to_email: str, to_name: str, subject: str, 
                   html_content: str, text_content: str, 
                   reply_to_email: str = None, reply_to_name: str = None) -> bool:
        """
        Send email via SendGrid API
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/mail/send"
            
            payload = {
                "personalizations": [{
                    "to": [{"email": to_email, "name": to_name}],
                    "subject": subject
                }],
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": text_content
                    },
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            if reply_to_email:
                payload["reply_to"] = {
                    "email": reply_to_email,
                    "name": reply_to_name or reply_to_email
                }
            
            response = requests.post(
                endpoint, 
                headers=self.headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 202:
                logging.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logging.error(f"SendGrid API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending email via SendGrid: {str(e)}")
            return False
    
    def _generate_bill_notification_html(self, user_name: str, bill_data: Dict) -> str:
        """Generate HTML content for bill notification email"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #c8102e; color: white; padding: 20px; text-align: center;">
                <h1>Redbird Bill Alert</h1>
            </div>
            
            <div style="padding: 20px;">
                <p>Hi {user_name},</p>
                
                <p>A new bill has been introduced that matches your interests:</p>
                
                <div style="border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <h2 style="color: #c8102e; margin-top: 0;">{bill_data.get('identifier', 'Unknown')}</h2>
                    <h3>{bill_data.get('title', 'No title available')}</h3>
                    <p><strong>Chamber:</strong> {bill_data.get('chamber', 'Unknown')}</p>
                    <p><strong>Status:</strong> {bill_data.get('status', 'Unknown')}</p>
                </div>
                
                <p>View the full bill details and AI summary on Redbird.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #c8102e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                        View Bill Details
                    </a>
                </div>
                
                <p style="color: #666; font-size: 12px;">
                    You received this email because you signed up for bill notifications on Redbird.
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_bill_notification_text(self, user_name: str, bill_data: Dict) -> str:
        """Generate text content for bill notification email"""
        return f"""
Hi {user_name},

A new bill has been introduced that matches your interests:

{bill_data.get('identifier', 'Unknown')}: {bill_data.get('title', 'No title available')}
Chamber: {bill_data.get('chamber', 'Unknown')}
Status: {bill_data.get('status', 'Unknown')}

View the full bill details and AI summary on Redbird.

You received this email because you signed up for bill notifications on Redbird.
        """
    
    def _generate_weekly_digest_html(self, user_name: str, bills: List[Dict]) -> str:
        """Generate HTML content for weekly digest email"""
        bills_html = ""
        for bill in bills:
            bills_html += f"""
            <div style="border-bottom: 1px solid #eee; padding: 15px 0;">
                <h3 style="color: #c8102e; margin-top: 0;">{bill.get('identifier', 'Unknown')}</h3>
                <p><strong>{bill.get('title', 'No title available')}</strong></p>
                <p>Status: {bill.get('status', 'Unknown')}</p>
            </div>
            """
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #c8102e; color: white; padding: 20px; text-align: center;">
                <h1>Your Weekly Legislation Digest</h1>
            </div>
            
            <div style="padding: 20px;">
                <p>Hi {user_name},</p>
                
                <p>Here are the latest California bills from this week:</p>
                
                {bills_html}
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #c8102e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                        View All Bills
                    </a>
                </div>
                
                <p style="color: #666; font-size: 12px;">
                    You received this email because you signed up for weekly digests on Redbird.
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_weekly_digest_text(self, user_name: str, bills: List[Dict]) -> str:
        """Generate text content for weekly digest email"""
        bills_text = ""
        for bill in bills:
            bills_text += f"\n{bill.get('identifier', 'Unknown')}: {bill.get('title', 'No title available')}\nStatus: {bill.get('status', 'Unknown')}\n"
        
        return f"""
Hi {user_name},

Here are the latest California bills from this week:
{bills_text}

View all bills on Redbird.

You received this email because you signed up for weekly digests on Redbird.
        """
    
    def _generate_representative_contact_html(self, user_name: str, user_email: str, 
                                            message: str, bill_id: str) -> str:
        """Generate HTML content for representative contact email"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #c8102e; color: white; padding: 20px; text-align: center;">
                <h1>Constituent Message</h1>
            </div>
            
            <div style="padding: 20px;">
                <p><strong>From:</strong> {user_name} ({user_email})</p>
                <p><strong>Regarding:</strong> {bill_id}</p>
                
                <div style="border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <p>{message}</p>
                </div>
                
                <p style="color: #666; font-size: 12px;">
                    This message was sent via Redbird - California Legislation Tracker
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_representative_contact_text(self, user_name: str, user_email: str, 
                                            message: str, bill_id: str) -> str:
        """Generate text content for representative contact email"""
        return f"""
From: {user_name} ({user_email})
Regarding: {bill_id}

{message}

This message was sent via Redbird - California Legislation Tracker
        """