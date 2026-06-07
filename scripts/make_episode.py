#!/usr/bin/env python3
"""
ORCHESTRATEUR : un commerce → un épisode Makeover complet, en enchaînant toutes
les briques. Idempotent (cache : ne refait pas ce qui existe) + manifest d'état.

Le seul point manuel (tant que l'API Bunua n'existe pas) = l'URL du site Bunua,
passée en argument. Le reste est automatique.

Chaîne :
  render_script → render_google_card → screenshot_site → generate_video_fal(hook,cta)
  → clone_host_voice → render_voiceover → generate_transition_fal → assemble_episode

⚠️ Réseau (Places/fal) requis → lancer EN LOCAL. FAL_KEY + GOOGLE_MAPS_API_KEY + (REPLICATE en fallback) dans .env.

Usage :
    python3 scripts/make_episode.py "Austin Plumbing & Drain Pros" --bunua-url "https://bunua.com/..."
    python3 scripts/make_episode.py "<nom>" --bunua-url "<url>" --force   # tout regénérer
    python3 scripts/make_episode.py "<nom>" --skip-site                   # si bunua_site.png déjà prêt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

PY = sys.executable
CARD = "out/images/google_profile.png"
SITE = "out/images/bunua_site.png"
HOOK = "out/clips/hook.mp4"
CTA = "out/clips/cta.mp4"
TRANS = "out/clips/transition.mp4"
EMBED = "out/voice/host/embedding_url.txt"

# Estimations de coût (USD) pour le manifest — indicatif (cf. skills).
COST = {"hook": 0.63, "cta": 0.63, "transition": 0.63, "clone": 0.05,
        "voiceover": 0.05, "card": 0.01, "site": 0.0, "script": 0.0, "assemble": 0.0}


def sh(cmd: list[str], capture: bool = False) -> str:
    """Lance une commande, échoue fort si code ≠ 0. Renvoie stdout si capture."""
    print(f"\n$ {' '.join(cmd)}")
    if capture:
        p = subprocess.run(cmd, text=True, capture_output=True)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
    else:
        p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        sys.exit(f"❌ Étape échouée (code {p.returncode}) : {' '.join(cmd)}")
    return p.stdout if capture else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Orchestrateur : commerce → épisode complet.")
    ap.add_argument("business", help="Nom du commerce (+ ville)")
    ap.add_argument("--bunua-url", help="URL du site Bunua live (le 'après')")
    ap.add_argument("--hook", default="auto", help="Variante de hook (auto/A/B/C/D)")
    ap.add_argument("--skip-site", action="store_true", help="Ne pas re-screenshoter (bunua_site.png déjà prêt)")
    ap.add_argument("--force", action="store_true", help="Tout regénérer (ignore le cache)")
    args = ap.parse_args()

    if not args.skip_site and not args.bunua_url:
        ap.error("Fournis --bunua-url (ou --skip-site si out/images/bunua_site.png est déjà prêt).")

    t0 = time.time()
    state: dict[str, dict] = {}

    def step(name: str, output: str | None, cmd: list[str], capture: bool = False) -> str:
        """Exécute une étape avec cache (skip si output existe et pas --force)."""
        s = time.time()
        if output and os.path.exists(output) and not args.force:
            print(f"\n⏭  [{name}] {output} existe → réutilisé (cache).")
            state[name] = {"status": "cached", "sec": 0, "cost": 0.0}
            return ""
        out = sh(cmd, capture=capture)
        if output and not os.path.exists(output):
            sys.exit(f"❌ [{name}] sortie attendue absente : {output}")
        state[name] = {"status": "run", "sec": round(time.time() - s, 1), "cost": COST.get(name, 0.0)}
        return out

    # 1) Script (donne aussi le slug → chemins JSON/voix/épisode).
    out = step("script", None, [PY, "scripts/render_script.py", args.business, "--hook", args.hook], capture=True)
    m = re.search(r"out/scripts/\S+\.script\.json", out)
    if not m:
        sys.exit("❌ Impossible de retrouver le chemin du script généré.")
    script_json = m.group(0)
    slug = os.path.basename(script_json).replace(".script.json", "")
    manifest_voice = f"out/voice/{slug}/voiceover.manifest.json"
    episode = f"out/episodes/{slug}.mp4"
    print(f"\n📌 slug = {slug}")

    # 2) Carte Google (avant).
    step("card", CARD, [PY, "scripts/render_google_card.py", args.business])

    # 3) Site Bunua (après) — screenshot de l'URL live.
    if args.skip_site:
        if not os.path.exists(SITE):
            sys.exit(f"❌ --skip-site mais {SITE} absent.")
        state["site"] = {"status": "cached", "sec": 0, "cost": 0.0}
    else:
        step("site", SITE, [PY, "scripts/screenshot_site.py", args.bunua_url])

    # 4) Clips parlants hook + CTA (Kling/fal).
    step("hook", HOOK, [PY, "scripts/generate_video_fal.py", "hook", "--script", script_json])
    step("cta", CTA, [PY, "scripts/generate_video_fal.py", "cta", "--script", script_json])

    # 5) Voix de l'hôte : clonée 1× depuis hook+CTA, mise en cache (réutilisée ensuite).
    step("clone", EMBED, [PY, "scripts/clone_host_voice.py"])

    # 6) Voix off du milieu (voix clonée).
    step("voiceover", manifest_voice, [PY, "scripts/render_voiceover.py", script_json])

    # 7) Transition morph fiche→site (silencieuse).
    step("transition", TRANS, [PY, "scripts/generate_transition_fal.py", "--duration", "5"])

    # 8) Montage final + sous-titres.
    step("assemble", episode, [PY, "scripts/assemble_episode.py", script_json])

    # Manifest d'exécution.
    total_cost = round(sum(v.get("cost", 0) for v in state.values()), 2)
    run = {"business": args.business, "slug": slug, "bunua_url": args.bunua_url,
           "episode": episode, "total_sec": round(time.time() - t0, 1),
           "est_cost_usd": total_cost, "steps": state}
    os.makedirs("out/episodes", exist_ok=True)
    with open(f"out/episodes/{slug}.run.json", "w") as f:
        json.dump(run, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*56}\n✅ ÉPISODE : {episode}")
    print(f"⏱  {run['total_sec']}s  ·  💵 ~${total_cost}  ·  manifest → out/episodes/{slug}.run.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
