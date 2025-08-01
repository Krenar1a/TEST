from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.representatives import Representative

def create_representative(db: Session, representative_data: dict) -> Representative:
    """Create a new representative"""
    db_representative = Representative(**representative_data)
    db.add(db_representative)
    db.commit()
    db.refresh(db_representative)
    return db_representative

def get_representative(db: Session, representative_id: int) -> Optional[Representative]:
    """Get a representative by ID"""
    return db.query(Representative).filter(Representative.id == representative_id).first()

def get_stored_representatives(db: Session, skip: int = 0, limit: int = 100, level: Optional[str] = None) -> List[Representative]:
    """Get all representatives with optional filtering"""
    query = db.query(Representative).filter(Representative.is_active == True)
    if level:
        query = query.filter(Representative.level == level)
    return query.offset(skip).limit(limit).all()

def update_representative(db: Session, representative_id: int, representative_data: dict) -> Optional[Representative]:
    """Update a representative"""
    db_representative = db.query(Representative).filter(Representative.id == representative_id).first()
    if db_representative:
        for key, value in representative_data.items():
            setattr(db_representative, key, value)
        db.commit()
        db.refresh(db_representative)
    return db_representative

def delete_representative(db: Session, representative_id: int) -> bool:
    """Delete a representative (soft delete by setting is_active = False)"""
    db_representative = db.query(Representative).filter(Representative.id == representative_id).first()
    if db_representative:
        db_representative.is_active = False
        db.commit()
        return True
    return False

def hard_delete_representative(db: Session, representative_id: int) -> bool:
    """Hard delete a representative (permanently remove from database)"""
    db_representative = db.query(Representative).filter(Representative.id == representative_id).first()
    if db_representative:
        db.delete(db_representative)
        db.commit()
        return True
    return False
