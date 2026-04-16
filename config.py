import os
from dotenv import load_dotenv

load_dotenv()

SORARE_GRAPHQL_URL = "https://api.sorare.com/federation/graphql"
SORARE_AUTH_URL = "https://api.sorare.com/api/v1/users/sign_in"

SORARE_EMAIL = os.getenv("SORARE_EMAIL", "")
SORARE_PASSWORD = os.getenv("SORARE_PASSWORD", "")
SORARE_JWT = os.getenv("SORARE_JWT", "")

# Critères d'achat
MAX_AGE_BUY = int(os.getenv("MAX_AGE_BUY", "20"))
MIN_SCORE_BUY = float(os.getenv("MIN_SCORE_BUY", "50"))
MAX_PRICE_ETH = float(os.getenv("MAX_PRICE_ETH", "0.1"))

# Critères de vente
MIN_PROFIT_PERCENT = float(os.getenv("MIN_PROFIT_PERCENT", "30"))
MIN_SCORE_KEEP = float(os.getenv("MIN_SCORE_KEEP", "40"))
