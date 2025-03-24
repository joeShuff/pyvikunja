import logging
from functools import cached_property
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse

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
    def __init__(self, base_url: str, token: str, strict_ssl: bool = True):
        self.host = self._normalize_host(base_url)
        self.api_base_url = self._normalize_api_base_url(self.host)
        self.headers = {"Authorization": f"Bearer {token}"}
        self.strict_ssl = strict_ssl

    @cached_property
    def client(self) -> httpx.AsyncClient:
        """Lazily instantiate the HTTP client when first accessed."""
        return httpx.AsyncClient(verify=self.strict_ssl)

    @property
    def web_ui_link(self):
        return self.host

    def _normalize_host(self, url: str) -> str:
        """Ensures the host has a valid protocol and retains ports if provided."""
        if "://" not in url:
            url = f"https://{url}"  # Default to HTTPS if no scheme provided

        parsed = urlparse(url)

        # Default to HTTPS if no scheme is provided
        scheme = parsed.scheme if parsed.scheme else "https"

        # Ensure netloc is correctly used (handles ports)
        netloc = parsed.netloc if parsed.netloc else parsed.path  # Handles cases where netloc is empty

        # Rebuild the host URL
        host = urlunparse((scheme, netloc, "", "", "", ""))

        return host.rstrip("/")

    def _normalize_api_base_url(self, host: str) -> str:
        """Ensures the API base URL includes /api/v1."""
        if not host.endswith("/api/v1"):
            return f"{host}/api/v1"
        return host

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> \
    Optional[Dict[str, Any]]:
        url = f"{self.api_base_url}{endpoint}"
        try:
            response = await self.client.request(method, url, headers=self.headers, params=params, json=data)
            response.raise_for_status()

            # Return JSON data and headers
            return {
                "data": response.json(),
                "headers": response.headers
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} | {e.response.text} | URL: {url}")
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e} | URL: {url}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e} | URL: {url}")
        return None

    async def ping(self) -> bool:
        """Tests if the API key is valid by calling the /projects endpoint."""
        """Not chosen the /user endpoint here because it was always returning 401 with an API Token"""
        url = f"{self.api_base_url}/projects"

        try:
            response = await self.client.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                return True
            else:
                raise httpx.HTTPError(f"Non-200 Response from server {response.status_code}")
        except httpx.HTTPError as e:
            raise e

    async def get_paginated_data(self, endpoint: str) -> List[Dict[str, Any]]:
        all_data = []
        page = 1
        per_page = 20

        while True:
            response = await self._request("GET", endpoint, params={"page": page, "per_page": per_page})
            if not response:
                break

            all_data.extend(response["data"])
            total_pages = int(response["headers"].get("x-pagination-total-pages", 1))
            if page >= total_pages:
                break

            page += 1

        return all_data

    # Projects
    async def get_projects(self) -> List[Project]:
        data = await self.get_paginated_data("/projects")
        return [Project(self, project) for project in data]

    async def get_project(self, project_id: int) -> Optional[Project]:
        response = await self._request("GET", f"/projects/{project_id}")
        return Project(self, response['data'])

    async def create_project(self, project: Dict) -> Optional[Dict]:
        result = await self._request("PUT", "/projects", data=project)
        return result['data']

    async def update_project(self, project_id: int, project: Dict) -> Optional[Dict]:
        result = await self._request("POST", f"/projects/{project_id}", data=project)
        return result['data']

    async def delete_project(self, project_id: int) -> Optional[Dict]:
        result = await self._request("DELETE", f"/projects/{project_id}")
        return result['data']

    # Tasks
    async def get_tasks(self, project_id: int) -> List[Task]:
        response = await self.get_paginated_data(f"/projects/{project_id}/tasks")
        return [Task(self, task_data) for task_data in response or []]

    async def get_task(self, task_id: int) -> Task:
        data = await self._request("GET", f"/tasks/{task_id}")
        return Task(self, data['data'])

    async def create_task(self, project_id: int, task: Dict) -> Optional[Dict]:
        result = await self._request("PUT", f"/projects/{project_id}/tasks", data=task)
        return result['data']

    async def update_task(self, task_id: int, task: Dict) -> Optional[Dict]:
        result = await self._request("POST", f"/tasks/{task_id}", data=task)
        return result['data']

    async def delete_task(self, task_id: int) -> Optional[Dict]:
        result = await self._request("DELETE", f"/tasks/{task_id}")
        return result['data']

    # Labels
    async def get_labels(self) -> List[Label]:
        response = await self.get_paginated_data("/labels")
        return [Label(label_data) for label_data in response or []]

    async def get_label(self, label_id: int) -> Optional[Dict]:
        result = await self._request("GET", f"/labels/{label_id}")
        return result['data']

    async def create_label(self, label: Dict) -> Optional[Dict]:
        result = await self._request("PUT", "/labels", data=label)
        return result['data']

    async def update_label(self, label_id: int, label: Dict) -> Optional[Dict]:
        result = await self._request("PUT", f"/labels/{label_id}", data=label)
        return result['data']

    async def delete_label(self, label_id: int) -> Optional[Dict]:
        result = await self._request("DELETE", f"/labels/{label_id}")
        return result['data']

    # Teams
    async def get_teams(self) -> List[Team]:
        response = await self.get_paginated_data("/teams")
        return [Team(self, team_data) for team_data in response or []]

    async def get_team(self, team_id: int) -> Optional[Team]:
        response = await self._request("GET", f"/teams/{team_id}")
        return Team(self, response['data'])

    async def create_team(self, team: Dict) -> Optional[Team]:
        response = await self._request("PUT", "/teams", data=team)
        return Team(self, response['data'])

    async def update_team(self, team_id: int, team: Dict) -> Optional[Team]:
        response = await self._request("POST", f"/teams/{team_id}", data=team)
        return Team(self, response['data'])

    async def delete_team(self, team_id: int) -> Optional[Team]:
        result = await self._request("DELETE", f"/teams/{team_id}")
        return result['data']
