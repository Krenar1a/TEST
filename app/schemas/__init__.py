from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# BillSummary Schemas
class BillSummaryBase(BaseModel):
    """Base schema for BillSummary"""
    bill_id: str
    title: str
    summary: str
    key_provisions: Optional[str] = None
    impact: Optional[str] = None
    status: Optional[str] = None


class BillSummaryCreate(BillSummaryBase):
    """Schema for creating a new BillSummary"""
    pass


class BillSummaryUpdate(BaseModel):
    """Schema for updating a BillSummary"""
    title: Optional[str] = None
    summary: Optional[str] = None
    key_provisions: Optional[str] = None
    impact: Optional[str] = None
    status: Optional[str] = None


class BillSummaryInDBBase(BillSummaryBase):
    """Base schema for BillSummary in database"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BillSummary(BillSummaryInDBBase):
    """Schema for BillSummary response"""
    pass


class BillSummaryInDB(BillSummaryInDBBase):
    """Schema for BillSummary stored in database"""
    pass


# BillCache Schemas
class BillCacheBase(BaseModel):
    """Base schema for BillCache"""
    bill_id: str
    data: str  # JSON string


class BillCacheCreate(BillCacheBase):
    """Schema for creating a new BillCache"""
    pass


class BillCacheUpdate(BaseModel):
    """Schema for updating a BillCache"""
    data: Optional[str] = None


class BillCacheInDBBase(BillCacheBase):
    """Base schema for BillCache in database"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BillCache(BillCacheInDBBase):
    """Schema for BillCache response"""
    pass


class BillCacheInDB(BillCacheInDBBase):
    """Schema for BillCache stored in database"""
    pass
