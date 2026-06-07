#!/usr/bin/env python3
"""
Rend une CARTE PROFIL GOOGLE fidèle (style Maps mobile) à partir de la Places API,
en image 9:16 — le "avant" du Makeover Reveal Show.

Device clé : le bouton "Website" est MANQUANT / grisé = la douleur visualisée.

Pipeline : Places API (searchText) → données + 1 photo → HTML stylé Maps → screenshot
Playwright → out/images/google_profile.png

Prérequis :
    pip3 install -r scripts/requirements.txt
    python3 -m playwright install chromium
    export GOOGLE_MAPS_API_KEY="..."

Usage :
    python3 scripts/render_google_card.py "Joe's Plumbing Austin TX"
    python3 scripts/render_google_card.py --place-id ChIJ....
    # sortie : out/images/google_profile.png  (override avec --out)

⚠️ Données PUBLIQUES uniquement. Le commerce est mis en héros, jamais moqué.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id",
    "places.displayName",
    "places.rating",
    "places.userRatingCount",
    "places.primaryTypeDisplayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.regularOpeningHours",
    "places.websiteUri",
    "places.photos",
])


def load_dotenv() -> None:
    """Charge .env (racine du repo) dans l'environnement, sans écraser l'existant."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Le .env du projet fait autorité : il écrase une éventuelle variable
            # shell (ex: clé Bunua exportée dans ~/.zshrc) pour éviter les surprises.
            os.environ[key] = val


def api_key() -> str:
    load_dotenv()
    k = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_PLACES_API_KEY")
    if not k:
        sys.exit("❌ Manque GOOGLE_MAPS_API_KEY (ni env ni .env).")
    return k.strip()


def search_place(query: str, key: str) -> dict:
    body = json.dumps({"textQuery": query}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": FIELDS,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(
            f"❌ Places API {e.code}. Réponse Google :\n{detail}\n\n"
            "Causes 403 fréquentes : 'Places API (New)' pas activée sur le projet · "
            "facturation non activée · clé restreinte (API/référent/IP)."
        )
    places = data.get("places") or []
    if not places:
        sys.exit(f"❌ Aucun résultat Places pour : {query!r}")
    return places[0]


def fetch_photo_data_uri(place: dict, key: str) -> str | None:
    photos = place.get("photos") or []
    if not photos:
        return None
    name = photos[0].get("name")  # ex: places/XXX/photos/YYY
    if not name:
        return None
    url = f"https://places.googleapis.com/v1/{name}/media?maxWidthPx=900&key={key}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "image/jpeg")
        return f"data:{ctype};base64," + base64.b64encode(raw).decode()
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ photo non récupérée ({e})")
        return None


STAR_PATH = "M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"

# Icônes Material (vectorielles plates) — fidèles à Google Maps, pas d'emoji.
ICONS = {
    "directions": "M21.41 10.59l-7.99-8c-.78-.78-2.05-.78-2.83 0l-8 8c-.78.78-.78 2.05 0 2.83l8 8c.78.78 2.05.78 2.83 0l7.99-8c.79-.79.79-2.05 0-2.83zM13.5 14.5V12H10v3H8v-4c0-.55.45-1 1-1h4.5V7.5L17 11l-3.5 3.5z",
    "call": "M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z",
    "save": "M17 3H7c-1.1 0-1.99.9-1.99 2L5 21l7-3 7 3V5c0-1.1-.9-2-2-2z",
    "website": "M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm6.93 6h-2.95c-.32-1.25-.78-2.45-1.38-3.56 1.84.63 3.37 1.91 4.33 3.56zM12 4.04c.83 1.2 1.48 2.53 1.91 3.96h-3.82c.43-1.43 1.08-2.76 1.91-3.96zM4.26 14C4.1 13.36 4 12.69 4 12s.1-1.36.26-2h3.38c-.08.66-.14 1.32-.14 2 0 .68.06 1.34.14 2H4.26zm.82 2h2.95c.32 1.25.78 2.45 1.38 3.56-1.84-.63-3.37-1.9-4.33-3.56zm2.95-8H5.08c.96-1.66 2.49-2.93 4.33-3.56C8.81 5.55 8.35 6.75 8.03 8zM12 19.96c-.83-1.2-1.48-2.53-1.91-3.96h3.82c-.43 1.43-1.08 2.76-1.91 3.96zM14.34 14H9.66c-.09-.66-.16-1.32-.16-2 0-.68.07-1.35.16-2h4.68c.09.65.16 1.32.16 2 0 .68-.07 1.34-.16 2zm.25 5.56c.6-1.11 1.06-2.31 1.38-3.56h2.95c-.96 1.65-2.49 2.93-4.33 3.56zM16.36 14c.08-.66.14-1.32.14-2 0-.68-.06-1.34-.14-2h3.38c.16.64.26 1.31.26 2s-.1 1.36-.26 2h-3.38z",
    "share": "M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z",
    "pin": "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    "clock": "M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z",
    "close": "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
}

