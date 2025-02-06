from typing import Dict, Optional, List

from pyvikunja.models.models import BaseModel


class Project(BaseModel):
    def __init__(self, api: 'VikunjaAPI', data: Dict):
        from pyvikunja.models.user import User

        super().__init__(data)
        self.api = api
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.is_archived: bool = data.get('is_archived', False)
        self.hex_color: Optional[str] = data.get('hex_color')
        self.owner: 'User' = User(data.get('owner') or {})

    async def get_tasks(self, page: int = 1, per_page: int = 20) -> List['Task']:
        return await self.api.get_tasks(self.id, page, per_page)

    async def create_task(self, task: Dict) -> 'Task':
        from pyvikunja.models.task import Task
        task_data = await self.api.create_task(self.id, task)
        return Task(self.api, task_data)

    async def update(self, data: Dict) -> 'Project':
        updated_data = await self.api.update_project(self.id, data)
        return Project(self.api, updated_data)

    async def delete(self) -> Dict:
        return await self.api.delete_project(self.id)
