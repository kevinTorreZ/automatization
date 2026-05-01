import os
import re

import requests

CATEGORY_API = "https://uploadcategory-4v2s5sfrtq-uc.a.run.app"
SCRIPT_API = "https://uploadscript-4v2s5sfrtq-uc.a.run.app"

# Términos prohibidos en título/descripción (regex, case-insensitive).
# Motivo: contenido amigable para anunciantes / mejor CPM.
FORBIDDEN_PATTERNS = [
    # Combos largos primero (más específico → más general).
    r"\bauto[-\s]?farm(?:ing|er|ers)?\s+autom[aá]tic[oa]s?\b",
    r"\bfarm(?:ing|er|ers)?\s+autom[aá]tic[oa]s?\b",
    r"\banti[-\s]?cheat\s+bypass\b",
    r"\ba\.?c\.?\s+bypass\b",
    r"\bsilent\s+aim\b",
    r"\bskin\s*changer\b",
    r"\bwall[-\s]?hack(?:s)?\b",
    r"\baim[-\s]?bot(?:s)?\b",
    r"\brage[-\s]?bot(?:s)?\b",
    r"\blegit[-\s]?bot(?:s)?\b",
    r"\btrigger[-\s]?bot(?:s)?\b",
    r"\bno[-\s]?clip\b",
    r"\bgod\s*mode\b",
    r"\bunlock\s+all\b",
    r"\bremote\s+spy\b",
    r"\bop\s+scripts?\b",
    r"\bmod\s*menu\b",
    r"\bfree\s+robux\b",
    r"\brobux\s+gratis\b",
    # "no key" / "keyless" / "[NO KEY]"
    r"\bno[-\s]?keys?\b",
    r"\bkey[-\s]?less\b",
    r"\bkey\s+system\b",
    # Familia "Auto X": auto raid/loot/buy/build/quest/skill/parry/...
    r"\bauto[-\s]?farm(?:ing|er|ers)?\b",
    r"\bfarm(?:ing|er|ers)?\b",
    r"\bauto[-\s]+[a-záéíóúñ]+\b",
    # "AutoRob", "AutoFarm", "AutoLoot" sin separador (lista cerrada para
    # no atrapar "automatic", "autonomous", "automation").
    r"\bauto(?:rob|raid|loot|buy|build|quest|skill|parry|dodge|rebirth|reborn|skip|kill|attack|level|grind|sell|equip|claim|collect|spin|dig|fish|fly|tp|tele|teleport|stats|win|reroll|prestige|click|hit|hatch|merge|fuse|pull|trade|spawn|food|sprint|swim|jump|combo|shoot|aim|use|complete|train|race|play|join|leave|bring|pop|spam|hold|press)\b",
    # Stat boosters / chest spawners
    r"\binf(?:inite|inity)?\s+[a-záéíóúñ]+\b",
    r"\bspoof(?:er|ers|ing)?\b",
    r"\bspawner(?:s)?\b",
    r"\bdisabler(?:s)?\b",
    # Términos genéricos al final.
    r"\besp\b",
    r"\bdupe(?:s|d|r|rs|ing)?\b",
    r"\bscripts?\b",
    r"\bexploits?\b",
    r"\bhacks?\b",
    r"\bcheats?\b",
    r"\bbypass(?:es|ed|ing)?\b",
    r"\binject(?:or|ion|ed|ing)?\b",
    r"\bexec(?:utor|ute|uting)?\b",
]

FORBIDDEN_WORDS = [
    "script", "scripts", "exploit", "exploits", "hack", "hacks",
    "cheat", "cheats", "farm", "farming", "autofarm", "auto farm",
    "auto-farm", "auto raid", "auto loot", "auto buy", "auto build",
    "auto quest", "auto skill", "auto parry", "auto dodge",
    "auto rebirth", "auto reborn", "auto skip", "auto kill",
    "auto attack", "auto level", "auto grind", "auto sell",
    "auto equip", "auto claim", "auto collect", "auto spin",
    "auto dig", "auto fish", "auto fly", "auto teleport", "auto tp",
    "auto stats", "auto rob", "auto win",
    "no key", "no keys", "nokey", "keyless", "key system",
    "bypass", "injector", "inject", "executor", "exec",
    "mod menu", "op script", "free robux", "robux gratis",
    "aimbot", "silent aim", "triggerbot", "wallhack", "wall hack",
    "ragebot", "legitbot", "skinchanger", "skin changer",
    "ac bypass", "anti-cheat bypass", "esp", "noclip", "no clip",
    "god mode", "dupe", "spoofer", "spawner", "disabler",
    "unlock all", "remote spy", "infinite",
]


