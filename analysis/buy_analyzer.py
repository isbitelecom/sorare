"""
Analyseur d'achat: recommande des cartes à acheter selon des critères.

Critères configurables:
- Âge du joueur (< 20 ans par défaut)
- Score moyen minimum
- Prix maximum en ETH
- Joueurs blessés (prix bas = opportunité d'achat)
- Position souhaitée
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from models.card import Card
from models.player import Player
from config import MAX_AGE_BUY, MIN_SCORE_BUY, MAX_PRICE_ETH


@dataclass
class BuyCriteria:
    """Critères personnalisables pour les recommandations d'achat."""
    max_age: int = MAX_AGE_BUY
    min_score: float = MIN_SCORE_BUY
    max_price_eth: float = MAX_PRICE_ETH
    positions: List[str] = field(default_factory=list)  # ex: ["Goalkeeper", "Midfielder"]
    include_injured: bool = True    # Inclure les blessés (opportunité prix bas)
    rarities: List[str] = field(
        default_factory=lambda: ["limited", "rare"]
    )


@dataclass
class BuyOpportunity:
    """Opportunité d'achat pour une carte."""
    player: Player
    card_slug: Optional[str]
    rarity: str
    estimated_price_eth: Optional[float]
    score: int              # Score d'opportunité 0-100
    reasons: List[str]
    risks: List[str]
    criteria_matched: List[str]

    @property
    def score_color(self) -> str:
        if self.score >= 75:
            return "bold green"
        if self.score >= 50:
            return "yellow"
        return "red"

    @property
    def price_display(self) -> str:
        if self.estimated_price_eth is None:
            return "Prix inconnu"
        return f"{self.estimated_price_eth:.4f} ETH"


def analyze_buy_opportunity(
    player: Player,
    card_slug: Optional[str],
    rarity: str,
    price_eth: Optional[float],
    criteria: BuyCriteria,
) -> Optional[BuyOpportunity]:
    """
    Analyse si un joueur/carte représente une bonne opportunité d'achat.
    Retourne None si la carte ne correspond pas aux critères.
    """
    reasons = []
    risks = []
    criteria_matched = []
    opportunity_score = 0

    # --- Critère 1: Prix ---
    if price_eth is not None:
        if price_eth > criteria.max_price_eth:
            return None  # Trop cher, on passe
        price_ratio = price_eth / criteria.max_price_eth
        if price_ratio < 0.3:
            opportunity_score += 25
            criteria_matched.append(f"Prix tres bas: {price_eth:.4f} ETH")
        elif price_ratio < 0.6:
            opportunity_score += 15
            criteria_matched.append(f"Prix accessible: {price_eth:.4f} ETH")
        else:
            opportunity_score += 5
            criteria_matched.append(f"Prix limite: {price_eth:.4f} ETH")

    # --- Critère 2: Âge ---
    if player.age is not None:
        if player.age > criteria.max_age:
            return None  # Trop vieux pour les critères
        criteria_matched.append(f"Jeune joueur: {player.age} ans")
        age_bonus = max(0, (criteria.max_age - player.age) * 3)
        opportunity_score += min(age_bonus, 30)
        if player.age <= 17:
            reasons.append(
                f"Prodige de {player.age} ans - potentiel de valorisation exceptionnel"
            )
        elif player.age <= 19:
            reasons.append(
                f"Jeune talent de {player.age} ans - forte marge de progression"
            )
        else:
            reasons.append(f"Joueur de {player.age} ans - encore en developpement")

    # --- Critère 3: Score moyen ---
    if player.average_score is not None:
        if player.average_score < criteria.min_score:
            # Score insuffisant mais si blessé, on tolère
            if not player.is_injured:
                return None
            else:
                risks.append(
                    f"Score faible ({player.average_score:.1f}) mais blessure = prix reduit"
                )
        else:
            score_bonus = min(int((player.average_score - criteria.min_score) * 0.5), 25)
            opportunity_score += score_bonus
            criteria_matched.append(f"Score: {player.average_score:.1f}/100")
            if player.average_score >= 70:
                reasons.append("Excellent niveau de jeu confirme")
            elif player.average_score >= 60:
                reasons.append("Bon niveau de jeu")

    # --- Critère 4: Blessure (opportunité prix bas) ---
    if player.is_injured:
        if not criteria.include_injured:
            return None
        opportunity_score += 15
        criteria_matched.append("Joueur blesse = prix reduit")
        reasons.append(
            f"Blessure temporaire cree une opportunite: {player.injury.label}"
        )
        if player.injury.expected_return_date:
            reasons.append(
                f"Retour prevu le {player.injury.expected_return_date[:10]} "
                "= achat avant remontee du prix"
            )
            risks.append("Incertitude sur le delai de retour reelle")
        else:
            risks.append("Duree de la blessure inconnue - risque eleve")
            opportunity_score -= 10

    # --- Critère 5: Position ---
    if criteria.positions and player.position:
        pos_normalized = player.position.upper()
        if not any(p.upper() in pos_normalized for p in criteria.positions):
            return None  # Position non souhaitée
        criteria_matched.append(f"Position: {player.position}")

    # --- Score final ---
    opportunity_score = min(100, max(0, opportunity_score))

    if opportunity_score < 20:
        return None  # Opportunité trop faible

    if not reasons:
        reasons.append("Correspond aux criteres de recherche")

    return BuyOpportunity(
        player=player,
        card_slug=card_slug,
        rarity=rarity,
        estimated_price_eth=price_eth,
        score=opportunity_score,
        reasons=reasons,
        risks=risks,
        criteria_matched=criteria_matched,
    )


def find_buy_opportunities(
    players_data: List[Dict[str, Any]],
    criteria: Optional[BuyCriteria] = None,
) -> List[BuyOpportunity]:
    """
    Analyse une liste de joueurs/cartes et retourne les meilleures opportunités.
    Les données doivent avoir la structure retournée par l'API Sorare.
    """
    if criteria is None:
        criteria = BuyCriteria()

    opportunities = []

    for player_data in players_data:
        player = Player.from_api(player_data)

        # Analyser les cartes disponibles pour ce joueur
        cards_data = player_data.get("cards", {}).get("nodes", [])

        if not cards_data:
            # Pas de carte disponible, on crée quand même une analyse sans carte
            opp = analyze_buy_opportunity(
                player=player,
                card_slug=None,
                rarity="limited",
                price_eth=None,
                criteria=criteria,
            )
            if opp:
                opportunities.append(opp)
            continue

        for card_data in cards_data:
            rarity = card_data.get("rarity", "limited").lower()
            if rarity not in criteria.rarities:
                continue

            price_range = card_data.get("priceRange") or {}
            min_price = price_range.get("min")
            price_eth = float(min_price) / 1e18 if min_price else None

            opp = analyze_buy_opportunity(
                player=player,
                card_slug=card_data.get("slug"),
                rarity=rarity,
                price_eth=price_eth,
                criteria=criteria,
            )
            if opp:
                opportunities.append(opp)

    # Classer par score décroissant
    opportunities.sort(key=lambda o: -o.score)
    return opportunities
