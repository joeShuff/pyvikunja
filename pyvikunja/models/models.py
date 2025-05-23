from datetime import datetime, timezone
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
                date = datetime.fromisoformat(date_str.rstrip('Z'))
                epoch_seconds = int(date.timestamp())

                utc_time = date.replace(tzinfo=timezone.utc)
                local_time = utc_time.astimezone()

                if epoch_seconds == 0:
                    return None
                else:
                    return local_time
            except ValueError as e:
                return None
        return None
