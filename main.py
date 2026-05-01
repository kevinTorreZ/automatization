import json
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from auto_uploader import (
    create_category,
    detect_game,
    format_category_name,
    sanitize_title,
    upload_script,
)
from rscripts_source import fetch_raw_code, fetch_recent_verified

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

OUTPUT_DIR = "scraped_scripts"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

STATE_FILE = "last_run.json"

# Categorias ya creadas en Bublox: {nombre_formateado -> placeid}
# Se persiste en last_run.json para no re-crearlas en cada run
KNOWN_CATEGORIES = {}


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_state(data):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save state: {e}")


def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"    [ERROR] fetching {url}: {e}")
        return None


def ensure_category_exists(game_name: str, placeid: int) -> str:
    """
    Verifica si la categoria existe localmente. Si no, la crea via API.
    Retorna el nombre formateado de la categoria.
    """
    formatted = format_category_name(game_name)
    if formatted not in KNOWN_CATEGORIES:
        print(f"      [NUEVA CAT]: '{formatted}' no existe, creando...")
        ok = create_category(formatted, placeid)
        if ok:
            KNOWN_CATEGORIES[formatted] = placeid
        else:
            print(f"      [ERROR CAT]: No se pudo crear '{formatted}'")
            return None
    return formatted


def save_script(title, code):
    clean_title = sanitize_title(title)
    safe_title = re.sub(r'[<>:"/\\|?*]', "", clean_title).strip()
    if len(safe_title) > 100:
        safe_title = safe_title[:100]
    filepath = os.path.join(OUTPUT_DIR, f"{safe_title}.lua")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"      [SAVED]: {filepath}")
    except:
        pass

    # Detectar el juego desde el titulo original (sin sanitizar) para no perder pistas
    game_name, placeid = detect_game(title)

    if not game_name:
        print(f"      [SKIP]: No se reconocio ningun juego en '{title}'")
        return

    # Verificar/crear categoria antes de subir el script
    category = ensure_category_exists(game_name, placeid)
    if not category:
        return

    print(f"      [UPLOAD]: '{clean_title}' -> categoria '{category}'")
    upload_script(title, [category], code)


def scrape_tertiary(url, title):
    if not url or (
        url.startswith("https://scriptpastebin.com")
        and "scriptpastebins.com" not in url
    ):
        return
    soup = get_soup(url)
    if not soup:
        return

    code = None
    textareas = soup.find_all("textarea")
    if textareas:
        for ta in textareas:
            c = ta.get_text(strip=True)
            if len(c) > 10:
                code = c
                break
    if not code:
        pres = soup.find_all("pre")
        if pres:
            code = pres[0].get_text(strip=True)

    if code:
        save_script(title, code)
    else:
        print("      No code found on tertiary page.")


def scrape_detail(url):
    soup = get_soup(url)
    if not soup:
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    post_date = None
    time_tag = soup.find("time", class_="entry-date") or soup.find(
        "time", class_="published"
    )

    if time_tag and time_tag.has_attr("datetime"):
        post_date = time_tag["datetime"][:10]

    if post_date:
        if post_date != today_str:
            print(
                f"    [SKIP DATE]: Script date {post_date} is not today ({today_str})."
            )
            return
        else:
            print(f"    [DATE OK]: {post_date}")
    else:
        print("    [WARNING]: Could not extract date. Proceeding with caution...")

    target_title = "Unknown Script"

    button = soup.find("a", string=lambda t: t and "Get Script" in t)
    if not button:
        button = soup.find(
            "a", class_=lambda c: c and "button" in c and "wp-block-button__link" in c
        )

    if button:
        container = button
        for _ in range(3):
            if container.parent and (
                "buttons" in container.parent.get("class", [])
                or "entry-content" in container.parent.get("class", [])
            ):
                break
            container = container.parent

        curr = container
        found = False
        limit = 5
        while curr and limit > 0:
            curr = curr.previous_sibling
            if curr and curr.name in [
                "p",
                "div",
                "h4",
                "h3",
                "h2",
                "h1",
                "strong",
                "span",
            ]:
                text = curr.get_text(strip=True)
                if text and len(text) > 3 and "Step" not in text:
                    target_title = text
                    found = True
                    break
            limit -= 1

        if found:
            print(f"    [TITLE ABOVE]: {target_title}")
        else:
            h1 = soup.find("h1")
            if h1:
                target_title = h1.get_text(strip=True)
                print(f"    [FALLBACK H1]: {target_title}")

        target_link = button.get("href")
        scrape_tertiary(target_link, target_title)
    else:
        h1 = soup.find("h1")
        if h1:
            target_title = h1.get_text(strip=True)
        scrape_tertiary(url, target_title)


