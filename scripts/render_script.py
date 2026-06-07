#!/usr/bin/env python3
"""
Génère le SCRIPT d'un épisode du Makeover Reveal Show à partir d'une fiche Google.

Gabarit unique (brief/makeover-episode.md) → trous {name} {trade} {city} {rating}
{reviews} {url} remplis depuis Places. Déterministe, gratuit, scalable à l'infini.

Réutilise la récup Places de render_google_card.py → carte ET script parlent du
MÊME commerce avec les MÊMES chiffres, garantis cohérents.

Sortie :
  - JSON structuré (contrat machine, consommé par le TTS + le montage)
  - aperçu lisible à l'écran

Usage :
    python3 scripts/render_script.py "Plombier Sevran BDS"
    python3 scripts/render_script.py "Joe's Plumbing Austin" --hook B
    # sortie : out/scripts/<slug>.script.json  (override avec --out)

⚠️ Données PUBLIQUES. Commerce = héros, jamais moqué. L'avatar parle AU NOM de
Bunua (« chez Bunua on lui a refait son site »), jamais « je l'ai construit ».
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Réutilise la logique Places déjà testée (même dossier).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import api_key, search_place  # noqa: E402

# Débit voix off énergique ≈ 2.6 mots/s → sert à estimer la durée par beat.
WORDS_PER_SEC = 2.6

# ───────────────────────── Gabarits par langue ─────────────────────────
# Architecture multilingue : seul "en" est rempli pour l'instant ; ajouter
# une clé (ex: "fr") suffit pour une nouvelle langue, zéro autre changement.
TEMPLATES = {
    "en": {
        # 4 hooks à A/B tester (beat 1). "A" nécessite des avis (fallback sinon).
        "hooks": {
            "A": "This {trade} has a {rating}-star rating from {reviews} reviews… and no website.",
            "B": "We're giving local {trade}s a free website they never asked for. Today: {name}.",
            "C": "If you own a {trade} and THIS is your Google page, we need to talk.",
            "D": "Can we build {name} a real website in sixty seconds? Watch.",
        },
        "stakes": "Every customer who Googles {name} hits a dead end. That's calls walking straight out the door.",
        "setup":  "So at Bunua, we built them one. Watch this.",
        "reveal": "Same reviews. Same photos. Pulled straight from Google — and turned into a real website.",
        "kicker": "And that? A giant Call button. It took one search.",
        "cta":    "If this is your business, it's already online — link's in bio. Free to try.",
    },
}

# Métadonnées des beats : ordre, qui parle, repères de montage. Le texte vient
# du gabarit ci-dessus. (beat hook traité à part pour la rotation de variante.)
BEAT_ORDER = [
    ("stakes", "host_oncam", ["card_hold", "overlay:arrow@website", "sub:burn"]),
    ("setup",  "host_oncam", ["host_oncam", "transition:start", "sub:burn"]),
    ("reveal", "voiceover",  ["transition:card_to_site", "scroll:hero,reviews,photos,call", "sub:burn"]),
    ("kicker", "voiceover",  ["zoom:call_button", "tap:call", "sub:burn"]),
    ("cta",    "host_oncam", ["host_oncam", "screen_text:{url}", "sub:burn"]),
]
HOOK_CUES = ["card_in", "zoom:website_area", "overlay:red_circle@website", "sub:burn"]


def est_duration(text: str) -> float:
    """Durée parlée estimée (s), plancher 1.8s pour les répliques courtes."""
    words = len(text.split())
    return round(max(1.8, words / WORDS_PER_SEC), 1)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "business"


def build_slots(place: dict) -> dict:
    """Extrait les slots depuis l'objet Places (mêmes champs que la carte)."""
    name = (place.get("displayName") or {}).get("text", "this business")
    trade = (place.get("primaryTypeDisplayName") or {}).get("text", "business").lower()
    rating = place.get("rating")
    count = place.get("userRatingCount")
    # Ville : avant-dernier segment de l'adresse formatée ("…, Sevran, France").
    parts = [p.strip() for p in (place.get("formattedAddress") or "").split(",") if p.strip()]
    city = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")
    slug = slugify(name)
    return {
        "name": name,
        "trade": trade,
        "city": city,
        "rating": f"{rating:.1f}" if isinstance(rating, (int, float)) else None,
        "reviews": f"{count:,}" if isinstance(count, int) else None,
        "url": f"bunua.com/{slug}",
        "slug": slug,
        "has_website": bool(place.get("websiteUri")),
    }


