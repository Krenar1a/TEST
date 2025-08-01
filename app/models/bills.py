from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.models.database import Base
from datetime import datetime

class BillSummary(Base):
    """Model to store comprehensive bill data with AI analysis"""
    __tablename__ = "bill_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(String(100), unique=True, nullable=False, index=True)
    identifier = Column(String(50), nullable=True, index=True)  # e.g., "AB 100"
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String(500), nullable=True)
    
    # Basic bill information
    classification = Column(Text, nullable=True)  # JSON: ["bill", "appropriation"]
    subject = Column(Text, nullable=True)  # JSON: ["education", "budget"]
    session = Column(String(50), nullable=True)  # e.g., "20252026"
    jurisdiction = Column(String(100), nullable=True)  # e.g., "California"
    chamber = Column(String(50), nullable=True)  # "Assembly" or "Senate"
    
    # Sponsorship and authorship
    sponsors = Column(Text, nullable=True)  # JSON array of sponsor objects
    
    # Action history and dates
    action_history = Column(Text, nullable=True)  # JSON array of actions
    first_action_date = Column(String(20), nullable=True)
    latest_action_date = Column(String(20), nullable=True)
    latest_action_description = Column(Text, nullable=True)
    latest_passage_date = Column(String(20), nullable=True)
    
    # External data
    sources = Column(Text, nullable=True)  # JSON array of source URLs
    openstates_url = Column(String(500), nullable=True)
    
    # Additional metadata
    tags = Column(Text, nullable=True)  # JSON array of tags
    impact_clause = Column(Text, nullable=True)
    
    # AI-generated content
    key_provisions = Column(Text, nullable=True)  # JSON array of bullet points
    impact = Column(Text, nullable=True)
    ai_analysis = Column(Text, nullable=True)  # JSON object with full AI analysis
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary with JSON parsing for complex fields"""
        import json
        
        def safe_json_loads(value):
            if value is None:
                return None
            try:
                return json.loads(value) if isinstance(value, str) else value
            except:
                return value
        
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'identifier': self.identifier,
            'title': self.title,
            'summary': self.summary,
            'status': self.status,
            'classification': safe_json_loads(self.classification),
            'subject': safe_json_loads(self.subject),
            'session': self.session,
            'jurisdiction': self.jurisdiction,
            'chamber': self.chamber,
            'sponsors': safe_json_loads(self.sponsors),
            'action_history': safe_json_loads(self.action_history),
            'first_action_date': self.first_action_date,
            'latest_action_date': self.latest_action_date,
            'latest_action_description': self.latest_action_description,
            'latest_passage_date': self.latest_passage_date,
            'sources': safe_json_loads(self.sources),
            'openstates_url': self.openstates_url,
            'tags': safe_json_loads(self.tags),
            'impact_clause': self.impact_clause,
            'key_provisions': safe_json_loads(self.key_provisions),
            'impact': self.impact,
            'ai_analysis': safe_json_loads(self.ai_analysis),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BillCache(Base):
    """Model to cache bill data from OpenStates API"""
    __tablename__ = "bill_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(String(100), unique=True, nullable=False, index=True)
    data = Column(Text, nullable=False)  # JSON string of bill data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
