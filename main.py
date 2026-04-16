#!/usr/bin/env python3
"""
Sorare Card Analyzer - Analyseur de cartes Sorare
Voir vos cartes, décider quand vendre, quoi acheter.

Usage:
    python main.py mes-cartes
    python main.py vendre
    python main.py acheter
    python main.py acheter --age-max 18 --score-min 60 --prix-max 0.05
    python main.py acheter --blesses --positions GK MF
"""
import asyncio
import sys
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

from api.client import SorareClient
from api.queries import (
    MY_CARDS_QUERY,
    SEARCH_PLAYERS_QUERY,
)
from models.card import Card
from models.player import Player
from analysis.sell_analyzer import analyze_sell, rank_cards_to_sell, SellRecommendation
from analysis.buy_analyzer import (
    BuyCriteria,
    find_buy_opportunities,
)
from config import SORARE_EMAIL, SORARE_PASSWORD, MAX_AGE_BUY, MIN_SCORE_BUY, MAX_PRICE_ETH

console = Console()


# ────────────────────────────────────────────────────────────────────────────
# Helpers d'affichage
# ────────────────────────────────────────────────────────────────────────────

def _header():
    console.print(
        Panel.fit(
            "[bold cyan]Sorare Card Analyzer[/bold cyan]\n"
            "[dim]Analyse vos cartes et trouve les meilleures opportunités[/dim]",
            border_style="cyan",
        )
    )
    console.print()


def _check_credentials():
    if not SORARE_EMAIL or not SORARE_PASSWORD:
        console.print(
            "[red]Erreur:[/red] Identifiants manquants.\n"
            "Créez un fichier [bold].env[/bold] à partir de [bold].env.example[/bold] "
            "et renseignez SORARE_EMAIL et SORARE_PASSWORD."
        )
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────
# Commandes CLI
# ────────────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Sorare Card Analyzer - Analyseur intelligent de cartes Sorare."""
    pass


@cli.command("mes-cartes")
def my_cards_cmd():
    """Affiche toutes vos cartes Sorare avec leur valeur de marché."""
    _header()
    _check_credentials()
    asyncio.run(_my_cards())


@cli.command("vendre")
def sell_cmd():
    """Analyse vos cartes et recommande lesquelles vendre."""
    _header()
    _check_credentials()
    asyncio.run(_sell_analysis())


@cli.command("acheter")
@click.option("--age-max", default=MAX_AGE_BUY, show_default=True,
              help="Âge maximum du joueur")
@click.option("--score-min", default=MIN_SCORE_BUY, show_default=True,
              help="Score moyen minimum du joueur (sur 100)")
@click.option("--prix-max", default=MAX_PRICE_ETH, show_default=True,
              help="Prix maximum en ETH")
@click.option("--blesses/--pas-blesses", default=True, show_default=True,
              help="Inclure les joueurs blessés (opportunités prix bas)")
@click.option("--positions", "-p", multiple=True,
              help="Positions souhaitées (ex: Goalkeeper, Midfielder, Defender, Forward)")
@click.option("--rarete", "-r", multiple=True,
              default=["limited", "rare"],
              help="Raretés souhaitées (limited, rare, super_rare, unique)")
def buy_cmd(age_max, score_min, prix_max, blesses, positions, rarete):
    """Trouve les meilleures cartes à acheter selon vos critères."""
    _header()
    _check_credentials()

    criteria = BuyCriteria(
        max_age=age_max,
        min_score=score_min,
        max_price_eth=prix_max,
        include_injured=blesses,
        positions=list(positions),
        rarities=list(rarete) if rarete else ["limited", "rare"],
    )

    console.print("[bold]Critères de recherche:[/bold]")
    console.print(f"  • Âge max: [cyan]{age_max} ans[/cyan]")
    console.print(f"  • Score min: [cyan]{score_min}/100[/cyan]")
    console.print(f"  • Prix max: [cyan]{prix_max} ETH[/cyan]")
    console.print(f"  • Blessés inclus: [cyan]{'Oui' if blesses else 'Non'}[/cyan]")
    if positions:
        console.print(f"  • Positions: [cyan]{', '.join(positions)}[/cyan]")
    console.print()

    asyncio.run(_buy_analysis(criteria))