def run_rscripts(state, max_pages=2):
    """
    Sube los scripts más recientes de rscripts.net cumpliendo:
    - verifiedOnly=true (autores verificados)
    - noKeySystem=true (sin sistema de keys)
    - orderBy=date sort=desc (lo más reciente primero)
    Dedup: persiste set de _id ya subidos en state['rscripts_uploaded_ids'].
    """
    seen_ids = set(state.get("rscripts_uploaded_ids", []))
    new_uploaded = 0
    skipped_seen = 0
    skipped_nogame = 0
    skipped_norawcode = 0

    print(f"[rscripts] {len(seen_ids)} IDs previamente subidos.")

    for s in fetch_recent_verified(max_pages=max_pages):
        sid = s.get("_id")
        title = (s.get("title") or "").strip()
        if not sid or not title:
            continue

        if sid in seen_ids:
            skipped_seen += 1
            continue

        game = s.get("game") or {}
        game_name = (game.get("title") or "").strip()
        place_id = game.get("placeId")
        try:
            place_id = int(place_id) if place_id is not None else None
        except (TypeError, ValueError):
            place_id = None

        if not game_name or not place_id:
            print(f"  [SKIP] '{title[:60]}': sin game/placeId")
            skipped_nogame += 1
            continue

        raw_url = s.get("rawScript")
        code = fetch_raw_code(raw_url)
        if not code:
            print(f"  [SKIP] '{title[:60]}': raw vacío o inaccesible")
            skipped_norawcode += 1
            continue

        category = ensure_category_exists(game_name, place_id)
        if not category:
            seen_ids.add(sid)
            continue

        clean_title = sanitize_title(title)
        print(f"  [UPLOAD]: '{clean_title[:80]}' -> '{category}'")
        ok = upload_script(title, [category], code)
        if ok:
            seen_ids.add(sid)
            new_uploaded += 1
        time.sleep(1)

    state["rscripts_uploaded_ids"] = sorted(seen_ids)
    print(
        f"[rscripts] subidos: {new_uploaded} | ya vistos: {skipped_seen} | "
        f"sin juego: {skipped_nogame} | sin raw: {skipped_norawcode}"
    )


def main():
    global KNOWN_CATEGORIES

    state = load_state()
    last_run_date = state.get("last_successful_run", "")
    today_str = datetime.now().strftime("%Y-%m-%d")

    if last_run_date == today_str:
        print(f"[INFO] Script already ran successfully today ({today_str}). Exiting.")
        return

    # Cargar categorias conocidas desde el estado persistido
    KNOWN_CATEGORIES = state.get("known_categories", {})
    print(f"[INFO] {len(KNOWN_CATEGORIES)} categorias conocidas cargadas desde estado.")

    try:
        # ───── Fuente 1: rscripts.net API (verificados, sin keys, recientes) ─────
        print("\n=== rscripts.net ===")
        run_rscripts(state)

        # ───── Fuente 2: scriptpastebin.com (HTML scrape, fallback) ─────
        print("\n=== scriptpastebin.com ===")
        base_url = "https://scriptpastebin.com/"
        print(f"Fetching homepage: {base_url}")
        soup = get_soup(base_url)
        if soup:
            article = soup.find("article")
            items = []
            if article:
                headers = article.find_all("h3")
                for h in headers:
                    a = h.find("a")
                    if a:
                        items.append({"link": a.get("href")})
            else:
                headers = soup.find_all("h3")
                for h in headers:
                    a = h.find("a")
                    if a:
                        items.append({"link": a.get("href")})

            print(f"Found {len(items)} items. Processing...")

            for i, item in enumerate(items):
                print(f"Processing Item {i + 1}...")
                scrape_detail(item["link"])
                time.sleep(1)

        state["last_successful_run"] = today_str
        state["known_categories"] = KNOWN_CATEGORIES
        save_state(state)
        print(f"[SUCCESS] Process completed for {today_str}. State saved.")

    except Exception as e:
        print(f"[ERROR] {e}")
        # Guardar categorias y dedup aunque haya error, para no perderlas
        state["known_categories"] = KNOWN_CATEGORIES
        save_state(state)


if __name__ == "__main__":
    main()
