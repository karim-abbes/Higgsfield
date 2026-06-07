# Brief — Script-type Makeover Reveal Show

> Gabarit unique, rempli automatiquement par épisode avec les données Google Places.
> Un seul template → personnalisé à l'infini. 9:16 vertical, EN-US, organique (TikTok/IG/FB).

## Décisions verrouillées
- **Hôte** : **avatar IA récurrent** (persona de marque), visage à la caméra au **hook** + **CTA**, **voix off** pendant le reveal plein écran.
  - Parle **au nom de Bunua** (« chez Bunua, on lui a refait son site »), **jamais** « je l'ai construit de mes mains » → honnêteté, pas de retour de bâton « c'est une IA ».
  - La confiance ne repose pas sur un vrai visage → **l'URL live réelle devient la preuve centrale** (voir CTA).
- **Ton** : **énergique / hype, mais positif** (commerce = héros, jamais moqué).
- **Durée** : **~30-35 s**.
- **Offre** : « **gratuit à essayer / à réclamer** » — jamais « gratuit à vie » (promesse intenable). Mécanisme = le site est **déjà en ligne**, l'action = venir le réclamer (zéro engagement-bait).
- **URL réelle affichée** au reveal + CTA (`bunua.com/{slug}`), site **généré et en ligne AVANT de poster**. Prévoir un « c'est mon commerce, retirez-le ».

## Slots auto-remplis (depuis Places API)
`{name}` · `{trade}` (ex: plumber) · `{city}` · `{rating}` · `{reviews}` · `{phone}`

---

## Beat sheet (~33 s)

| # | Beat | Durée | Visuel + montage | Voix |
|---|---|---|---|---|
| 1 | **HOOK** | 0–3s | Hôte caméra → cut sur la carte Google, **zoom + cercle rouge** sur le bouton site absent | *"This `{trade}` has `{rating}` stars and `{reviews}` reviews… and no website."* |
| 2 | **STAKES** | 3–8s | Carte à l'écran, flèche/cercle animé sur le vide | *"Every single customer who Googles `{name}` hits a dead end. That's calls walking out the door."* |
| 3 | **SETUP** | 8–11s | Retour hôte 1s, puis amorce transition | *"So I built `{name}` a website. In 60 seconds. Watch."* |
| 4 | **REVEAL** ⭐ | 11–25s | **Transition** carte→site Bunua live ; scroll : hero, avis, photos, bouton Call (voix off, plein écran) | VO: *"Same reviews. Same photos. Pulled straight from Google — now it's a real site."* |
| 5 | **KICKER** | 25–30s | Gros plan mobile, tap sur **Call** | VO: *"And that — a giant Call button. Took me one search."* |
| 6 | **CTA** | 30–33s | Hôte caméra + texte écran `bunua.com` | *"If this is your business — link's in my bio. It's free to try."* |

⭐ Le **reveal** est le shoot de dopamine : tout le reste sert à y amener. Ne jamais le compresser sous 12 s.

## Phrase-franchise (transforme les vidéos en *série* suivie)
À placer en surimpression / en intro vocale, **identique chaque épisode** :
> **"Another business, another 60-second glow-up."**
(à tester vs 2-3 variantes — voir ci-dessous)

## Hooks à A/B tester (beat 1)
- **A — Contraste chiffré** : *"`{reviews}` five-star reviews… and zero website."*
- **B — Don gratuit** : *"I'm giving local `{trade}`s a free website they never asked for. Today: `{name}`."*
- **C — POV proprio** : *"If you own a `{trade}` and THIS is your Google page, we need to talk."*
- **D — Défi** : *"Can I build `{name}` a real website in 60 seconds? Go."*

## Règles de production
- **Sous-titres brûlés** partout (mot-à-mot, déjà outillé via Whisper).
- **Cercle rouge** = overlay au montage (jamais dans la carte → fiche crédible).
- Hôte : **récurrent**, 1 persona, voix clonée 1× (Qwen3-TTS).
- Le **site Bunua** doit être généré et en ligne (URL récupérée) AVANT le rendu.
- Frame toujours le commerce en **héros** : « voici ce qu'il mérite », pas « il est nul ».

## CTA / conversion
- Lien en **bio** → bunua.com.
- Caption : 1 ligne hook + `{city}`/`{trade}` + hashtags secteur + "free to try".
- Flywheel : le commerce vedette → contact outbound (« on t'a fait un site, viens le chercher »).

## Mapping pipeline (ce que le générateur de script consomme/produit)
1. Entrée : objet Place (Places API) → slots.
2. Sort : script segmenté par beat (texte hôte vs voix off) + cues montage.
3. → TTS (voix off + lignes hôte) → clips (hook/CTA caméra + reveal) → montage + sous-titres.
