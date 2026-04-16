# Sorare Card Analyzer

Analyseur intelligent de cartes Sorare. Connectez-vous à votre compte Sorare pour:
- **Voir vos cartes** avec leurs valeurs de marché
- **Savoir quand vendre** basé sur les performances, blessures et prix du marché
- **Trouver quoi acheter** selon vos critères (jeunes joueurs, blessés temporaires, etc.)

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Éditez .env avec vos identifiants Sorare
```

## Utilisation

### Voir vos cartes
```bash
python main.py mes-cartes
```

### Recommandations de vente
```bash
python main.py vendre
```

### Rechercher des cartes à acheter
```bash
# Par défaut: joueurs < 20 ans, score >= 50, prix <= 0.1 ETH
python main.py acheter

# Personnalisé: joueurs < 18 ans, bon score, pas cher
python main.py acheter --age-max 18 --score-min 60 --prix-max 0.05

# Inclure les blessés (opportunités de prix bas)
python main.py acheter --blesses --age-max 22

# Filtrer par position
python main.py acheter --positions Midfielder --positions Forward

# Chercher uniquement des cartes Limited
python main.py acheter --rarete limited
```

## Critères d'analyse

### Vente (analyse de vos cartes)
| Signal | Poids | Action |
|--------|-------|--------|
| Joueur blessé (durée inconnue) | Fort | Vendre maintenant |
| Joueur blessé (retour prévu) | Moyen | Vendre bientôt |
| Score moyen < seuil | Moyen | Vendre bientôt |
| Offre en cours sur la carte | Faible | Saisir l'occasion |
| Carte Limited | Faible | Plus liquide = facile à revendre |
| Score >= 70 | Négatif | Garder |
| Carte Unique/Super Rare | Fort négatif | Garder sauf urgence |

### Achat (recherche d'opportunités)
| Critère | Description |
|---------|-------------|
| `--age-max` | Limite d'âge (défaut: 20 ans) |
| `--score-min` | Score minimum Sorare/100 (défaut: 50) |
| `--prix-max` | Prix maximum en ETH (défaut: 0.1) |
| `--blesses` | Inclure les joueurs blessés (opportunités) |
| `--positions` | Filtrer par position |
| `--rarete` | Filtrer par rareté (limited, rare, etc.) |

## Configuration .env

```env
SORARE_EMAIL=votre@email.com
SORARE_PASSWORD=votre_mot_de_passe

# Seuils personnalisés
MAX_AGE_BUY=20
MIN_SCORE_BUY=50
MAX_PRICE_ETH=0.1
MIN_PROFIT_PERCENT=30
MIN_SCORE_KEEP=40
```

## Structure du projet

```
sorare/
├── main.py              # CLI principal
├── config.py            # Configuration et variables d'environnement
├── requirements.txt
├── .env.example
├── api/
│   ├── auth.py          # Authentification Sorare (JWT)
│   ├── client.py        # Client GraphQL
│   └── queries.py       # Requêtes GraphQL
├── models/
│   ├── card.py          # Modèle de carte
│   └── player.py        # Modèle de joueur
└── analysis/
    ├── sell_analyzer.py # Analyse de vente
    └── buy_analyzer.py  # Analyse d'achat
```
