"""
Modèle de données pour un joueur Sorare.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class InjuryStatus:
    active: bool = False
    probability: Optional[str] = None
    expected_return_date: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def from_api(cls, data: Optional[dict]) -> "InjuryStatus":
        if not data:
            return cls()
        return cls(
            active=data.get("active", False),
            probability=data.get("probability"),
            expected_return_date=data.get("expectedReturnDate"),
            description=data.get("description"),
        )

    @property
    def label(self) -> str:
        if not self.active:
            return "Disponible"
        parts = ["Blesse"]
        if self.description:
            parts.append(self.description)
        if self.expected_return_date:
            parts.append(f"Retour: {self.expected_return_date[:10]}")
        return " | ".join(parts)


@dataclass
class Player:
    slug: str
    display_name: str
    age: Optional[int] = None
    position: Optional[str] = None
    country: Optional[str] = None
    club: Optional[str] = None
    average_score: Optional[float] = None
    last_score: Optional[float] = None
    injury: InjuryStatus = field(default_factory=InjuryStatus)

    @classmethod
    def from_api(cls, data: dict) -> "Player":
        injury_data = data.get("injuryStatus")
        last_stats = data.get("latestFinalFixtureStats") or {}

        return cls(
            slug=data.get("slug", ""),
            display_name=data.get("displayName", "Inconnu"),
            age=data.get("age"),
            position=data.get("position"),
            country=(data.get("country") or {}).get("name"),
            club=(data.get("activeClub") or {}).get("name"),
            average_score=data.get("averageScore"),
            last_score=last_stats.get("score"),
            injury=InjuryStatus.from_api(injury_data),
        )

    @property
    def is_young(self) -> bool:
        """Joueur de moins de 20 ans."""
        return self.age is not None and self.age < 20

    @property
    def is_injured(self) -> bool:
        return self.injury.active

    @property
    def score_display(self) -> str:
        if self.average_score is None:
            return "N/A"
        return f"{self.average_score:.1f}"

    @property
    def age_display(self) -> str:
        if self.age is None:
            return "N/A"
        return f"{self.age} ans"
