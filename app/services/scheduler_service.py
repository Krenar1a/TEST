"""
Scheduler service for running cron jobs
Handles weekly scraping of bills and representatives
"""

import schedule
import time
import threading
import logging
from datetime import datetime
from app.services.bill_scraper import BillScraperService
from app.services.representative_scraper import RepresentativeScraperService

class SchedulerService:
    """Service to manage scheduled tasks"""
    
    def __init__(self):
        self.bill_scraper = BillScraperService()
        self.representative_scraper = RepresentativeScraperService()
        self.running = False
        self.scheduler_thread = None
        
    def setup_jobs(self):
        """Setup all scheduled jobs"""
        # Schedule weekly bill scraping (every Monday at 2 AM)
        schedule.every().monday.at("02:00").do(self.scrape_bills_job)
        
        # Schedule weekly representative scraping (every Monday at 3 AM)
        schedule.every().monday.at("03:00").do(self.scrape_representatives_job)
        
        logging.info("Scheduled jobs setup complete")
        
    def scrape_bills_job(self):
        """Job to scrape all bills"""
        try:
            logging.info("Starting weekly bill scraping job")
            result = self.bill_scraper.scrape_all_bills()
            logging.info(f"Bill scraping completed: {result}")
        except Exception as e:
            logging.error(f"Error in bill scraping job: {str(e)}")
            
    def scrape_representatives_job(self):
        """Job to scrape all representatives"""
        try:
            logging.info("Starting weekly representative scraping job")
            result = self.representative_scraper.scrape_all_representatives()
            logging.info(f"Representative scraping completed: {result}")
        except Exception as e:
            logging.error(f"Error in representative scraping job: {str(e)}")
            
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        self.running = True
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.setup_jobs()
            self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logging.info("Scheduler started")
            
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logging.info("Scheduler stopped")
        
    def run_manual_scraping(self):
        """Run manual scraping for testing"""
        logging.info("Running manual scraping...")
        
        # Run bill scraping
        logging.info("Scraping bills...")
        bills_result = self.bill_scraper.scrape_all_bills()
        
        # Run representative scraping
        logging.info("Scraping representatives...")
        reps_result = self.representative_scraper.scrape_all_representatives()
        
        return {
            "bills": bills_result,
            "representatives": reps_result
        }

# Global scheduler instance
scheduler_service = SchedulerService()
