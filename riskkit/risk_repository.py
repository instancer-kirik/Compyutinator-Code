from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from NITTY_GRITTY.database import Base, DatabaseManager
from .schemas import RiskCreate, RiskUpdate
from .risk import Risk
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Define Project model if it doesn't exist
class Project(Base):
    __tablename__ = 'projects'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    name = Column(String)
    risks = relationship("RiskRecord", back_populates="project", cascade="all, delete-orphan")
    # Add other necessary fields

class RiskRecord(Base):
    """SQLAlchemy model for risk storage"""
    __tablename__ = 'risks'
    __table_args__ = {'extend_existing': True}  # Allow table redefinition

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    project = relationship("Project", back_populates="risks")
    description = Column(String)
    probability = Column(String)
    impact = Column(String)
    priority = Column(String)
    status = Column(String)
    mitigation = Column(String, nullable=True)
    reward_type = Column(String, nullable=True)
    estimated_value = Column(Float, nullable=True)
    reward_probability = Column(String, nullable=True)
    date_created = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner = Column(String, nullable=True)
    category_id = Column(Integer, nullable=True)

class RiskIndexingThread(QThread):
    indexing_complete = pyqtSignal(list)

    def __init__(self, repository, project_id=None):
        super().__init__()
        self.repository = repository
        self.project_id = project_id

    def run(self):
        try:
            risks = self.repository.get_by_project(self.project_id)
            self.indexing_complete.emit(risks)
        except Exception as e:
            logging.error(f"Error during risk indexing: {e}")
            self.indexing_complete.emit([])

class RiskRepository(QObject):
    """Handles database operations for risks"""
    risks_updated = pyqtSignal(list)
    risk_created = pyqtSignal(int)  # Emits risk ID
    risk_deleted = pyqtSignal(int)  # Emits risk ID
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self._indexing_thread = None
        
        try:
            Base.metadata.create_all(db_manager.engine, tables=[RiskRecord.__table__])
        except Exception as e:
            logging.error(f"Error initializing risk repository: {e}")

    def load_risks_async(self, project_id: Optional[int] = None):
        """Asynchronously load risks for a project"""
        if self._indexing_thread and self._indexing_thread.isRunning():
            logging.warning("Risk indexing already in progress")
            return
            
        self._indexing_thread = RiskIndexingThread(self, project_id)
        self._indexing_thread.indexing_complete.connect(self._on_indexing_complete)
        self._indexing_thread.start()

    def _on_indexing_complete(self, risks: List[Risk]):
        """Handle completed risk indexing"""
        self.risks_updated.emit(risks)

    def create(self, risk: Risk) -> Optional[int]:
        """Store a new risk"""
        try:
            db = next(self.db_manager.get_db())
            record = RiskRecord(
                project_id=risk.project_id,
                description=risk.description,
                probability=risk.probability.value,
                impact=risk.impact.value,
                priority=risk.priority,
                status=risk.status.value,
                mitigation=risk.mitigation,
                reward_type=risk.reward_type.value if risk.reward_type else None,
                estimated_value=risk.estimated_value,
                reward_probability=risk.reward_probability.value if risk.reward_probability else None,
                owner=risk.owner
            )
            db.add(record)
            db.commit()
            self.risk_created.emit(record.id)
            return record.id
        except Exception as e:
            logging.error(f"Error creating risk record: {e}")
            return None

    def get_by_project(self, project_id: int) -> List[Risk]:
        """Get all risks for a project"""
        try:
            db = next(self.db_manager.get_db())
            records = db.query(RiskRecord).filter_by(project_id=project_id).all()
            return [self._record_to_risk(r) for r in records]
        except Exception as e:
            logging.error(f"Error fetching project risks: {e}")
            return []

    def _record_to_risk(self, record: RiskRecord) -> Risk:
        """Convert database record to Risk object"""
        return Risk.from_dict({
            "id": record.id,
            "description": record.description,
            "probability": record.probability,
            "impact": record.impact,
            "priority": record.priority,
            "status": record.status,
            "mitigation": record.mitigation,
            "reward_type": record.reward_type,
            "estimated_value": record.estimated_value,
            "reward_probability": record.reward_probability,
            "date_created": record.date_created.strftime("%Y-%m-%d"),
            "last_updated": record.last_updated.strftime("%Y-%m-%d"),
            "owner": record.owner,
            "category_id": record.category_id,
            "project_id": record.project_id
        })

    def get_by_id(self, risk_id: int) -> Optional[Risk]:
        """Get a risk by its ID"""
        try:
            db = next(self.db_manager.get_db())
            record = db.query(RiskRecord).filter_by(id=risk_id).first()
            if record:
                return self._record_to_risk(record)
            return None
        except Exception as e:
            logging.error(f"Error fetching risk by ID: {e}")
            return None