def choose_hook(requested: str, slots: dict) -> str:
    """'auto' = A si avis dispo, sinon D. Fallback si A demandé sans avis."""
    if requested == "auto":
        return "A" if slots["reviews"] else "D"
    if requested == "A" and not slots["reviews"]:
        print("  ⚠️ Hook A nécessite des avis (absents) → repli sur hook D.")
        return "D"
    return requested


def build_script(place: dict, lang: str, hook_key: str) -> dict:
    if lang not in TEMPLATES:
        sys.exit(f"❌ Langue {lang!r} non disponible. Dispo : {', '.join(TEMPLATES)}.")
    tpl = TEMPLATES[lang]
    slots = build_slots(place)
    hook_key = choose_hook(hook_key, slots)

    # Remplit un gabarit ; signale tout slot manquant plutôt que d'écrire "None".
    def fill(text: str) -> str:
        try:
            return text.format(**{k: ("" if v is None else v) for k, v in slots.items()})
        except KeyError as e:  # slot inconnu dans un gabarit
            sys.exit(f"❌ Slot inconnu dans le gabarit : {e}")

    beats = [{
        "beat": "hook",
        "type": "host_oncam",
        "text": fill(tpl["hooks"][hook_key]),
        "cues": HOOK_CUES,
    }]
    for beat, typ, cues in BEAT_ORDER:
        beats.append({
            "beat": beat,
            "type": typ,
            "text": fill(tpl[beat]),
            "cues": [c.format(**slots) for c in cues],
        })

    for b in beats:
        b["duration_s"] = est_duration(b["text"])

    total = round(sum(b["duration_s"] for b in beats), 1)
    return {
        "business": slots["name"],
        "lang": lang,
        "hook_variant": hook_key,
        "url": slots["url"],
        "has_website": slots["has_website"],
        "total_duration_s": total,
        "beats": beats,
    }


def print_preview(script: dict) -> None:
    print(f"\n🎬 {script['business']}  ·  hook {script['hook_variant']}  ·  "
          f"~{script['total_duration_s']}s  ·  {script['lang']}")
    if script["has_website"]:
        print("  ⚠️ Ce commerce A DÉJÀ un site → mauvaise cible démo (pas de douleur).")
    if not 25 <= script["total_duration_s"] <= 37:
        print(f"  ⚠️ Durée hors cible 30-35s ({script['total_duration_s']}s).")
    print("  " + "─" * 60)
    for b in script["beats"]:
        tag = "🎙️VO" if b["type"] == "voiceover" else "👤CAM"
        print(f"  [{b['beat']:<6}] {tag} {b['duration_s']:>4}s  {b['text']}")
    print("  " + "─" * 60)


def main() -> int:
    ap = argparse.ArgumentParser(description="Génère le script d'un épisode Makeover.")
    ap.add_argument("query", nargs="?", help="Nom du commerce à chercher")
    ap.add_argument("--place-id", help="Place ID Google (au lieu du nom)")
    ap.add_argument("--hook", choices=["auto", "A", "B", "C", "D"], default="auto",
                    help="Variante de hook (auto=A si avis dispo, sinon D)")
    ap.add_argument("--lang", default="en", help="Langue (en seule pour l'instant)")
    ap.add_argument("--out", help="Chemin JSON de sortie (défaut out/scripts/<slug>.script.json)")
    args = ap.parse_args()

    if not args.query and not args.place_id:
        ap.error("Fournis un nom de commerce ou --place-id.")

    key = api_key()
    query = args.query or args.place_id
    print(f"🔎 Places: {query!r}")
    place = search_place(query, key)

    script = build_script(place, args.lang, args.hook)
    print_preview(script)

    out = args.out or os.path.join("out", "scripts", f"{slugify(script['business'])}.script.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Script → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
