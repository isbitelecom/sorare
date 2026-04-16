"""
Authentification Sorare via email/mot de passe.
Retourne un token JWT pour les requêtes GraphQL.
"""
import aiohttp
import hashlib
from config import SORARE_AUTH_URL


async def get_jwt_token(email: str, password: str) -> str:
    """
    Authentifie l'utilisateur sur Sorare et retourne le token JWT.
    Sorare utilise une authentification en deux étapes:
    1. Récupérer le salt pour le mot de passe hashé
    2. Envoyer email + mot de passe hashé pour obtenir le JWT
    """
    async with aiohttp.ClientSession() as session:
        # Étape 1: récupérer le salt
        salt_url = f"https://api.sorare.com/api/v1/users/{email}/salt"
        async with session.get(salt_url) as resp:
            if resp.status != 200:
                raise ValueError(
                    f"Utilisateur introuvable ({resp.status}). "
                    "Vérifiez votre email dans le fichier .env"
                )
            salt_data = await resp.json()
            salt = salt_data.get("salt", "")

        # Étape 2: hasher le mot de passe avec le salt
        hashed_password = _hash_password(password, salt)

        # Étape 3: s'authentifier
        payload = {
            "user": {
                "email": email,
                "password": hashed_password,
            }
        }
        headers = {"Content-Type": "application/json"}
        async with session.post(SORARE_AUTH_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise ValueError(
                    f"Erreur d'authentification ({resp.status}): {body}\n"
                    "Vérifiez vos identifiants dans le fichier .env"
                )
            data = await resp.json()
            token = data.get("jwt")
            if not token:
                raise ValueError("Token JWT non reçu. Vérifiez vos identifiants.")
            return token


def _hash_password(password: str, salt: str) -> str:
    """Hash le mot de passe avec le salt fourni par Sorare (SHA512)."""
    salted = f"{password}{salt}"
    return hashlib.sha512(salted.encode("utf-8")).hexdigest()
