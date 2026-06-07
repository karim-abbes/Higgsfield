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


def stars_html(rating: float) -> str:
    pct = max(0.0, min(100.0, (rating / 5.0) * 100.0))
    return (
        '<span class="stars">'
        '<span class="stars-bg">★★★★★</span>'
        f'<span class="stars-fg" style="width:{pct:.1f}%">★★★★★</span>'
        '</span>'
    )


def build_html(place: dict, photo_uri: str | None) -> str:
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
        f'<div class="hero" style="background-image:url(\'{photo_uri}\')"></div>'
        if photo_uri else '<div class="hero hero-empty"></div>'
    )

    # Bouton "Website" : c'est LA douleur. S'il n'a pas de site → slot manquant/grisé.
    website_btn = (
        '<div class="action website-ok"><div class="ic">🌐</div><div>Website</div></div>'
        if has_website else
        '<div class="action website-missing"><div class="ic">＋</div><div>Website</div></div>'
    )

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; }}
  html,body {{ width:1080px; height:1920px; background:#fff;
    font-family:Roboto,Arial,Helvetica,sans-serif; color:#202124; }}
  .hero {{ width:1080px; height:760px; background-size:cover; background-position:center; }}
  .hero-empty {{ background:linear-gradient(135deg,#e8eaed,#dadce0); }}
  .body {{ padding:48px 56px; }}
  .name {{ font-size:64px; font-weight:500; letter-spacing:-.5px; }}
  .ratingrow {{ display:flex; align-items:center; gap:16px; margin-top:20px; font-size:34px; color:#5f6368; }}
  .rating-num {{ color:#202124; font-weight:500; }}
  .stars {{ position:relative; display:inline-block; font-size:38px; line-height:1; }}
  .stars-bg {{ color:#dadce0; letter-spacing:4px; }}
  .stars-fg {{ color:#fbbc04; letter-spacing:4px; position:absolute; left:0; top:0;
    overflow:hidden; white-space:nowrap; }}
  .meta {{ margin-top:18px; font-size:34px; color:#5f6368; }}
  .meta .open {{ color:#188038; font-weight:500; }}
  .meta .closed {{ color:#d93025; font-weight:500; }}
  .actions {{ display:flex; gap:28px; margin:56px 0 40px; }}
  .action {{ flex:1; text-align:center; color:#1a73e8; font-size:28px; }}
  .action .ic {{ width:108px; height:108px; margin:0 auto 14px; border-radius:50%;
    border:1px solid #dadce0; display:flex; align-items:center; justify-content:center;
    font-size:46px; }}
  .website-missing {{ color:#d93025; }}
  .website-missing .ic {{ border:2px dashed #d93025; color:#d93025; background:#fce8e6; }}
  .rows {{ border-top:1px solid #ebebeb; }}
  .row {{ display:flex; align-items:flex-start; gap:30px; padding:34px 0;
    border-bottom:1px solid #ebebeb; font-size:34px; color:#3c4043; }}
  .row .ic {{ width:44px; color:#5f6368; flex:none; text-align:center; }}
</style></head><body>
  {hero}
  <div class="body">
    <div class="name">{name}</div>
    <div class="ratingrow">
      <span class="rating-num">{rating_str}</span>{stars}
      <span>{count_str}</span>
    </div>
    <div class="meta">{category}{(' · <span class="' + ('open' if open_now else 'closed') + '">' + status + '</span>') if status else ''}</div>
    <div class="actions">
      <div class="action"><div class="ic">🧭</div><div>Directions</div></div>
      <div class="action"><div class="ic">📞</div><div>Call</div></div>
      <div class="action"><div class="ic">🔖</div><div>Save</div></div>
      {website_btn}
    </div>
    <div class="rows">
      {f'<div class="row"><div class="ic">📍</div><div>{address}</div></div>' if address else ''}
      {f'<div class="row"><div class="ic">📞</div><div>{phone}</div></div>' if phone else ''}
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
    html = build_html(place, photo)

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
