"""
Client GraphQL pour l'API Sorare.
Gère l'authentification et les requêtes.
"""
import asyncio
from typing import Any, Dict, Optional

import aiohttp

from config import SORARE_GRAPHQL_URL, SORARE_EMAIL, SORARE_PASSWORD, SORARE_JWT
from api.auth import get_jwt_token


class SorareClient:
    """Client pour l'API GraphQL de Sorare."""

    def __init__(self, jwt_token: Optional[str] = None):
        self.jwt_token = jwt_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(self, *args):
        await self._close()

    async def _connect(self):
        """Ouvre la session HTTP et s'authentifie si nécessaire."""
        if not self.jwt_token:
            if SORARE_JWT:
                self.jwt_token = SORARE_JWT
            elif SORARE_EMAIL and SORARE_PASSWORD:
                self.jwt_token = await get_jwt_token(SORARE_EMAIL, SORARE_PASSWORD)
            else:
                raise ValueError(
                    "Identifiants manquants. Créez un fichier .env avec "
                    "SORARE_JWT ou SORARE_EMAIL + SORARE_PASSWORD (voir .env.example)"
                )

        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://sorare.com",
                "Referer": "https://sorare.com/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )

    async def _close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Exécute une requête GraphQL et retourne les données.
        Lève une exception en cas d'erreur GraphQL.
        """
        payload = {"query": query, "variables": variables or {}}

        async with self._session.post(
            SORARE_GRAPHQL_URL, json=payload
        ) as resp:
            if resp.status == 401:
                raise PermissionError(
                    "Token expiré ou invalide. Reconnectez-vous."
                )
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"Erreur API ({resp.status}): {text[:500]}"
                )

            data = await resp.json()

            if "errors" in data:
                errors = data["errors"]
                messages = [e.get("message", str(e)) for e in errors]
                raise RuntimeError(
                    "Erreurs GraphQL:\n" + "\n".join(f"  - {m}" for m in messages)
                )

            return data.get("data", {})

    async def paginate(
        self,
        query: str,
        path: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> list:
        """
        Récupère toutes les pages d'une requête paginée.
        `path` est le chemin vers le nœud paginé (ex: "currentUser.cards").
        """
        all_nodes = []
        cursor = None
        vars_copy = dict(variables or {})

        while True:
            if cursor:
                vars_copy["after"] = cursor

            data = await self.query(query, vars_copy)

            # Naviguer dans le chemin
            node = data
            for key in path.split("."):
                node = node.get(key, {})

            nodes = node.get("nodes", [])
            all_nodes.extend(nodes)

            page_info = node.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return all_nodes


async def create_client(jwt_token: Optional[str] = None) -> SorareClient:
    """Crée et connecte un client Sorare."""
    client = SorareClient(jwt_token=jwt_token)
    await client._connect()
    return client
