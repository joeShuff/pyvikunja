from typing import Dict, Optional, List

from pyvikunja.models.models import BaseModel
from pyvikunja.models.project_view import ProjectView


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
        # There are zero to many kanban views for a project 
        self.views: List[ProjectView] = [
            ProjectView(view_data) for view_data in data.get('views', []) or []
        ]

    def get_default_kanban_view(self) -> Optional[ProjectView]:
        # Return the first kanban view for this project, ordered by position 
        kanban_views = [view for view in self.views if view.view_kind == 'kanban']
        if not kanban_views:
            return None

        return min(kanban_views, key=lambda view: view.position)

    async def get_tasks(self) -> List['Task']:
        return await self.api.get_tasks(self.id)

    async def create_task(self, task: Dict) -> 'Task':
        from pyvikunja.models.task import Task
        task_data = await self.api.create_task(self.id, task)
        return Task(self.api, task_data)

    async def update(self, data: Dict) -> 'Project':
        updated_data = await self.api.update_project(self.id, data)
        return Project(self.api, updated_data)

    async def delete(self) -> Dict:
        return await self.api.delete_project(self.id)
