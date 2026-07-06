from typing import Dict, Optional

from pyvikunja.models.models import BaseModel


class Bucket(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.title: str = data.get('title', '')
        self.project_view_id: Optional[int] = data.get('project_view_id')
        self.limit: int = data.get('limit', 0)
        self.position: float = data.get('position', 0.0)
        self.count: Optional[int] = data.get('count')
