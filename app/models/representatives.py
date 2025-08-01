from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.models.database import Base

class Representative(Base):
    """Model to store representative information"""
    __tablename__ = "representatives"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    office = Column(String(200), nullable=False)
    party = Column(String(100))
    level = Column(String(50))  # federal, state, local
    address = Column(Text)  # Address this representative serves
    phone = Column(String(50))
    email = Column(String(200))
    website_url = Column(String(500))
    photo_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'office': self.office,
            'party': self.party,
            'level': self.level,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'website_url': self.website_url,
            'photo_url': self.photo_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
