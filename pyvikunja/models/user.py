from typing import Dict

from pyvikunja.models.models import BaseModel


class User(BaseModel):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.username: str = data.get('username', '')
        self.name: str = data.get('name', '')
        self.email: str = data.get('email', '')