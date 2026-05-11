from dataclasses import dataclass, field


@dataclass
class UserInfo:
    screen_name: str
    rest_id: str = ''
    name: str = ''
    statuses_count: int = 0
    media_count: int = 0
    save_path: str = ''
    cursor: str = ''
    count: int = 0
