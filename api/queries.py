"""
Requêtes GraphQL pour l'API Sorare.
Documentation: https://api.sorare.com/federation/graphql
"""

# Récupérer les cartes de l'utilisateur connecté
MY_CARDS_QUERY = """
query MyCards($after: String) {
  currentUser {
    slug
    nickname
    cards(first: 50, after: $after) {
      nodes {
        slug
        serialNumber
        rarity
        season
        tradeableStatus
        publicMinPrice
        publicMaxPrice
        card {
          slug
          rarity
          season
          serialNumber
          priceRange {
            min
            max
          }
        }
        player {
          slug
          displayName
          age
          position
          country {
            name
          }
          activeClub {
            name
          }
          averageScore(type: LAST_FIFTEEN_SO5_AVERAGE_SCORE)
          latestFinalFixtureStats {
            score
            decisiveActions
            allAroundStats {
              totalScore
            }
          }
          injuryStatus {
            active
            probability
            expectedReturnDate
            description
          }
        }
        latestAuction {
          bestBid {
            amount
          }
          endDate
        }
        openForOffers
        notContractual
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

# Récupérer les prix du marché pour une carte
CARD_MARKET_QUERY = """
query CardMarket($slug: String!) {
  card(slug: $slug) {
    slug
    priceRange {
      min
      max
    }
    openAuctions(first: 5) {
      nodes {
        bestBid {
          amount
        }
        endDate
        minNextBid
      }
    }
    recentSales: tokenAuctions(
      sortByEndDate: true
      first: 5
    ) {
      nodes {
        soldAt
        bestBid {
          amount
        }
      }
    }
  }
}
"""

# Rechercher des joueurs selon des critères
SEARCH_PLAYERS_QUERY = """
query SearchPlayers(
  $maxAge: Int
  $positions: [PlayerPosition!]
  $after: String
) {
  players(
    first: 50
    after: $after
    ageMax: $maxAge
    positions: $positions
  ) {
    nodes {
      slug
      displayName
      age
      position
      country {
        name
      }
      activeClub {
        name
      }
      averageScore(type: LAST_FIFTEEN_SO5_AVERAGE_SCORE)
      injuryStatus {
        active
        probability
        expectedReturnDate
        description
      }
      cards(first: 1, rarities: [limited]) {
        nodes {
          slug
          rarity
          priceRange {
            min
            max
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

# Récupérer les informations d'un joueur spécifique
PLAYER_DETAIL_QUERY = """
query PlayerDetail($slug: String!) {
  player(slug: $slug) {
    slug
    displayName
    age
    position
    country {
      name
    }
    activeClub {
      name
    }
    averageScore(type: LAST_FIFTEEN_SO5_AVERAGE_SCORE)
    latestFinalFixtureStats {
      score
      decisiveActions
      allAroundStats {
        totalScore
      }
    }
    injuryStatus {
      active
      probability
      expectedReturnDate
      description
    }
    cards(first: 10, rarities: [limited, rare, super_rare, unique]) {
      nodes {
        slug
        rarity
        serialNumber
        priceRange {
          min
          max
        }
      }
    }
  }
}
"""

# Récupérer les meilleures ventes récentes du marché
MARKET_BEST_SELLERS_QUERY = """
query MarketBestSellers {
  tokenAuctions(
    first: 20
    sortByEndDate: true
  ) {
    nodes {
      slug
      bestBid {
        amount
      }
      soldAt
      card {
        slug
        rarity
        player {
          displayName
          age
          averageScore(type: LAST_FIFTEEN_SO5_AVERAGE_SCORE)
        }
      }
    }
  }
}
"""
