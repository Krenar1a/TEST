from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.crud.base import CRUDBase
from app.models.bills import BillSummary
from app.schemas import BillSummaryCreate, BillSummaryUpdate
import json


class CRUDBillSummary(CRUDBase[BillSummary, BillSummaryCreate, BillSummaryUpdate]):
    """CRUD operations for BillSummary model"""
    
    def get_by_bill_id(self, db: Session, *, bill_id: str) -> Optional[BillSummary]:
        """Get a bill summary by bill_id"""
        return db.query(BillSummary).filter(BillSummary.bill_id == bill_id).first()
    
    def get_recent_summaries(self, db: Session, *, limit: int = 10) -> List[BillSummary]:
        """Get recent bill summaries ordered by creation date"""
        return (
            db.query(BillSummary)
            .order_by(desc(BillSummary.created_at))
            .limit(limit)
            .all()
        )
    
    def search_by_title(self, db: Session, *, search_term: str, skip: int = 0, limit: int = 100) -> List[BillSummary]:
        """Search bill summaries by title"""
        return (
            db.query(BillSummary)
            .filter(BillSummary.title.contains(search_term))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_provisions(
        self, 
        db: Session, 
        *, 
        bill_id: str,
        title: str,
        summary: str,
        key_provisions: List[str],
        impact: Optional[str] = None,
        status: Optional[str] = None
    ) -> BillSummary:
        """Create a bill summary with key provisions list"""
        bill_summary_data = BillSummaryCreate(
            bill_id=bill_id,
            title=title,
            summary=summary,
            key_provisions=json.dumps(key_provisions) if key_provisions else None,
            impact=impact,
            status=status
        )
        return self.create(db=db, obj_in=bill_summary_data)
    
    def update_summary_content(
        self,
        db: Session,
        *,
        db_obj: BillSummary,
        summary: Optional[str] = None,
        key_provisions: Optional[List[str]] = None,
        impact: Optional[str] = None,
        status: Optional[str] = None
    ) -> BillSummary:
        """Update specific fields of a bill summary"""
        update_data = {}
        if summary is not None:
            update_data["summary"] = summary
        if key_provisions is not None:
            update_data["key_provisions"] = json.dumps(key_provisions)
        if impact is not None:
            update_data["impact"] = impact
        if status is not None:
            update_data["status"] = status
            
        return self.update(db=db, db_obj=db_obj, obj_in=update_data)
    
    def get_key_provisions_as_list(self, bill_summary: BillSummary) -> List[str]:
        """Helper method to parse key_provisions JSON string to list"""
        if not bill_summary.key_provisions:
            return []
        try:
            return json.loads(bill_summary.key_provisions)
        except json.JSONDecodeError:
            return []
    
    def delete_by_bill_id(self, db: Session, *, bill_id: str) -> Optional[BillSummary]:
        """Delete a bill summary by bill_id"""
        obj = db.query(BillSummary).filter(BillSummary.bill_id == bill_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def count_by_status(self, db: Session, *, status: str) -> int:
        """Count bill summaries by status"""
        return db.query(BillSummary).filter(BillSummary.status == status).count()
    
    def get_by_status(self, db: Session, *, status: str, skip: int = 0, limit: int = 100) -> List[BillSummary]:
        """Get bill summaries by status"""
        return (
            db.query(BillSummary)
            .filter(BillSummary.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )


bill_summary_crud = CRUDBillSummary(BillSummary)
