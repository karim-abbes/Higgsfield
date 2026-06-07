# Stratégie — Usine à vidéos UGC Bunua

> Document vivant. Décisions verrouillées + architecture cible. Mis à jour au fil du projet.

## Vision

Bunua transforme une fiche Google Business en site web pro automatiquement.
On construit une **machine à contenu vidéo** qui sert à la fois l'acquisition et la marque.

## Décisions verrouillées

| Sujet | Décision | Raison |
|---|---|---|
| **Secteur beachhead** | Artisans / services techniques (plombier, élec, garage, BTP) — prototyper sur **1 métier** d'abord | Sans site, 100% pilotés par appels, forte valeur/appel, urgence = intention max |
| **Marché / langue** | Anglais US | Marché cible actuel |
| **Format principal** | 🎬 **Makeover Reveal Show** (hôte récurrent transforme un commerce : fiche Google → site Bunua en 60s) | Viral natif + démo produit + bâtit l'influenceur + réutilise le pipeline |
| **Format secondaire (fork)** | Testimonial par secteur (l'avatar-commerçant parle) — **conservé** comme variante | Garde l'option outbound 1:1 ; tag de restauration `v1-testimonial` |
| **Avatar** | **1-2 hôtes récurrents** ultra-travaillés (pas une librairie par secteur) | Le makeover a besoin d'une star de chaîne, pas de 15 visages |
| **Voix** | Clonée 1× par hôte (Qwen3-TTS), mise en cache | Cohérence + coût marginal nul |
| **Device "pas de site"** | Bouton Website **absent** (fiche 100% crédible) ; cercle rouge ajouté en **overlay au montage**, pas dans la carte | La crédibilité « c'est MA fiche » prime ; on dirige l'attention sans falsifier l'UI |
| **Commerces** | **Réels sans accord**, mis en héros → site offert gratuit ensuite (+ options payantes) | Authenticité + flywheel organique→outbound |
| **Distribution** | **Organique** (TikTok/IG/FB) via viralité + suivi des perfs | Vision fondateur ; coût marginal nul si ça perce |
| **Diffusion** | Semi-auto : file de validation → publication (manuelle/planificateur) | Risque marque/légal ; qualité organique |

## Le flywheel

```
Vidéo makeover (commerce réel, héros)
   → postée en organique (TikTok/IG/FB)
   → vues / partages / followers  ──┐
   → artisans s'identifient          │ boucle d'optimisation
   → lien bio → bunua.com → signup   │ (track ce qui performe)
   → + le commerce vedette : on lui OFFRE son site gratuit
        → il devient client + ambassadeur (upsell options)
```

## Architecture du pipeline (Makeover Show)

```
CSV de commerces (name / place_id, US, métier ciblé)
   │
   ▼
[1] ENRICHISSEMENT — Google Places API (clé dispo)
     → nom, catégorie, note, étoiles, nb avis, photos, tél, adresse
   │
   ▼
[2] CARTE PROFIL GOOGLE — rendue par nous (HTML→image)
     • fidèle à l'UI Maps (identification du spectateur)
     • device clé : bouton "Site web" ABSENT/grisé = la douleur visualisée
   │
   ▼
[3] SITE BUNUA
     • V1 : généré manuellement → URL récupérée via sitemap.xml → screenshot Playwright
     • V2 : API Bunua (à construire)
   │
   ▼
[4] SCRIPT D'ÉPISODE — hôte récurrent, personnalisé (nom/métier du commerce)
     intro (hook) → reveal (fiche→site) → CTA
   │
   ▼
[5] GÉNÉRATION (couche provider abstraite : fal.ai aujourd'hui, Wan local/4090 demain)
     • hôte parlant : Kling (intro + CTA)
     • narration : TTS voix clonée de l'hôte
     • transition fiche→site : Kling start/end (notre techno actuelle)
   │
   ▼
[6] MONTAGE — concat + sous-titres auto (Whisper)
   │
   ▼
[7] DESCRIPTIONS — TikTok/IG/FB + hashtags secteur + CTA lien bio
   │
   ▼
[8] FILE DE VALIDATION — vidéo + caption + métadonnées → approbation humaine
   │
   ▼
[9] TRACKING — perfs par vidéo → boucle d'optimisation (+ Virality Predictor en pré-filtre)
```

## Principes d'ingénierie

- **Idempotent + reprenable** : reprise sans re-payer les commerces déjà traités.
- **Cache agressif** : hôtes/voix + artefacts par commerce.
- **Couche génération abstraite** : swap cloud→local sans réécrire le pipeline.
- **Manifest** (SQLite/JSON) : état + coût par commerce.
- **Fork préservé** : le pipeline testimonial reste utilisable (tag `v1-testimonial`).

## Goulot d'étranglement réel

Pas la production vidéo (maîtrisée) mais :
1. **L'obtention des URLs de sites Bunua** (manuel V1 → sitemap.xml → API V2).
2. **La viralité** (variance) → résolue par volume + itération + tracking.

## Phases de build

- **Phase 0 (fait)** : pipeline testimonial bout-en-bout (avatar, clips, voix clonée, transition, sous-titres auto, montage).
- **Phase 1** : hôte récurrent + script makeover + carte profil Google (renderer) + enrichissement Places.
- **Phase 2** : orchestrateur CSV (batch, idempotent, manifest, coûts) + file de validation. **→ Dockerfile ici** (fige ffmpeg + playwright + whisper) pour déploiement VPS. Pas avant : friction inutile en phase proto.
- **Phase 3** : tracking perfs + boucle d'optimisation + flywheel outbound (offre site gratuit).
- **Phase 4** : scaling coût (Wan local sur 4090 louée) + élévation hôte en influenceur.

## Risques & garde-fous

| Risque | Garde-fou |
|---|---|
| Commerce vexé (réel sans accord) | Héros jamais moqué · données publiques · takedown · site offert |
| Virality aléatoire | Volume + tests + Virality Predictor + double sur les gagnants |
| Coût cloud à l'échelle | Couche provider → bascule Wan local quand volume |
| Qualité (lip-sync, halluc. UI) | Carte profil rendue par nous (pas screenshot Google) · validation humaine |
| Voix incohérente | TTS Qwen3 voix clonée (jamais le voice_id Kling sur image-to-video) |
