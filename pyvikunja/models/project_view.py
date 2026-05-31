from typing import Dict, Optional

from pyvikunja.models.models import BaseModel


class ProjectView(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.title: str = data.get('title', '')
        self.project_id: Optional[int] = data.get('project_id')
        self.view_kind: str = data.get('view_kind', 'list')
        self.position: float = data.get('position', 0.0)
        self.default_bucket_id: Optional[int] = data.get('default_bucket_id')
        self.done_bucket_id: Optional[int] = data.get('done_bucket_id')
        self.bucket_configuration_mode: str = data.get('bucket_configuration_mode', 'manual')
