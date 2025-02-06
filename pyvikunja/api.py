import logging
from typing import List, Dict, Any, Optional

import httpx

from pyvikunja.models.label import Label
from pyvikunja.models.project import Project
from pyvikunja.models.task import Task
from pyvikunja.models.team import Team

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API-related errors."""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class VikunjaAPI:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient()

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Optional[Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = await self.client.request(method, url, headers=self.headers, params=params, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} | {e.response.text} | URL: {url}")
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e} | URL: {url}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e} | URL: {url}")
        return None

    # Projects
    async def get_projects(self, page: int = 1, per_page: int = 20) -> List[Project]:
        response = await self._request("GET", "/projects", params={"page": page, "per_page": per_page})
        return [Project(self, project_data) for project_data in response or []]

    async def get_project(self, project_id: int) -> Optional[Project]:
        response = await self._request("GET", f"/projects/{project_id}")
        return Project(self, response)

    async def create_project(self, project: Dict) -> Optional[Dict]:
        return await self._request("PUT", "/projects", data=project)

    async def update_project(self, project_id: int, project: Dict) -> Optional[Dict]:
        return await self._request("POST", f"/projects/{project_id}", data=project)

    async def delete_project(self, project_id: int) -> Optional[Dict]:
        return await self._request("DELETE", f"/projects/{project_id}")

    # Tasks
    async def get_tasks(self, project_id: int, page: int = 1, per_page: int = 20) -> List[Task]:
        response = await self._request("GET", f"/projects/{project_id}/tasks",
                                       params={"page": page, "per_page": per_page})
        return [Task(self, task_data) for task_data in response or []]

    async def get_task(self, task_id: int) -> Task:
        data = await self._request("GET", f"/tasks/{task_id}")
        return Task(self, data)

    async def create_task(self, project_id: int, task: Dict) -> Optional[Dict]:
        return await self._request("PUT", f"/projects/{project_id}/tasks", data=task)

    async def update_task(self, task_id: int, task: Dict) -> Optional[Dict]:
        return await self._request("POST", f"/tasks/{task_id}", data=task)

    async def delete_task(self, task_id: int) -> Optional[Dict]:
        return await self._request("DELETE", f"/tasks/{task_id}")

    # Labels
    async def get_labels(self, page: int = 1, per_page: int = 20) -> List[Label]:
        response = await self._request("GET", "/labels", params={"page": page, "per_page": per_page})
        return [Label(label_data) for label_data in response or []]

    async def get_label(self, label_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/labels/{label_id}")

    async def create_label(self, label: Dict) -> Optional[Dict]:
        return await self._request("PUT", "/labels", data=label)

    async def update_label(self, label_id: int, label: Dict) -> Optional[Dict]:
        return await self._request("PUT", f"/labels/{label_id}", data=label)

    async def delete_label(self, label_id: int) -> Optional[Dict]:
        return await self._request("DELETE", f"/labels/{label_id}")

    # Teams
    async def get_teams(self, page: int = 1, per_page: int = 20) -> List[Team]:
        response = await self._request("GET", "/teams", params={"page": page, "per_page": per_page})
        return [Team(self, team_data) for team_data in response or []]

    async def get_team(self, team_id: int) -> Optional[Team]:
        response = await self._request("GET", f"/teams/{team_id}")
        return Team(self, response)

    async def create_team(self, team: Dict) -> Optional[Team]:
        response = await self._request("PUT", "/teams", data=team)
        return Team(self, response)

    async def update_team(self, team_id: int, team: Dict) -> Optional[Team]:
        response = await self._request("POST", f"/teams/{team_id}", data=team)
        return Team(self, response)

    async def delete_team(self, team_id: int) -> Optional[Team]:
        return await self._request("DELETE", f"/teams/{team_id}")


