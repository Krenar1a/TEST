from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.crud.base import CRUDBase
from app.models.bills import BillCache
from app.schemas import BillCacheCreate, BillCacheUpdate
import json
from datetime import datetime, timedelta


class CRUDBillCache(CRUDBase[BillCache, BillCacheCreate, BillCacheUpdate]):
    """CRUD operations for BillCache model"""
    
    def get_by_bill_id(self, db: Session, *, bill_id: str) -> Optional[BillCache]:
        """Get cached bill data by bill_id"""
        return db.query(BillCache).filter(BillCache.bill_id == bill_id).first()
    
    def get_recent_cached(self, db: Session, *, limit: int = 10) -> List[BillCache]:
        """Get recent cached bills ordered by creation date"""
        return (
            db.query(BillCache)
            .order_by(desc(BillCache.created_at))
            .limit(limit)
            .all()
        )
    
    def create_or_update_cache(
        self, 
        db: Session, 
        *, 
        bill_id: str,
        data: dict
    ) -> BillCache:
        """Create new cache entry or update existing one"""
        existing_cache = self.get_by_bill_id(db=db, bill_id=bill_id)
        
        if existing_cache:
            # Update existing cache
            return self.update(
                db=db,
                db_obj=existing_cache,
                obj_in={"data": json.dumps(data)}
            )
        else:
            # Create new cache entry
            cache_data = BillCacheCreate(
                bill_id=bill_id,
                data=json.dumps(data)
            )
            return self.create(db=db, obj_in=cache_data)
    
    def get_cached_data_as_dict(self, bill_cache: BillCache) -> dict:
        """Helper method to parse cached data JSON string to dict"""
        if not bill_cache.data:
            return {}
        try:
            return json.loads(bill_cache.data)
        except json.JSONDecodeError:
            return {}
    
    def is_cache_expired(self, bill_cache: BillCache, *, hours: int = 24) -> bool:
        """Check if cache entry is expired (older than specified hours)"""
        if not bill_cache.updated_at:
            return True
        
        expiry_time = datetime.utcnow() - timedelta(hours=hours)
        return bill_cache.updated_at < expiry_time
    
    def delete_by_bill_id(self, db: Session, *, bill_id: str) -> Optional[BillCache]:
        """Delete cached bill data by bill_id"""
        obj = db.query(BillCache).filter(BillCache.bill_id == bill_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def delete_expired_cache(self, db: Session, *, hours: int = 24) -> int:
        """Delete all expired cache entries"""
        expiry_time = datetime.utcnow() - timedelta(hours=hours)
        deleted_count = (
            db.query(BillCache)
            .filter(BillCache.updated_at < expiry_time)
            .delete()
        )
        db.commit()
        return deleted_count
    
    def clear_all_cache(self, db: Session) -> int:
        """Clear all cached bill data"""
        deleted_count = db.query(BillCache).delete()
        db.commit()
        return deleted_count
    
    def get_cache_stats(self, db: Session) -> dict:
        """Get cache statistics"""
        total_cache = self.count(db)
        
        # Count cache entries by age
        now = datetime.utcnow()
        recent_cache = (
            db.query(BillCache)
            .filter(BillCache.updated_at >= now - timedelta(hours=24))
            .count()
        )
        
        old_cache = (
            db.query(BillCache)
            .filter(BillCache.updated_at < now - timedelta(hours=24))
            .count()
        )
        
        return {
            "total": total_cache,
            "recent_24h": recent_cache,
            "older_24h": old_cache
        }


bill_cache_crud = CRUDBillCache(BillCache)