TEAL = "#00696d"          # accent Maps (icônes, onglet actif)
TEAL_FILL = "#00696d"     # bouton principal plein
TEAL_TINT = "#d3eae7"     # ronds d'action secondaires


def _svg(name: str, color: str, size: int = 48) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}">'
            f'<path fill="{color}" d="{ICONS[name]}"/></svg>')


def _star_row(color: str) -> str:
    one = f'<svg viewBox="0 0 24 24" width="36" height="36"><path fill="{color}" d="{STAR_PATH}"/></svg>'
    return one * 5


def stars_html(rating: float) -> str:
    pct = max(0.0, min(100.0, (rating / 5.0) * 100.0))
    return (
        '<span class="stars">'
        f'<span class="stars-bg">{_star_row("#dadce0")}</span>'
        f'<span class="stars-fg" style="width:{pct:.1f}%">{_star_row("#fbbc04")}</span>'
        '</span>'
    )


def _action(name: str, label: str, primary: bool = False) -> str:
    cls = "action primary" if primary else "action"
    icon = _svg(name, "#fff" if primary else TEAL)
    return f'<div class="{cls}"><div class="ic">{icon}</div><div class="lbl">{label}</div></div>'


def build_html(place: dict, photo_uri: str | None, website_device: str = "highlight") -> str:
    name = (place.get("displayName") or {}).get("text", "Local Business")
    rating = place.get("rating")
    count = place.get("userRatingCount")
    category = (place.get("primaryTypeDisplayName") or {}).get("text", "Business")
    address = place.get("formattedAddress", "")
    phone = place.get("nationalPhoneNumber", "")
    open_now = (place.get("regularOpeningHours") or {}).get("openNow")
    has_website = bool(place.get("websiteUri"))

    rating_str = f"{rating:.1f}" if isinstance(rating, (int, float)) else "—"
    count_str = f"({count:,})" if isinstance(count, int) else ""
    status = ("Open" if open_now else "Closed") if open_now is not None else ""
    stars = stars_html(rating) if isinstance(rating, (int, float)) else ""

    hero = (
        f'<div class="hero" style="background-image:url(\'{photo_uri}\')">'
        f'<div class="closebtn">{_svg("close", "#3c4043", 34)}</div></div>'
        if photo_uri else '<div class="hero hero-empty"></div>'
    )

    # Bouton "Website" : LA douleur. Modes : highlight (rouge), absent (réaliste), addsite (vue proprio).
    if has_website:
        website_btn = _action("website", "Website")
    elif website_device == "absent":
        website_btn = ""  # Google n'affiche simplement aucun bouton site
    elif website_device == "addsite":
        website_btn = ('<div class="action addsite"><div class="ic">'
                       f'{_svg("website", "#9aa0a6")}</div><div class="lbl">Add website</div></div>')
    else:  # highlight
        website_btn = ('<div class="action missing"><div class="ic">'
                       f'{_svg("website", "#d93025")}</div><div class="lbl">Website</div></div>')

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; }}
  html,body {{ width:1080px; height:1920px; background:#fff;
    font-family:Roboto,Arial,Helvetica,sans-serif; color:#202124; }}
  .hero {{ position:relative; width:1080px; height:720px;
    background-size:cover; background-position:center; }}
  .hero-empty {{ background:linear-gradient(135deg,#e8eaed,#dadce0); }}
  .closebtn {{ position:absolute; top:36px; right:36px; width:84px; height:84px;
    border-radius:50%; background:#fff; display:flex; align-items:center;
    justify-content:center; box-shadow:0 1px 3px rgba(0,0,0,.3); }}
  .body {{ padding:44px 56px 0; }}
  .name {{ font-size:66px; font-weight:400; letter-spacing:-.5px; }}
  .ratingrow {{ display:flex; align-items:center; gap:14px; margin-top:24px; font-size:36px; color:#5f6368; }}
  .rating-num {{ color:#202124; }}
  .stars {{ position:relative; display:inline-block; height:36px; line-height:0; }}
  .stars-bg svg, .stars-fg svg {{ vertical-align:top; }}
  .stars-fg {{ position:absolute; left:0; top:0; overflow:hidden; white-space:nowrap; }}
  .meta {{ margin-top:14px; font-size:36px; color:#5f6368; }}
  .meta .open {{ color:#188038; }}
  .meta .closed {{ color:#d93025; }}
  .tabs {{ display:flex; gap:64px; margin:40px 0 0; border-bottom:1px solid #e8eaed;
    font-size:34px; color:#5f6368; }}
  .tabs .tab {{ padding-bottom:24px; }}
  .tabs .tab.active {{ color:{TEAL}; border-bottom:4px solid {TEAL}; font-weight:500; }}
  .actions {{ display:flex; gap:24px; margin:48px 0 8px; }}
  .action {{ flex:1; text-align:center; }}
  .action .ic {{ width:104px; height:104px; margin:0 auto 16px; border-radius:50%;
    background:{TEAL_TINT}; display:flex; align-items:center; justify-content:center; }}
  .action.primary .ic {{ background:{TEAL_FILL}; }}
  .action .lbl {{ font-size:30px; color:#3c4043; }}
  .action.missing .ic {{ background:#fce8e6; border:3px dashed #d93025; }}
  .action.missing .lbl {{ color:#d93025; font-weight:500; }}
  .action.addsite .ic {{ background:#f1f3f4; }}
  .action.addsite .lbl {{ color:#9aa0a6; }}
  .rows {{ margin-top:36px; border-top:1px solid #ebebeb; }}
  .row {{ display:flex; align-items:center; gap:34px; padding:36px 4px;
    border-bottom:1px solid #ebebeb; font-size:36px; color:#3c4043; }}
  .row .ic {{ width:48px; flex:none; display:flex; }}
</style></head><body>
  {hero}
  <div class="body">
    <div class="name">{name}</div>
    <div class="ratingrow">
      <span class="rating-num">{rating_str}</span>{stars}
      <span>{count_str}</span>
    </div>
    <div class="meta">{category}{(' · <span class="' + ('open' if open_now else 'closed') + '">' + status + '</span>') if status else ''}</div>
    <div class="tabs">
      <div class="tab active">Overview</div>
      <div class="tab">Reviews</div>
      <div class="tab">About</div>
      <div class="tab">Photos</div>
    </div>
    <div class="actions">
      {_action("directions", "Directions", primary=True)}
      {_action("call", "Call")}
      {_action("save", "Save")}
      {website_btn}
      {_action("share", "Share")}
    </div>
    <div class="rows">
      {f'<div class="row"><div class="ic">{_svg("pin", "#5f6368", 44)}</div><div>{address}</div></div>' if address else ''}
      {f'<div class="row"><div class="ic">{_svg("call", "#5f6368", 44)}</div><div>{phone}</div></div>' if phone else ''}
    </div>
  </div>
</body></html>"""


def render(html: str, out: str) -> None:
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.set_content(html, wait_until="load")
        page.screenshot(path=out)
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", help="Nom du commerce (+ ville)")
    ap.add_argument("--place-id", help="place_id direct (sinon recherche par nom)")
    ap.add_argument("--out", default="out/images/google_profile.png")
    ap.add_argument("--website-device", choices=["highlight", "absent", "addsite"],
                    default="highlight",
                    help="Sans site : highlight=bouton rouge (device), absent=rien (réaliste), "
                         "addsite='Add website' grisé (vue proprio)")
    ap.add_argument("--html-only", action="store_true", help="Écrit le HTML sans screenshot (debug)")
    args = ap.parse_args()

    if not args.query and not args.place_id:
        ap.error("Fournis un nom de commerce ou --place-id.")

    key = api_key()
    query = args.query or args.place_id
    print(f"🔎 Places: {query!r}")
    place = search_place(query, key)
    name = (place.get("displayName") or {}).get("text", "?")
    print(f"  → {name} · note {place.get('rating')} ({place.get('userRatingCount')}) · "
          f"site={'oui' if place.get('websiteUri') else 'NON (cible idéale)'}")

    photo = fetch_photo_data_uri(place, key)
    html = build_html(place, photo, website_device=args.website_device)

    if args.html_only:
        with open("out/google_card_debug.html", "w") as f:
            f.write(html)
        print("📝 HTML debug → out/google_card_debug.html")
        return 0

    render(html, args.out)
    print(f"✅ Carte profil → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
