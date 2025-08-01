from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.bills import BillSummary
import json

def create_bill(db: Session, bill_data: dict) -> BillSummary:
    """Create a new bill summary with comprehensive data"""
    # Convert complex data structures to JSON strings
    json_fields = ['key_provisions', 'sponsors', 'action_history', 'sources', 'tags', 'classification', 'subject', 'ai_analysis']
    for field in json_fields:
        if field in bill_data and bill_data[field] is not None:
            if isinstance(bill_data[field], (list, dict)):
                bill_data[field] = json.dumps(bill_data[field])
    
    db_bill = BillSummary(**bill_data)
    db.add(db_bill)
    db.commit()
    db.refresh(db_bill)
    return db_bill

def get_bill(db: Session, bill_id: str) -> Optional[BillSummary]:
    """Get a bill by bill_id"""
    return db.query(BillSummary).filter(BillSummary.bill_id == bill_id).first()

def get_bill_by_pk(db: Session, pk_id: int) -> Optional[BillSummary]:
    """Get a bill by primary key ID"""
    return db.query(BillSummary).filter(BillSummary.id == pk_id).first()

def get_stored_bills(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None, search: Optional[str] = None) -> List[BillSummary]:
    """Get all bills with optional filtering and search"""
    query = db.query(BillSummary)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            BillSummary.title.ilike(search_term) |
            BillSummary.summary.ilike(search_term) |
            BillSummary.bill_id.ilike(search_term)
        )
    
    # Apply status filter
    if status:
        query = query.filter(BillSummary.status == status)
    
    # Order by most recent first (assuming you have a created_at or updated_at field)
    query = query.order_by(BillSummary.id.desc())
    
    return query.offset(skip).limit(limit).all()

def update_bill(db: Session, bill_id: str, bill_data: dict) -> Optional[BillSummary]:
    """Update a bill summary with comprehensive data"""
    # Convert complex data structures to JSON strings
    json_fields = ['key_provisions', 'sponsors', 'action_history', 'sources', 'tags', 'classification', 'subject', 'ai_analysis']
    for field in json_fields:
        if field in bill_data and bill_data[field] is not None:
            if isinstance(bill_data[field], (list, dict)):
                bill_data[field] = json.dumps(bill_data[field])
    
    db_bill = db.query(BillSummary).filter(BillSummary.bill_id == bill_id).first()
    if db_bill:
        for key, value in bill_data.items():
            setattr(db_bill, key, value)
        db.commit()
        db.refresh(db_bill)
    return db_bill

def clear_all_bills(db: Session) -> int:
    """Clear all bills from database and return count of deleted bills"""
    try:
        count = db.query(BillSummary).count()
        db.query(BillSummary).delete()
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        raise e

def delete_bill(db: Session, bill_id: str) -> bool:
    """Delete a bill summary by bill_id"""
    db_bill = db.query(BillSummary).filter(BillSummary.bill_id == bill_id).first()
    if db_bill:
        db.delete(db_bill)
        db.commit()
        return True
    return False

def delete_bill_by_pk(db: Session, pk_id: int) -> bool:
    """Delete a bill summary by primary key ID"""
    db_bill = db.query(BillSummary).filter(BillSummary.id == pk_id).first()
    if db_bill:
        db.delete(db_bill)
        db.commit()
        return True
    return False
