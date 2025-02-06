from typing import Dict, Optional

from pyvikunja.models.models import BaseModel


class Label(BaseModel):
    def __init__(self, data: Dict):
        from pyvikunja.models.user import User

        super().__init__(data)
        self.title: str = data.get('title', '')
        self.description: str = data.get('description', '')
        self.hex_color: Optional[str] = data.get('hex_color')
        self.created_by: Optional[User] = User(data.get('created_by', {}))
