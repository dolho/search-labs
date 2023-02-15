from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Album:
    album_name: str
    release_date: date
    musicians: list[str]
    box_office: int

    _id: Optional[str] = None