# ────────────────────────────────────────────────────────────────────────────
# Logique asynchrone
# ────────────────────────────────────────────────────────────────────────────

async def _my_cards():
    """Récupère et affiche les cartes de l'utilisateur."""
    with console.status("[cyan]Connexion à Sorare...[/cyan]"):
        client = SorareClient()
        await client._connect()

    try:
        with console.status("[cyan]Récupération de vos cartes...[/cyan]"):
            all_cards_data = await client.paginate(
                MY_CARDS_QUERY,
                path="currentUser.cards",
            )

        if not all_cards_data:
            console.print("[yellow]Aucune carte trouvée dans votre collection.[/yellow]")
            return

        cards = [Card.from_api(d) for d in all_cards_data]
        _display_my_cards(cards)

    finally:
        await client._close()


async def _sell_analysis():
    """Analyse les cartes et donne des recommandations de vente."""
    with console.status("[cyan]Connexion à Sorare...[/cyan]"):
        client = SorareClient()
        await client._connect()

    try:
        with console.status("[cyan]Récupération de vos cartes...[/cyan]"):
            all_cards_data = await client.paginate(
                MY_CARDS_QUERY,
                path="currentUser.cards",
            )

        if not all_cards_data:
            console.print("[yellow]Aucune carte trouvée.[/yellow]")
            return

        cards = [Card.from_api(d) for d in all_cards_data]

        with console.status("[cyan]Analyse des cartes en cours...[/cyan]"):
            analyses = rank_cards_to_sell(cards)

        _display_sell_analysis(analyses)

    finally:
        await client._close()


async def _buy_analysis(criteria: BuyCriteria):
    """Recherche les meilleures opportunités d'achat."""
    with console.status("[cyan]Connexion à Sorare...[/cyan]"):
        client = SorareClient()
        await client._connect()

    try:
        variables = {"maxAge": criteria.max_age}
        if criteria.positions:
            variables["positions"] = [p.upper() for p in criteria.positions]

        with console.status(
            f"[cyan]Recherche de joueurs (age <= {criteria.max_age} ans)...[/cyan]"
        ):
            players_data = await client.paginate(
                SEARCH_PLAYERS_QUERY,
                path="players",
                variables=variables,
            )

        if not players_data:
            console.print("[yellow]Aucun joueur trouvé pour ces critères.[/yellow]")
            return

        with console.status("[cyan]Analyse des opportunités...[/cyan]"):
            opportunities = find_buy_opportunities(players_data, criteria)

        _display_buy_opportunities(opportunities, criteria)

    finally:
        await client._close()


# ────────────────────────────────────────────────────────────────────────────
# Affichage
# ────────────────────────────────────────────────────────────────────────────

def _display_my_cards(cards: List[Card]):
    """Affiche la collection de l'utilisateur dans un tableau."""
    console.print(
        f"[bold green]Collection:[/bold green] [cyan]{len(cards)}[/cyan] carte(s) trouvée(s)\n"
    )

    table = Table(
        title="Mes cartes Sorare",
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
    )
    table.add_column("Joueur", style="bold white", min_width=20)
    table.add_column("Age", justify="center", width=6)
    table.add_column("Club", width=18)
    table.add_column("Rarété", justify="center", width=12)
    table.add_column("Saison", justify="center", width=8)
    table.add_column("Score moy.", justify="center", width=10)
    table.add_column("Prix min ETH", justify="right", width=12)
    table.add_column("Prix max ETH", justify="right", width=12)
    table.add_column("Statut", justify="center", width=12)

    for card in cards:
        player = card.player
        age_str = str(player.age) if player and player.age else "-"
        club_str = (player.club or "-")[:18] if player else "-"
        score_str = player.score_display if player else "-"

        # Couleur du score
        if player and player.average_score is not None:
            if player.average_score >= 70:
                score_str = f"[green]{score_str}[/green]"
            elif player.average_score >= 50:
                score_str = f"[yellow]{score_str}[/yellow]"
            else:
                score_str = f"[red]{score_str}[/red]"

        rarity_style = card.rarity_color
        rarity_str = f"[{rarity_style}]{card.rarity_label}[/{rarity_style}]"

        # Statut blessure
        if player and player.is_injured:
            status_str = "[red]Blesse[/red]"
        elif player:
            status_str = "[green]OK[/green]"
        else:
            status_str = "-"

        min_eth = (
            f"{card.price_range.min_eth:.4f}" if card.price_range.min_eth else "-"
        )
        max_eth = (
            f"{card.price_range.max_eth:.4f}" if card.price_range.max_eth else "-"
        )

        table.add_row(
            card.player_name,
            age_str,
            club_str,
            rarity_str,
            card.season or "-",
            score_str,
            min_eth,
            max_eth,
            status_str,
        )

    console.print(table)


