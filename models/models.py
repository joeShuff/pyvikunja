from datetime import datetime
from typing import Optional, Dict


class BaseModel:
    def __init__(self, data: Dict):
        self.id: Optional[int] = data.get('id') or None
        self.created: Optional[datetime] = self._parse_datetime(data.get('created')) or None
        self.updated: Optional[datetime] = self._parse_datetime(data.get('updated')) or None

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        if date_str:
            try:
                return datetime.fromisoformat(date_str.rstrip('Z'))
            except ValueError:
                return None
        return None
