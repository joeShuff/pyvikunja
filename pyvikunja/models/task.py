from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List

from pyvikunja.models.enum.repeat_mode import RepeatMode
from pyvikunja.models.enum.task_priority import Priority
from pyvikunja.models.label import Label
from pyvikunja.models.models import BaseModel
from pyvikunja.models.user import User


class Task(BaseModel):
    def __init__(self, api: 'VikunjaAPI', data: Dict):
        super().__init__(data)
        self.api = api
        self.id: int = -1
        self.data = data
        self.title: str = ""
        self.description: str = ""
        self.done: bool = False
        self.done_at: Optional[datetime] = None
        self.due_date: Optional[datetime] = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.hex_color: Optional[str] = None
        self.is_favorite: bool = False
        self.percent_done: int = 0
        self.priority: Optional[Priority] = None
        self.project_id: Optional[int] = None
        self.labels: List[Label] = []
        self.assignees: List[User] = []
        self.repeat_mode: Optional[RepeatMode] = None
        self.repeat_after: Optional[timedelta] = None
        self.repeat_enabled = False

        self.parse_data(data)

    def __eq__(self, other):
        if not isinstance(other, Task):
            return False

        return (
                self.id == other.id and
                self.title == other.title and
                self.description == other.description and
                self.done == other.done and
                self.done_at == other.done_at and
                self.due_date == other.due_date and
                self.start_date == other.start_date and
                self.end_date == other.end_date and
                self.hex_color == other.hex_color and
                self.is_favorite == other.is_favorite and
                self.percent_done == other.percent_done and
                self.priority == other.priority and
                self.project_id == other.project_id and
                self.repeat_mode == other.repeat_mode and
                self.repeat_after == other.repeat_after and
                self.repeat_enabled == other.repeat_enabled and
                sorted(self.labels, key=lambda x: x.id) == sorted(other.labels, key=lambda x: x.id) and
                sorted(self.assignees, key=lambda x: x.id) == sorted(other.assignees, key=lambda x: x.id)
        )

    def parse_data(self, data):
        self.data = data
        self.id: int = data.get('id', -1)
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.done: bool = data.get('done', False)
        self.done_at: Optional[datetime] = self._parse_datetime(data.get('done_at'))
        self.due_date: Optional[datetime] = self._parse_datetime(data.get('due_date'))
        self.start_date: Optional[datetime] = self._parse_datetime(data.get('start_date'))
        self.end_date: Optional[datetime] = self._parse_datetime(data.get('end_date'))
        self.hex_color: Optional[str] = data.get('hex_color')
        self.is_favorite: bool = data.get('is_favorite', False)
        self.percent_done: int = data.get('percent_done', 0)

        priority_value = data.get('priority', 0)  # Default to 0 if missing
        self.priority: Optional[Priority] = Priority(
            priority_value) if priority_value in Priority._value2member_map_ else None

        self.project_id: Optional[int] = data.get('project_id')
        self.labels: List[Label] = [Label(label_data) for label_data in data.get('labels', []) or []]
        self.assignees: List[User] = [User(user_data) for user_data in data.get('assignees', []) or []]

        # Parse repeat_mode into an enum
        self.repeat_mode: Optional[RepeatMode] = self._parse_repeat_mode(data.get('repeat_mode'))

        # Parse repeat_after into timedelta
        self.repeat_after: Optional[timedelta] = self._parse_repeat_after(data.get('repeat_after'))
        self.repeat_enabled = self.repeat_after is not None

    def _parse_repeat_mode(self, mode: Optional[int]) -> Optional[RepeatMode]:
        """Convert repeat_mode integer into an Enum value, defaulting to NONE."""
        try:
            return RepeatMode(mode) if mode is not None else None
        except ValueError:
            return None

    def _parse_repeat_after(self, seconds: Optional[int]) -> Optional[timedelta]:
        """Convert repeat_after seconds into a timedelta."""
        try:
            return timedelta(seconds=seconds) if seconds else None
        except:
            # Error parsing seconds to timedelta. Possibly too large.
            return None

    async def update(self, data: Dict) -> 'Task':
        # Merge self.data with the new data (data overrides keys in self.data)
        combined = {**self.data, **data}

        # Send the combined data to the API
        updated_data = await self.api.update_task(self.id, combined)

        # Update the local data with the response
        self.parse_data(updated_data)

        return self

    async def mark_as_done(self) -> 'Task':
        return await self.update({'done': True})

    async def set_is_favorite(self, is_favourite: bool) -> 'Task':
        return await self.update({'is_favorite': is_favourite})

    async def set_priority(self, priority: Priority) -> 'Task':
        return await self.update({'priority': priority.value})

    async def set_progress(self, percent_done: int) -> 'Task':
        return await self.update({'percent_done': percent_done / 100})

    async def set_color(self, color: str) -> 'Task':
        return await self.update({'hex_color': color})

    async def assign_to_user(self, user_id: int) -> 'Task':
        return await self.update({'assignees': [user_id]})

    async def add_labels(self, labels: List[int]) -> 'Task':
        return await self.update({'labels': labels})

    async def move_to_project(self, project_id: int) -> 'Task':
        # Move the task to a new project
        return await self.update({'project_id': project_id})

    async def set_due_date(self, date: datetime) -> 'Task':
        # Set the task's due date in ISO format
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        iso_date = str(date.isoformat())
        return await self.update({'due_date': iso_date})

    async def set_start_date(self, date: datetime) -> 'Task':
        # Set the task's start date in ISO format
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        iso_date = str(date.isoformat())
        return await self.update({'start_date': iso_date})

    async def set_end_date(self, date: datetime) -> 'Task':
        # Set the task's end date in ISO format
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        iso_date = str(date.isoformat())
        return await self.update({'end_date': iso_date})

    async def set_repeating_enabled(self, enabled: bool):
        return await self.update({
            'repeat_after': None if not enabled else 3600,  # 1 hour min
            'repeat_mode': 0
        })

    async def set_repeating_interval(self, interval: Optional[timedelta] = None,
                                     mode: Optional[RepeatMode] = None) -> 'Task':
        new_interval = interval if interval is not None else self.repeat_after
        total_seconds = int(new_interval.total_seconds())

        new_mode = mode if mode is not None else self.repeat_mode

        return await self.update({'repeat_after': total_seconds,
                                  'repeat_mode': new_mode.value})

    async def delete_task(self) -> Dict:
        return await self.api.delete_task(self.id)