def sanitize_title(title: str) -> str:
    """Remueve términos prohibidos y limpia separadores residuales."""
    if not title:
        return title
    cleaned = title
    for pat in FORBIDDEN_PATTERNS:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    # Brackets/paréntesis con solo whitespace dentro: "[ ]", "(  )"
    cleaned = re.sub(r"[\(\[\{]\s*[\)\]\}]", " ", cleaned)
    # "word , word" → "word, word" (whitespace antes del separador)
    cleaned = re.sub(r"\s+([,;|])", r"\1", cleaned)
    # Colapsar separadores repetidos (",,", " - - ", "| |", etc.)
    cleaned = re.sub(r"([,;|/\\\-]\s*){2,}", lambda m: m.group(0)[0] + " ", cleaned)
    # Whitespace múltiple → uno
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Quitar separadores sueltos al inicio/fin
    cleaned = re.sub(r"^[\s\-|:•·,.;/\\\(\[\{]+|[\s\-|:•·,.;/\\\)\]\}]+$", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned or title


# Prompt que se envía al backend para que genere título y descripción
# optimizados para CPM/SEO y libres de términos demonetizables.
TITLE_DESCRIPTION_PROMPT = (
    "You are an SEO copywriter for a Roblox guides website monetized with ads (CPM-driven). "
    "Given a base title and a Roblox game, produce an advertiser-friendly title and "
    "meta description.\n\n"
    "ADVERTISER / CPM SAFETY (hard rules):\n"
    "- NEVER use these words or close variants: script, scripts, exploit, exploits, "
    "hack, hacks, cheat, cheats, farm, farming, auto farm, autofarm, auto-farm, "
    "bypass, injector, inject, executor, exec, mod menu, op script, free robux.\n"
    "- Family-friendly, advertiser-safe language only. No profanity, slurs, NSFW, "
    "violence, gambling, or adult terms. Frame everything as a guide, tips, "
    "walkthrough, update notes, codes, or feature overview.\n\n"
    "QUALITY RULES (high CTR + CPM):\n"
    "- Title: 50-65 chars. Front-load the Roblox game name + a concrete benefit "
    "(\"Guide\", \"Tips\", \"Walkthrough\", \"Update\", \"Codes\", \"Best Strategies\", "
    "\"Beginner Guide\", \"Tier List\"). Title Case. No clickbait spam, no emojis, "
    "no ALL CAPS, no excessive punctuation.\n"
    "- Description: 140-160 chars. Natural, keyword-rich meta description. Mentions "
    "the game, what the reader will learn, and one specific feature/benefit. Ends "
    "with a soft CTA (\"Read the full guide\", \"Check the latest tips\").\n"
    "- Use neutral, evergreen wording so the page stays advertiser-safe long term.\n\n"
    "Return STRICT JSON only: {\"title\": \"...\", \"description\": \"...\"}"
)

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


_ROBLOX_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.roblox.com/",
    "Origin": "https://www.roblox.com",
}


def _search_roblox_placeid(game_name: str) -> int:
    """
    Busca el placeId del juego en Roblox con varios endpoints en cadena.
    Retorna 0 si no encuentra nada.
    """
    # Intento 1: omni-search (la búsqueda que usa la home de Roblox).
    # Devuelve grupos por contentGroupType; el primero con type=Game tiene rootPlaceId.
    try:
        url = (
            "https://apis.roblox.com/search-api/omni-search"
            f"?searchQuery={requests.utils.quote(game_name)}"
            "&pageType=all&sessionId=00000000-0000-0000-0000-000000000000"
        )
        r = requests.get(url, headers=_ROBLOX_HEADERS, timeout=10)
        if r.status_code == 200:
            for group in r.json().get("searchResults", []):
                if group.get("contentGroupType") in ("Game", "game", "Games"):
                    for entry in group.get("contents", []):
                        place_id = entry.get("rootPlaceId")
                        if place_id:
                            name = entry.get("name", "?")
                            print(
                                f"  [Roblox] '{game_name}' -> '{name}' "
                                f"placeid: {place_id} (omni-search)"
                            )
                            return int(place_id)
                    break
    except Exception as e:
        print(f"  [Roblox] omni-search fallo: {e}")

    # Intento 2: search/v1/search/universes -> games?universeIds=
    try:
        url1 = (
            "https://apis.roblox.com/search/v1/search/universes"
            f"?keyword={requests.utils.quote(game_name)}"
            "&sessionId=00000000-0000-0000-0000-000000000000&limit=1"
        )
        r1 = requests.get(url1, headers=_ROBLOX_HEADERS, timeout=10)
        if r1.status_code == 200:
            universe_id = (r1.json().get("data") or [{}])[0].get("id")
            if universe_id:
                r2 = requests.get(
                    f"https://games.roblox.com/v1/games?universeIds={universe_id}",
                    headers=_ROBLOX_HEADERS,
                    timeout=10,
                )
                if r2.status_code == 200:
                    place_id = (r2.json().get("data") or [{}])[0].get("rootPlaceId")
                    if place_id:
                        print(f"  [Roblox] '{game_name}' -> placeid: {place_id} (universes)")
                        return int(place_id)
    except Exception as e:
        print(f"  [Roblox] universes fallo: {e}")

    # Intento 3: games/list legacy
    try:
        r = requests.get(
            "https://games.roblox.com/v1/games/list",
            params={"keyword": game_name, "maxRows": 1, "startRows": 0},
            headers=_ROBLOX_HEADERS,
            timeout=10,
        )
        if r.status_code == 200:
            games = r.json().get("games") or []
            if games:
                place_id = games[0].get("PlaceID") or games[0].get("placeId")
                if place_id:
                    print(f"  [Roblox] '{game_name}' -> placeid: {place_id} (legacy)")
                    return int(place_id)
    except Exception as e:
        print(f"  [Roblox] legacy fallo: {e}")

    print(f"  [Roblox] Sin resultados para '{game_name}' tras 3 intentos.")
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
    """Sube un script via API con título sanitizado y prompt CPM-friendly."""
    safe_title = sanitize_title(title)
    if safe_title != title:
        print(f"  [SANITIZE] '{title}' -> '{safe_title}'")
    payload = {
        "baseTitle": safe_title,
        "originalTitle": title,
        "categories": categories,
        "code": code,
        "prompt": TITLE_DESCRIPTION_PROMPT,
        "forbiddenWords": FORBIDDEN_WORDS,
        "openaiKey": os.environ.get("OPENAI_KEY", ""),
    }
    try:
        resp = requests.post(SCRIPT_API, json=payload, timeout=60)
        if resp.status_code in (200, 201):
            print(f"  [API] Script '{safe_title}' subido correctamente.")
            return True
        else:
            print(f"  [API] Error subiendo script: {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [API] Excepcion subiendo script: {e}")
        return False
