from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pathlib import Path
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from riskkit.enums import MarkType
@dataclass
class Mark:
    id: int
    type: MarkType
    title: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0  # 0-5, with 5 being highest
    tags: List[str] = field(default_factory=list)
    related_files: List[Path] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    parent_id: Optional[int] = None
    children: List[int] = field(default_factory=list)
    recurring: bool = False
    recurring_interval: Optional[str] = None  # "daily", "weekly", "monthly"

class MarkManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.marks: Dict[int, Mark] = {}
        self.next_id = 1

    def add_mark(self, 
                type: MarkType,
                title: str,
                description: str = "",
                due_date: Optional[datetime] = None,
                priority: int = 0,
                tags: List[str] = None,
                related_files: List[Path] = None,
                parent_id: Optional[int] = None,
                recurring: bool = False,
                recurring_interval: Optional[str] = None) -> Mark:
        """Create a new mark"""
        mark = Mark(
            id=self.next_id,
            type=type,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            tags=tags or [],
            related_files=related_files or [],
            parent_id=parent_id,
            recurring=recurring,
            recurring_interval=recurring_interval
        )
        
        if parent_id and parent_id in self.marks:
            self.marks[parent_id].children.append(mark.id)
            
        self.marks[mark.id] = mark
        self.next_id += 1
        return mark

    def get_marks_by_type(self, type: MarkType) -> List[Mark]:
        """Get all marks of a specific type"""
        return [m for m in self.marks.values() if m.type == type]

    def get_marks_by_priority(self, min_priority: int = 0) -> List[Mark]:
        """Get marks above specified priority"""
        return [m for m in self.marks.values() if m.priority >= min_priority]

    def get_marks_for_file(self, file_path: Path) -> List[Mark]:
        """Get all marks related to a specific file"""
        return [m for m in self.marks.values() if file_path in m.related_files]

    def complete_mark(self, mark_id: int, completed_at: Optional[datetime] = None):
        """Complete a mark and handle recurring if needed"""
        if mark_id not in self.marks:
            return
            
        mark = self.marks[mark_id]
        mark.completed_at = completed_at or datetime.now()
        
        if mark.recurring:
            self._create_next_recurring(mark)

    def _create_next_recurring(self, mark: Mark):
        """Create next instance of a recurring mark"""
        if not mark.recurring_interval:
            return
            
        # Calculate next due date
        if mark.due_date:
            if mark.recurring_interval == "daily":
                next_due = mark.due_date + timedelta(days=1)
            elif mark.recurring_interval == "weekly":
                next_due = mark.due_date + timedelta(weeks=1)
            elif mark.recurring_interval == "monthly":
                next_due = mark.due_date + relativedelta(months=1)
        else:
            next_due = None
            
        # Create new mark
        self.add_mark(
            type=mark.type,
            title=mark.title,
            description=mark.description,
            due_date=next_due,
            priority=mark.priority,
            tags=mark.tags.copy(),
            related_files=mark.related_files.copy(),
            parent_id=mark.parent_id,
            recurring=True,
            recurring_interval=mark.recurring_interval
        )