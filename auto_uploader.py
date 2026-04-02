import requests
import os

CATEGORY_API = "https://uploadcategory-4v2s5sfrtq-uc.a.run.app"
SCRIPT_API = "https://uploadscript-4v2s5sfrtq-uc.a.run.app"

# Cache rapido: game name (lowercase) -> place ID
# Los juegos desconocidos se identifican via IA y se buscan en Roblox automaticamente.
KNOWN_GAMES = {
    "blox fruits": 2753915549,
    "sailor piece": 77747658251236,
    "anime adventures": 9694647334,
    "pet simulator x": 6284583030,
    "pet simulator 99": 8737899170,
    "adopt me": 920587237,
    "arsenal": 286090429,
    "da hood": 2788229376,
    "brookhaven": 4924922222,
    "murder mystery 2": 142823291,
    "tower of hell": 1962086868,
    "jailbreak": 606849621,
    "dragons life": 677333862,
    "fruit battlegrounds": 13772394625,
    "king legacy": 3224257968,
}


def format_category_name(name: str) -> str:
    """Solo la primera palabra lleva mayuscula: 'Blox fruits'."""
    words = name.strip().split()
    if not words:
        return name
    result = words[0].capitalize()
    if len(words) > 1:
        result += " " + " ".join(w.lower() for w in words[1:])
    return result


def _ask_ai_game_name(title: str, openai_key: str) -> str | None:
    """
    Le pregunta a OpenAI cual es el juego de Roblox del script a partir del titulo.
    Retorna el nombre del juego o None si no lo identifica.
    """
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in Roblox games. "
                            "Given a script title from scriptpastebin.com, extract ONLY the Roblox game name. "
                            "Reply with just the game name, nothing else. "
                            "If you cannot determine the game, reply with UNKNOWN."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f'What Roblox game is this script for? Title: "{title}"',
                    },
                ],
                "max_tokens": 20,
                "temperature": 0,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            game_name = resp.json()["choices"][0]["message"]["content"].strip()
            if game_name.upper() != "UNKNOWN" and len(game_name) > 1:
                print(f"  [AI] Juego identificado: '{game_name}'")
                return game_name
        else:
            print(f"  [AI] Error OpenAI: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        print(f"  [AI] Excepcion: {e}")
    return None


def _search_roblox_placeid(game_name: str) -> int:
    """
    Busca el place ID del juego en la API publica de Roblox.
    Retorna 0 si no encuentra nada.
    """
    try:
        resp = requests.get(
            "https://games.roblox.com/v1/games/list",
            params={"model.keyword": game_name, "model.maxRows": 6, "model.startRows": 0},
            timeout=10,
        )
        if resp.status_code == 200:
            games = resp.json().get("games", [])
            if games:
                placeid = games[0].get("placeId", 0)
                print(f"  [Roblox] '{game_name}' -> placeid: {placeid}")
                return placeid
        print(f"  [Roblox] Sin resultados para '{game_name}' (status: {resp.status_code})")
    except Exception as e:
        print(f"  [Roblox] Error: {e}")
    return 0


def detect_game(title: str):
    """
    Estrategia en 3 pasos:
    1. Match directo en KNOWN_GAMES (sin llamadas externas)
    2. Preguntar a OpenAI que juego es y verificar en KNOWN_GAMES
    3. Si sigue sin encontrarse, buscar el placeid en la API de Roblox

    Retorna (nombre_formateado, placeid) o (None, None).
    """
    openai_key = os.getenv(
        "OPENAI_KEY","")
    title_lower = title.lower()

    # Paso 1: match directo en KNOWN_GAMES
    for game_key, placeid in KNOWN_GAMES.items():
        if game_key in title_lower:
            return format_category_name(game_key), placeid

    # Paso 2: preguntar a la IA
    ai_game_name = _ask_ai_game_name(title, openai_key)
    if not ai_game_name:
        return None, None

    ai_game_lower = ai_game_name.lower()

    # Verificar si la IA identifico un juego ya conocido
    for game_key, placeid in KNOWN_GAMES.items():
        if game_key in ai_game_lower or ai_game_lower in game_key:
            KNOWN_GAMES[ai_game_lower] = placeid  # Guardar alias en cache
            return format_category_name(game_key), placeid

    # Paso 3: juego nuevo, buscar placeid en Roblox
    placeid = _search_roblox_placeid(ai_game_name)
    if placeid:
        KNOWN_GAMES[ai_game_lower] = placeid
        return format_category_name(ai_game_name), placeid

    print(f"  [detect_game] No se pudo obtener placeid para '{ai_game_name}'")
    return None, None


def create_category(name: str, placeid: int) -> bool:
    """Crea una nueva categoria via API. El nombre solo lleva mayuscula en la primera palabra."""
    formatted = format_category_name(name)
    payload = {"name": formatted, "placeid": placeid}
    try:
        resp = requests.post(CATEGORY_API, json=payload, timeout=30)
        if resp.status_code in (200, 201):
            print(f"  [API] Categoria '{formatted}' creada (placeid: {placeid}).")
            return True
        else:
            print(f"  [API] Error creando categoria: {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [API] Excepcion creando categoria: {e}")
        return False


def upload_script(title: str, categories: list, code: str) -> bool:
    """Sube un script via API."""
    openai_key = os.getenv("OPENAI_KEY", "")
    payload = {
        "baseTitle": title,
        "categories": categories,
        "openaiKey": openai_key,
        "code": code,
    }
    try:
        resp = requests.post(SCRIPT_API, json=payload, timeout=60)
        if resp.status_code in (200, 201):
            print(f"  [API] Script '{title}' subido correctamente.")
            return True
        else:
            print(f"  [API] Error subiendo script: {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [API] Excepcion subiendo script: {e}")
        return False
