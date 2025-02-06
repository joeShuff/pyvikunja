from datetime import datetime, timedelta
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
        self.data = data
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

    async def update(self, data: Dict) -> 'Task':
        # Merge self.data with the new data (data overrides keys in self.data)
        combined = {**self.data, **data}

        # Send the combined data to the API
        updated_data = await self.api.update_task(self.id, combined)

        # Update the local data with the response
        self.data = updated_data

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
        iso_date = date.isoformat() + "Z"
        return await self.update({'due_date': iso_date})

    async def set_start_date(self, date: datetime) -> 'Task':
        # Set the task's start date in ISO format
        iso_date = date.isoformat() + "Z"
        return await self.update({'start_date': iso_date})

    async def set_end_date(self, date: datetime) -> 'Task':
        # Set the task's end date in ISO format
        iso_date = date.isoformat() + "Z"
        return await self.update({'end_date': iso_date})

    async def set_repeating_interval(self, interval: timedelta, mode: RepeatMode = RepeatMode.DEFAULT) -> 'Task':
        # Convert the timedelta to total seconds
        total_seconds = int(interval.total_seconds())
        # Update the repeating interval for the task
        return await self.update({'repeat_after': total_seconds,
                                  'repeat_mode': mode.value})

    async def delete_task(self) -> Dict:
        return await self.api.delete_task(self.id)
