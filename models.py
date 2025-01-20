from datetime import datetime
from typing import List, Optional, Dict, Any


class BaseModel:
    def __init__(self, data: Dict):
        self.id: Optional[int] = data.get('id')
        self.created: Optional[datetime] = self._parse_datetime(data.get('created'))
        self.updated: Optional[datetime] = self._parse_datetime(data.get('updated'))

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        if date_str:
            try:
                return datetime.fromisoformat(date_str.rstrip('Z'))
            except ValueError:
                return None
        return None


class User(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.username: str = data.get('username', '')
        self.name: str = data.get('name', '')
        self.email: str = data.get('email', '')


class Label(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.hex_color: Optional[str] = data.get('hex_color')
        self.created_by: Optional[User] = User(data.get('created_by', {}))


class Attachment(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.task_id: Optional[int] = data.get('task_id')
        self.file: Dict = data.get('file', {})
        self.created_by: Optional[User] = User(data.get('created_by', {}))


class Reminder:
    def __init__(self, data: Dict):
        self.relative_period: int = data.get('relative_period', 0)
        self.relative_to: str = data.get('relative_to', 'due_date')
        self.reminder: str = data.get('reminder', '')


class Subscription(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.entity: str = data.get('entity', '')
        self.entity_id: int = data.get('entity_id', 0)
        self.user: Optional[User] = User(data.get('user', {}))


class Task(BaseModel):
    def __init__(self, api: 'VikunjaAPI', data: Dict):
        super().__init__(data)
        self.api = api
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
        self.priority: int = data.get('priority', 0)
        self.project_id: Optional[int] = data.get('project_id')
        self.labels: List[Label] = [Label(label_data) for label_data in data.get('labels', []) or []]
        self.assignees: List[User] = [User(user_data) for user_data in data.get('assignees', [])  or []]
        self.attachments: List[Attachment] = [Attachment(attachment_data) for attachment_data in data.get('attachments', []) or []]
        self.reminders: List[Reminder] = [Reminder(reminder_data) for reminder_data in data.get('reminders', []) or []]
        self.subscription: Optional[Subscription] = Subscription(data.get('subscription', {})) if data.get('subscription') else None
        self.related_tasks: Dict[str, List[Any]] = data.get('related_tasks', {})

    async def update(self, data: Dict) -> 'Task':
        updated_data = await self.api.update_task(self.id, data)
        return Task(self.api, updated_data)

    async def mark_done(self) -> 'Task':
        updated_task = await self.api.update_task(self.id, {"done": True})
        return Task(self.api, updated_task)

    async def delete(self) -> Dict:
        return await self.api.delete_task(self.id)

class Project(BaseModel):
    def __init__(self, api: 'VikunjaAPI', data: Dict):
        super().__init__(data)
        self.api = api
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.is_archived: bool = data.get('is_archived', False)
        self.hex_color: Optional[str] = data.get('hex_color')
        self.owner: 'User' = User(data.get('owner', {}))

    async def get_tasks(self, page: int = 1, per_page: int = 20) -> List['Task']:
        return await self.api.get_tasks(self.id, page, per_page)

    async def create_task(self, task: Dict) -> 'Task':
        task_data = await self.api.create_task(self.id, task)
        return Task(self.api, task_data)

    async def update(self, data: Dict) -> 'Project':
        updated_data = await self.api.update_project(self.id, data)
        return Project(self.api, updated_data)

    async def delete(self) -> Dict:
        return await self.api.delete_project(self.id)


class Team(BaseModel):
    def __init__(self, api: 'VikunjaAPI', data: Dict):
        super().__init__(data)
        self.api = api
        self.name: str = data.get('name', '')
        self.description: str = data.get('description', '')

    async def update(self, data: Dict) -> 'Team':
        updated_data = await self.api.update_team(self.id, data)
        return Team(self.api, updated_data)

    async def delete(self) -> Dict:
        return await self.api.delete_team(self.id)
