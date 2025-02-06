from typing import Dict

from pyvikunja.models.models import BaseModel


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
