"""
Analyseur de vente: détermine si c'est le bon moment de vendre une carte.

Critères d'analyse:
- Valeur de marché vs prix d'achat estimé
- Score moyen du joueur (performances récentes)
- Statut de blessure (blessure = vendre avant chute du prix)
- Rareté de la carte
- Statut de négociabilité
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from models.card import Card
from config import MIN_PROFIT_PERCENT, MIN_SCORE_KEEP


class SellRecommendation(Enum):
    SELL_NOW = "VENDRE MAINTENANT"
    SELL_SOON = "VENDRE BIENTOT"
    KEEP = "GARDER"
    WATCH = "SURVEILLER"


@dataclass
class SellAnalysis:
    card: Card
    recommendation: SellRecommendation
    score: int           # Score de conviction 0-100
    reasons: List[str]
    warnings: List[str]

    @property
    def recommendation_color(self) -> str:
        colors = {
            SellRecommendation.SELL_NOW: "bold red",
            SellRecommendation.SELL_SOON: "bold yellow",
            SellRecommendation.KEEP: "bold green",
            SellRecommendation.WATCH: "bold cyan",
        }
        return colors[self.recommendation]

    @property
    def recommendation_icon(self) -> str:
        icons = {
            SellRecommendation.SELL_NOW: "[red]VENDRE[/red]",
            SellRecommendation.SELL_SOON: "[yellow]BIENTOT[/yellow]",
            SellRecommendation.KEEP: "[green]GARDER[/green]",
            SellRecommendation.WATCH: "[cyan]SURVEILLER[/cyan]",
        }
        return icons[self.recommendation]


def analyze_sell(card: Card) -> SellAnalysis:
    """
    Analyse une carte et détermine s'il faut la vendre.
    Retourne une analyse détaillée avec recommandation.
    """
    reasons = []
    warnings = []
    sell_signals = 0
    keep_signals = 0

    player = card.player

    # --- Signal 1: Blessure du joueur ---
    if player and player.is_injured:
        sell_signals += 3
        injury = player.injury
        reasons.append(f"Joueur blesse: {injury.label}")
        if injury.expected_return_date:
            warnings.append(
                f"Retour prevu le {injury.expected_return_date[:10]} - "
                "le prix risque de chuter"
            )
        else:
            warnings.append("Blessure indefinie - risque de perte de valeur importante")

    # --- Signal 2: Score moyen faible ---
    if player and player.average_score is not None:
        if player.average_score < MIN_SCORE_KEEP:
            sell_signals += 2
            reasons.append(
                f"Score moyen faible: {player.average_score:.1f}/100 "
                f"(seuil: {MIN_SCORE_KEEP})"
            )
        elif player.average_score >= 70:
            keep_signals += 2
            reasons.append(f"Excellent score moyen: {player.average_score:.1f}/100")
        elif player.average_score >= 55:
            keep_signals += 1
            reasons.append(f"Bon score moyen: {player.average_score:.1f}/100")

    # --- Signal 3: Valeur de marché disponible ---
    value = card.estimated_value_eth
    if value is not None:
        if value > 0.05:
            sell_signals += 1
            reasons.append(
                f"Valeur de marche interessante: {value:.4f} ETH"
            )
        elif value < 0.005:
            keep_signals += 1
            reasons.append(
                f"Valeur faible ({value:.4f} ETH) - peu d'interet a vendre"
            )

    # --- Signal 4: Offre en cours ---
    if card.best_bid_eth is not None and card.best_bid_eth > 0:
        sell_signals += 1
        reasons.append(
            f"Offre en cours: {card.best_bid_eth:.4f} ETH - occasion de vendre"
        )

    # --- Signal 5: Rareté ---
    if card.rarity == "limited":
        # Les limited sont plus liquides, plus faciles a vendre/racheter
        sell_signals += 1
        reasons.append("Carte Limited: facile a revendre si besoin")
    elif card.rarity in ("unique", "super_rare"):
        keep_signals += 2
        reasons.append(
            f"Carte {card.rarity_label}: valeur rare, "
            "gardez sauf urgence"
        )

    # --- Signal 6: Statut de négociabilité ---
    if not card.is_tradeable:
        warnings.append(
            "Carte non négociable actuellement "
            f"(statut: {card.tradeable_status})"
        )

    # --- Décision finale ---
    total = sell_signals + keep_signals
    if total == 0:
        conviction = 50
    else:
        conviction = int((sell_signals / total) * 100)

    # Règle absolue: joueur blessé avec blessure grave => vendre maintenant
    if player and player.is_injured and player.injury.expected_return_date is None:
        recommendation = SellRecommendation.SELL_NOW
        conviction = max(conviction, 80)
    elif sell_signals >= 4:
        recommendation = SellRecommendation.SELL_NOW
    elif sell_signals >= 2 and sell_signals > keep_signals:
        recommendation = SellRecommendation.SELL_SOON
    elif keep_signals >= 3:
        recommendation = SellRecommendation.KEEP
    else:
        recommendation = SellRecommendation.WATCH

    if not reasons:
        reasons.append("Pas assez de donnees pour une analyse complete")

    return SellAnalysis(
        card=card,
        recommendation=recommendation,
        score=conviction,
        reasons=reasons,
        warnings=warnings,
    )


def rank_cards_to_sell(cards: List[Card]) -> List[SellAnalysis]:
    """
    Analyse toutes les cartes et les classe par priorité de vente.
    Les cartes SELL_NOW en premier, puis SELL_SOON, etc.
    """
    analyses = [analyze_sell(card) for card in cards]

    priority_order = {
        SellRecommendation.SELL_NOW: 0,
        SellRecommendation.SELL_SOON: 1,
        SellRecommendation.WATCH: 2,
        SellRecommendation.KEEP: 3,
    }

    analyses.sort(
        key=lambda a: (priority_order[a.recommendation], -a.score)
    )
    return analyses
