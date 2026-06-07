# CLAUDE.md — règles du projet

## Communication / commandes shell
- **NE JAMAIS inclure de commentaires `#` dans les blocs de commandes shell** donnés à
  l'utilisateur. Son shell est **zsh interactif** : `#` n'y est pas un commentaire →
  ça casse (`quote>`, `parse error`). Donner des **commandes pures, une par ligne**,
  sans aucun commentaire ni texte explicatif dans le bloc.
- Les explications vont **hors** du bloc de code, jamais dedans.

## Contexte projet
Usine à vidéos UGC « Makeover Reveal Show » pour Bunua. Voir `docs/STRATEGY.md`,
`brief/makeover-episode.md`, et les skills `fal-ai` / `higgsfield` / `replicate`.

- Pipeline complet : `scripts/make_episode.py "<commerce>" --bunua-url "<url>"`.
- Génération vidéo (Kling) = **fal.ai** (moins cher/rapide). Replicate = fallback.
- Voix = clonée de Kling (hook+CTA) puis TTS Qwen3. Wan S2V écarté (lip-sync KO).
- Avatar = CLI `higgsfield` (le SDK Python est cassé sur ce compte).
- Étapes réseau (Places/fal/screenshot) → **tournent en local** (container restreint).
