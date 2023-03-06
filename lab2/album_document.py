from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Album:
    album_name: str
    release_date: date
    musicians: list[str]
    box_office: int
    description: str
    critical_reception: str
    additional_notes: str

    _id: Optional[str] = None
    _score: Optional[float] = None