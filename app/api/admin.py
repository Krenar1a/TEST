from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.models.bills import BillSummary, BillCache
from app.models.admin import AdminUser, APIKey
from app.crud import bill_summary_crud, bill_cache_crud
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import jwt
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AdminStatsResponse(BaseModel):
    total_summaries: int
    total_cached_bills: int
    api_keys_configured: dict

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

class APIKeyRequest(BaseModel):
    service_name: str
    key_value: str
    description: Optional[str] = None

class APIKeyResponse(BaseModel):
    id: int
    service_name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(username: str = Depends(verify_token), db: Session = Depends(get_db)):
    """Get current admin user"""
    user = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Admin login endpoint
    """
    try:
        # Check if admin user exists
        admin_user = db.query(AdminUser).filter(AdminUser.username == request.username).first()
        
        if not admin_user:
            # Create default admin user if doesn't exist
            if request.username == "admin" and request.password == "admin123":
                admin_user = AdminUser(username="admin", is_active=True)
                admin_user.set_password("admin123")
                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
                logging.info("Created default admin user")
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
        
        # Verify password
        if not admin_user.check_password(request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": admin_user.username}, expires_delta=access_token_expires
        )
        
        return LoginResponse(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Get admin dashboard statistics using async CRUD operations
    """
    try:
        # Use CRUD operations instead of direct queries
        total_summaries = bill_summary_crud.count(db)
        total_cached_bills = bill_cache_crud.count(db)
        
        # Check API key configuration from database
        api_keys_configured = {}
        services = ["openstates", "openai", "google_civic", "sendgrid"]
        
        for service in services:
            api_key = db.query(APIKey).filter(APIKey.service_name == service, APIKey.is_active == True).first()
            api_keys_configured[service] = bool(api_key)
        
        return AdminStatsResponse(
            total_summaries=total_summaries,
            total_cached_bills=total_cached_bills,
            api_keys_configured=api_keys_configured
        )
        
    except Exception as e:
        logging.error(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api-keys")
async def get_api_keys(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Get all API keys (without revealing the actual keys)
    """
    try:
        api_keys = db.query(APIKey).all()
        return [
            APIKeyResponse(
                id=key.id,
                service_name=key.service_name,
                description=key.description,
                is_active=key.is_active,
                created_at=key.created_at
            )
            for key in api_keys
        ]
        
    except Exception as e:
        logging.error(f"Error fetching API keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/database")
async def get_database_stats(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Get database management statistics using async CRUD operations
    """
    try:
        # Use CRUD operations for better maintainability
        recent_summaries = bill_summary_crud.get_recent_summaries(db, limit=10)
        recent_cached = bill_cache_crud.get_recent_cached(db, limit=10)
        
        return {
            "total_summaries": bill_summary_crud.count(db),
            "total_cached": bill_cache_crud.count(db),
            "recent_summaries": [
                {
                    "id": s.id,
                    "bill_id": s.bill_id,
                    "title": s.title,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in recent_summaries
            ],
            "recent_cached": [
                {
                    "id": c.id,
                    "bill_id": c.bill_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None
                }
                for c in recent_cached
            ],
            "cache_stats": bill_cache_crud.get_cache_stats(db)
        }
        
    except Exception as e:
        logging.error(f"Error fetching database stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/clear-cache")
async def clear_cache(
    request: dict,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Clear cached data using async CRUD operations
    """
    try:
        cache_type = request.get('cache_type')
        
        if cache_type == "bill_cache":
            deleted = bill_cache_crud.clear_all_cache(db)
            return {"message": f"Cleared {deleted} cached bills", "deleted": deleted}
            
        elif cache_type == "expired":
            # Clear cache older than 24 hours
            deleted = bill_cache_crud.delete_expired_cache(db, hours=24)
            return {"message": f"Cleared {deleted} expired cache entries", "deleted": deleted}
            
        elif cache_type == "all":
            # Clear all cached data (but preserve summaries as they're valuable)
            deleted_cache = bill_cache_crud.clear_all_cache(db)
            return {
                "message": f"Cleared {deleted_cache} cached bills",
                "deleted_cache": deleted_cache,
                "note": "Bill summaries preserved (they contain AI-generated content)"
            }
            
        else:
            raise HTTPException(status_code=400, detail="Invalid cache type")
            
    except Exception as e:
        logging.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/summaries/search")
async def search_summaries(
    q: str = "",
    skip: int = 0,
    limit: int = 20,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Search and filter bill summaries using async CRUD operations
    """
    try:
        if q:
            summaries = bill_summary_crud.search_by_title(db, search_term=q, skip=skip, limit=limit)
        elif status_filter:
            summaries = bill_summary_crud.get_by_status(db, status=status_filter, skip=skip, limit=limit)
        else:
            summaries = bill_summary_crud.get_multi(db, skip=skip, limit=limit)
        
        return {
            "summaries": [
                {
                    "id": s.id,
                    "bill_id": s.bill_id,
                    "title": s.title,
                    "summary": s.summary[:200] + "..." if len(s.summary) > 200 else s.summary,
                    "status": s.status,
                    "key_provisions_count": len(bill_summary_crud.get_key_provisions_as_list(s)),
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in summaries
            ],
            "query": q,
            "status_filter": status_filter,
            "skip": skip,
            "limit": limit,
            "total": bill_summary_crud.count(db)
        }
        
    except Exception as e:
        logging.error(f"Error searching summaries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/summaries/{bill_id}")
async def delete_bill_summary(
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Delete a specific bill summary using async CRUD operations
    """
    try:
        deleted_summary = bill_summary_crud.delete_by_bill_id(db=db, bill_id=bill_id)
        if not deleted_summary:
            raise HTTPException(status_code=404, detail="Bill summary not found")
        
        return {"message": f"Bill summary for {bill_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/cache/stats")
async def get_cache_stats(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Get detailed cache statistics using async CRUD operations
    """
    try:
        return bill_cache_crud.get_cache_stats(db)
        
    except Exception as e:
        logging.error(f"Error fetching cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cache/cleanup")
async def cleanup_expired_cache(
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Clean up expired cache entries using async CRUD operations
    """
    try:
        deleted_count = bill_cache_crud.delete_expired_cache(db=db, hours=hours)
        
        return {
            "message": f"Cleaned up {deleted_count} cache entries older than {hours} hours",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logging.error(f"Error cleaning up cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/test-apis")
async def test_apis(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Test API connections
    """
    results = {}
    
    # Test OpenStates API
    try:
        from app.services.openstates_api import OpenStatesAPI
        api = OpenStatesAPI()
        test_result = api.get_california_bills(per_page=1)
        results['openstates'] = {
            'status': 'success' if test_result else 'error',
            'message': 'API connection successful' if test_result else 'API connection failed'
        }
    except Exception as e:
        results['openstates'] = {'status': 'error', 'message': str(e)}
    
    # Test OpenAI API
    try:
        from app.services.openai_service import OpenAIService
        service = OpenAIService()
        test_result = service.generate_bill_summary("Test Bill", "Test abstract", "test-123")
        results['openai'] = {
            'status': 'success' if test_result else 'error',
            'message': 'API connection successful' if test_result else 'API connection failed'
        }
    except Exception as e:
        results['openai'] = {'status': 'error', 'message': str(e)}
    
    # Test Google Civic API
    try:
        from app.services.google_civic_api import GoogleCivicAPI
        service = GoogleCivicAPI()
        # Test elections endpoint instead of discontinued representatives
        test_result = service.get_elections("Sacramento, CA")
        results['google_civic'] = {
            'status': 'success' if test_result else 'error',
            'message': 'Elections API connection successful' if test_result else 'Elections API connection failed'
        }
    except Exception as e:
        results['google_civic'] = {'status': 'error', 'message': str(e)}
    
    # Test SendGrid API
    try:
        from app.services.sendgrid_service import SendGridService
        service = SendGridService()
        # Just test initialization, not actual sending
        results['sendgrid'] = {
            'status': 'success' if service.api_key else 'error',
            'message': 'API key configured' if service.api_key else 'API key not configured'
        }
    except Exception as e:
        results['sendgrid'] = {'status': 'error', 'message': str(e)}
    
    return results

@router.post("/api-keys")
async def create_or_update_api_key(
    request: APIKeyRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Create or update an API key
    """
    try:
        # Check if API key already exists
        existing_key = db.query(APIKey).filter(APIKey.service_name == request.service_name).first()
        
        if existing_key:
            # Update existing key
            existing_key.key_value = request.key_value
            existing_key.description = request.description
            existing_key.is_active = True
            db.commit()
            db.refresh(existing_key)
            return {"message": f"API key for {request.service_name} updated successfully"}
        else:
            # Create new key
            new_key = APIKey(
                service_name=request.service_name,
                key_value=request.key_value,
                description=request.description,
                is_active=True
            )
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            return {"message": f"API key for {request.service_name} created successfully"}
            
    except Exception as e:
        logging.error(f"Error creating/updating API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/api-keys/{service_name}")
async def delete_api_key(
    service_name: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """
    Delete an API key
    """
    try:
        api_key = db.query(APIKey).filter(APIKey.service_name == service_name).first()
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        db.delete(api_key)
        db.commit()
        return {"message": f"API key for {service_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
