from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.models.database import engine, SessionLocal, Base
from app.models.admin import AdminUser, APIKey  # Import admin models
from app.models.representatives import Representative  # Import representatives model
from app.api.bills import router as bills_router
from app.api.representatives import router as representatives_router
from app.api.admin import router as admin_router
from app.api.widget import router as widget_router
from app.api.scraper import router as scraper_router
from app.services.openstates_api import OpenStatesAPI
from app.services.openai_service import OpenAIService
from app.services.google_civic_api import GoogleCivicAPI
from app.services.sendgrid_service import SendGridService
from app.services.scheduler_service import scheduler_service

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create FastAPI app
app = FastAPI(
    title="Redbird - California Legislation Tracker API",
    description="API for tracking California legislative bills with AI-powered summaries",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://legal-research-frontend.vercel.app",
        "https://*.vercel.app"  # Allow all Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Start the scheduler for cron jobs
scheduler_service.start()

# Include routers
app.include_router(bills_router, prefix="/api/bills", tags=["bills"])
app.include_router(representatives_router, prefix="/api/representatives", tags=["representatives"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(widget_router, prefix="/api/widget", tags=["widget"])
app.include_router(scraper_router, prefix="/api/scraper", tags=["scraper"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Redbird API is running"}

@app.get("/")
async def root():
    return {"message": "Redbird - California Legislation Tracker API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
