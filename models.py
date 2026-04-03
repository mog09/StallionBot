from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RaceResult:
    track: str
    race_number: int
    horse: str
    sire: str
    result: str  # "1st" = winner
    distance_m: Optional[int] = None
    race_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None  # "Colt", "Filly", "Gelding", "Mare", "Horse"
    trainer: Optional[str] = None
    sale_price: Optional[int] = None
    sale_name: Optional[str] = None
    vendor: Optional[str] = None
    buyer: Optional[str] = None
    status: Optional[str] = None  # "official", "protest", etc.
    race_class: Optional[str] = None  # "G1", "G2", "LR", "Maiden", etc.
    country: Optional[str] = None  # "AUS", "NZ", "HK"
