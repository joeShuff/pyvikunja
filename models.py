from datetime import datetime
from typing import List, Dict, Any, Optional


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


class Task(BaseModel):
    def __init__(self, api: 'VikunjaAPI', data: Dict):
        super().__init__(data)
        self.api = api
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.done: bool = data.get('done', False)
        self.due_date: Optional[datetime] = self._parse_datetime(data.get('due_date'))
        self.project_id: Optional[int] = data.get('project_id')
        self.labels: List['Label'] = [
            Label(label_data) for label_data in data.get("labels", []) or []
        ]

    async def update(self, data: Dict) -> 'Task':
        updated_data = await self.api.update_task(self.id, data)
        return Task(self.api, updated_data)

    async def delete(self) -> Dict:
        return await self.api.delete_task(self.id)


class Label(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.hex_color: Optional[str] = data.get('hex_color')


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


class User:
    def __init__(self, data: Dict):
        self.id: Optional[int] = data.get('id')
        self.username: str = data.get('username', '')
        self.email: str = data.get('email', '')
        self.name: str = data.get('name', '')