def _display_sell_analysis(analyses):
    """Affiche les recommandations de vente."""
    sell_now = [a for a in analyses if a.recommendation == SellRecommendation.SELL_NOW]
    sell_soon = [a for a in analyses if a.recommendation == SellRecommendation.SELL_SOON]
    watch = [a for a in analyses if a.recommendation == SellRecommendation.WATCH]
    keep = [a for a in analyses if a.recommendation == SellRecommendation.KEEP]

    console.print(
        f"[bold]Analyse de {len(analyses)} cartes:[/bold] "
        f"[red]{len(sell_now)} à vendre maintenant[/red] | "
        f"[yellow]{len(sell_soon)} à vendre bientôt[/yellow] | "
        f"[cyan]{len(watch)} à surveiller[/cyan] | "
        f"[green]{len(keep)} à garder[/green]\n"
    )

    for group, title, style in [
        (sell_now, "VENDRE MAINTENANT", "red"),
        (sell_soon, "VENDRE BIENTOT", "yellow"),
        (watch, "SURVEILLER", "cyan"),
        (keep, "GARDER", "green"),
    ]:
        if not group:
            continue

        console.print(f"[bold {style}]── {title} ({len(group)}) ──[/bold {style}]")
        console.print()

        for analysis in group:
            card = analysis.card
            player = card.player

            lines = []
            lines.append(
                f"[bold white]{card.player_name}[/bold white] "
                f"| [{card.rarity_color}]{card.rarity_label}[/{card.rarity_color}]"
                f" | Saison {card.season or 'N/A'}"
            )

            if player:
                age_info = f"{player.age} ans" if player.age else "âge inconnu"
                lines.append(
                    f"[dim]{player.club or 'Club inconnu'} | {age_info} | "
                    f"Score: {player.score_display}[/dim]"
                )

            value = card.estimated_value_eth
            if value:
                lines.append(f"Valeur estimée: [cyan]{value:.4f} ETH[/cyan]")

            lines.append("")
            lines.append("[bold]Analyse:[/bold]")
            for reason in analysis.reasons:
                lines.append(f"  • {reason}")

            if analysis.warnings:
                lines.append("")
                lines.append("[bold yellow]Avertissements:[/bold yellow]")
                for w in analysis.warnings:
                    lines.append(f"  [yellow]![/yellow] {w}")

            lines.append(
                f"\n[dim]Conviction de vente: {analysis.score}%[/dim]"
            )

            console.print(
                Panel(
                    "\n".join(lines),
                    border_style=style,
                    padding=(0, 1),
                )
            )

        console.print()


