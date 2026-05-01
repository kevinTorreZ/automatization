"""
Source: rscripts.net public API.

Filtra los scripts más recientes de usuarios verificados sin sistema de keys
(orderBy=date, sort=desc, verifiedOnly=true, noKeySystem=true).

La API trae directamente:
- title, lastUpdated, _id, slug
- rawScript: URL al .lua/.txt con el código
- game.title + game.placeId  (no necesitamos OpenAI ni Roblox lookup)

Atribución: la API requiere mostrar "Powered by Rscripts.net" en cualquier
app que la consuma.
"""

import time

import requests

API_URL = "https://rscripts.net/api/v2/scripts"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://rscripts.net/",
}


def fetch_recent_verified(max_pages: int = 2, sleep_between: float = 1.0):
    """
    Itera scripts: verificados, sin keys, ordenados por fecha desc.
    Yields el dict completo del script tal como lo devuelve la API.
    """
    for page in range(1, max_pages + 1):
        params = {
            "page": page,
            "orderBy": "date",
            "sort": "desc",
            # La API espera 1/0, NO strings "true"/"false" (los strings se ignoran).
            "verifiedOnly": 1,
            "noKeySystem": 1,
        }
        try:
            resp = requests.get(API_URL, params=params, headers=DEFAULT_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [rscripts] page {page} fetch fallo: {e}")
            return

        scripts = data.get("scripts") or []
        info = data.get("info") or {}
        print(
            f"  [rscripts] page {page}/{info.get('maxPages', '?')}: "
            f"{len(scripts)} scripts"
        )
        if not scripts:
            return

        for s in scripts:
            yield s

        # Si pedimos más páginas que las que existen, cortamos.
        if info.get("maxPages") and page >= int(info["maxPages"]):
            return

        time.sleep(sleep_between)


def fetch_raw_code(url: str) -> str | None:
    """Descarga el código del script. Retorna None si falla."""
    if not url:
        return None
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        resp.raise_for_status()
        text = resp.text or ""
        if len(text.strip()) < 10:
            return None
        return text
    except Exception as e:
        print(f"  [rscripts] raw fetch fallo ({url}): {e}")
        return None
