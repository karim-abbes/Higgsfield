#!/usr/bin/env python3
"""
Screenshot d'un site EN LIGNE en 1080×1920 (9:16) — le "après" du reveal makeover.

V1 Bunua = site généré manuellement sur bunua.com → on récupère l'URL live → on la
capture ici. (V2 = API Bunua à construire.) L'URL sert aussi de PREUVE live au CTA.

⚠️ Réseau requis vers le site → lancer EN LOCAL (le container restreint bloque).

Usage :
    python3 scripts/screenshot_site.py "https://bunua.com/austin-plumbing-drain-pros"
    python3 scripts/screenshot_site.py "<url>" --full-page --out out/images/bunua_site.png
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import _chromium_executable  # noqa: E402  (fallback env restreint)


def main() -> int:
    ap = argparse.ArgumentParser(description="Screenshot 1080×1920 d'un site en ligne.")
    ap.add_argument("url", help="URL du site (ex: la page Bunua générée)")
    ap.add_argument("--out", default="out/images/bunua_site.png")
    ap.add_argument("--full-page", action="store_true",
                    help="Capture toute la page (sinon juste l'écran 1080×1920 = above the fold)")
    ap.add_argument("--wait", type=float, default=2.5,
                    help="Secondes d'attente après chargement (animations/lazy-load)")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    exe = _chromium_executable()

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920},
                                device_scale_factor=1)
        print(f"🌐 Chargement : {args.url}")
        page.goto(args.url, wait_until="networkidle", timeout=60000)
        time.sleep(args.wait)
        page.screenshot(path=args.out, full_page=args.full_page)
        browser.close()

    print(f"✅ Screenshot → {args.out}"
          + ("  (pleine page)" if args.full_page else "  (1080×1920 above-the-fold)"))
    print("➡️ C'est le END_IMAGE de la transition (fiche → site).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