def _display_buy_opportunities(opportunities, criteria: BuyCriteria):
    """Affiche les opportunités d'achat."""
    if not opportunities:
        console.print(
            "[yellow]Aucune opportunité trouvée avec ces critères.[/yellow]\n"
            "Essayez d'assouplir les critères (prix max plus élevé, "
            "score min plus bas, etc.)"
        )
        return

    console.print(
        f"[bold green]{len(opportunities)} opportunité(s) trouvée(s)[/bold green]\n"
    )

    table = Table(
        title=f"Meilleures opportunités d'achat (age <= {criteria.max_age} ans)",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", justify="right", width=3)
    table.add_column("Joueur", style="bold white", min_width=20)
    table.add_column("Age", justify="center", width=5)
    table.add_column("Club", width=18)
    table.add_column("Pos.", justify="center", width=6)
    table.add_column("Score", justify="center", width=7)
    table.add_column("Rarété", justify="center", width=10)
    table.add_column("Prix ETH", justify="right", width=10)
    table.add_column("Opportunité", justify="center", width=12)
    table.add_column("Blessé?", justify="center", width=8)

    for i, opp in enumerate(opportunities[:20], 1):
        p = opp.player
        score_str = p.score_display if p.average_score else "-"
        if p.average_score and p.average_score >= 70:
            score_str = f"[green]{score_str}[/green]"
        elif p.average_score and p.average_score >= 50:
            score_str = f"[yellow]{score_str}[/yellow]"
        elif p.average_score:
            score_str = f"[red]{score_str}[/red]"

        opp_score = opp.score
        if opp_score >= 75:
            opp_str = f"[bold green]{opp_score}/100[/bold green]"
        elif opp_score >= 50:
            opp_str = f"[yellow]{opp_score}/100[/yellow]"
        else:
            opp_str = f"[red]{opp_score}/100[/red]"

        injured_str = "[red]Oui[/red]" if p.is_injured else "[green]Non[/green]"
        price_str = opp.price_display

        table.add_row(
            str(i),
            p.display_name,
            str(p.age) if p.age else "-",
            (p.club or "-")[:18],
            p.position[:6] if p.position else "-",
            score_str,
            opp.rarity.capitalize(),
            price_str,
            opp_str,
            injured_str,
        )

    console.print(table)
    console.print()

    # Détail des top 5
    console.print("[bold]── Détail des 5 meilleures opportunités ──[/bold]\n")

    for i, opp in enumerate(opportunities[:5], 1):
        p = opp.player
        lines = []
        lines.append(
            f"[bold cyan]#{i} {p.display_name}[/bold cyan] "
            f"| {p.age} ans | {p.club or 'Club inconnu'} | {p.position or 'N/A'}"
        )
        lines.append(f"Score: [yellow]{p.score_display}[/yellow] | "
                     f"Rarété: {opp.rarity} | Prix: [cyan]{opp.price_display}[/cyan]")

        if opp.is_injured if hasattr(opp, 'is_injured') else p.is_injured:
            lines.append(f"[red]Blessure: {p.injury.label}[/red]")

        lines.append("")
        lines.append("[bold]Raisons d'achat:[/bold]")
        for r in opp.reasons:
            lines.append(f"  [green]✓[/green] {r}")

        if opp.criteria_matched:
            lines.append("")
            lines.append("[bold]Critères validés:[/bold]")
            for c in opp.criteria_matched:
                lines.append(f"  [cyan]•[/cyan] {c}")

        if opp.risks:
            lines.append("")
            lines.append("[bold yellow]Risques:[/bold yellow]")
            for r in opp.risks:
                lines.append(f"  [yellow]![/yellow] {r}")

        if opp.card_slug:
            lines.append("")
            lines.append(
                f"[dim]Voir sur Sorare: https://sorare.com/fr/cards/{opp.card_slug}[/dim]"
            )

        score_color = "green" if opp.score >= 75 else "yellow" if opp.score >= 50 else "red"
        console.print(
            Panel(
                "\n".join(lines),
                title=f"[{score_color}]Score d'opportunité: {opp.score}/100[/{score_color}]",
                border_style=score_color,
                padding=(0, 1),
            )
        )

    console.print()
    console.print(
        "[dim]Note: Les prix affichés sont des estimations basées sur les données "
        "du marché Sorare. Faites vos propres recherches avant d'acheter.[/dim]"
    )


if __name__ == "__main__":
    cli()
