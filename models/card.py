"""
Modèle de données pour une carte Sorare.
"""
from dataclasses import dataclass, field
from typing import Optional, List

from models.player import Player

# Multiplicateurs de rareté pour l'estimation de valeur
RARITY_MULTIPLIER = {
    "unique": 20.0,
    "super_rare": 5.0,
    "rare": 2.0,
    "limited": 1.0,
    "common": 0.1,
}

RARITY_LABELS = {
    "unique": "Unique",
    "super_rare": "Super Rare",
    "rare": "Rare",
    "limited": "Limited",
    "common": "Commune",
}

RARITY_COLORS = {
    "unique": "gold1",
    "super_rare": "red1",
    "rare": "deep_sky_blue1",
    "limited": "yellow3",
    "common": "grey50",
}


@dataclass
class PriceRange:
    min_price: Optional[float] = None   # en wei (ETH * 1e18)
    max_price: Optional[float] = None

    @classmethod
    def from_api(cls, data: Optional[dict]) -> "PriceRange":
        if not data:
            return cls()
        return cls(
            min_price=_parse_price(data.get("min")),
            max_price=_parse_price(data.get("max")),
        )

    @property
    def min_eth(self) -> Optional[float]:
        if self.min_price is None:
            return None
        return self.min_price / 1e18

    @property
    def max_eth(self) -> Optional[float]:
        if self.max_price is None:
            return None
        return self.max_price / 1e18

    @property
    def avg_eth(self) -> Optional[float]:
        if self.min_eth is None and self.max_eth is None:
            return None
        values = [v for v in [self.min_eth, self.max_eth] if v is not None]
        return sum(values) / len(values)

    def display(self) -> str:
        if self.min_eth is None and self.max_eth is None:
            return "Prix inconnu"
        parts = []
        if self.min_eth is not None:
            parts.append(f"Min: {self.min_eth:.4f} ETH")
        if self.max_eth is not None:
            parts.append(f"Max: {self.max_eth:.4f} ETH")
        return " | ".join(parts)


@dataclass
class Card:
    slug: str
    serial_number: Optional[int] = None
    rarity: str = "limited"
    season: Optional[str] = None
    player: Optional[Player] = None
    price_range: PriceRange = field(default_factory=PriceRange)
    public_min_price: Optional[float] = None
    public_max_price: Optional[float] = None
    tradeable_status: Optional[str] = None
    open_for_offers: bool = False
    best_bid_amount: Optional[float] = None    # en wei

    @classmethod
    def from_api(cls, data: dict) -> "Card":
        player_data = data.get("player") or {}
        player = Player.from_api(player_data) if player_data else None

        # Prix depuis priceRange ou les champs directs
        price_range_data = (
            (data.get("card") or {}).get("priceRange")
            or data.get("priceRange")
        )

        # Meilleure offre en cours
        latest_auction = data.get("latestAuction") or {}
        best_bid = (latest_auction.get("bestBid") or {}).get("amount")

        return cls(
            slug=data.get("slug", ""),
            serial_number=data.get("serialNumber"),
            rarity=data.get("rarity", "limited").lower(),
            season=data.get("season"),
            player=player,
            price_range=PriceRange.from_api(price_range_data),
            public_min_price=_parse_price(data.get("publicMinPrice")),
            public_max_price=_parse_price(data.get("publicMaxPrice")),
            tradeable_status=data.get("tradeableStatus"),
            open_for_offers=data.get("openForOffers", False),
            best_bid_amount=_parse_price(best_bid),
        )

    @property
    def rarity_label(self) -> str:
        return RARITY_LABELS.get(self.rarity, self.rarity.capitalize())

    @property
    def rarity_color(self) -> str:
        return RARITY_COLORS.get(self.rarity, "white")

    @property
    def estimated_value_eth(self) -> Optional[float]:
        """Valeur estimée en ETH (moyenne des prix connus)."""
        return self.price_range.avg_eth

    @property
    def best_bid_eth(self) -> Optional[float]:
        if self.best_bid_amount is None:
            return None
        return self.best_bid_amount / 1e18

    @property
    def player_name(self) -> str:
        if self.player:
            return self.player.display_name
        return "Joueur inconnu"

    @property
    def is_tradeable(self) -> bool:
        return self.tradeable_status in ("TRADEABLE", None)


def _parse_price(value) -> Optional[float]:
    """Parse un prix qui peut être str ou int (en wei)."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
