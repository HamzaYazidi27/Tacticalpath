# autoedit : vidéo brute → Short monté, sans intervention

Vous donnez une vidéo non montée. `autoedit` l'analyse, choisit le meilleur passage, monte, sous-titre, étalonne et mixe, puis livre le Short final avec un rapport de contrôle qualité. Il applique automatiquement le style **Center-Punch** mesuré sur @Tacticalpath (voir `docs/`).

```
vidéo brute ─► transcription mot à mot ─► choix de la meilleure histoire (30–60 s)
            ─► suppression des silences / « euh » ─► plan de montage (≥ 50 coupes/min)
            ─► B-roll calé sur chaque mot-clé ─► recadrage 9:16 sur le visage + punch-ins
            ─► sous-titres verts centrés + marque ─► étalonnage + netteté
            ─► voix traitée + musique (ducking) + whooshes ─► −14 LUFS ─► MP4 1080×1920
            ─► contrôle qualité automatique (rapport PASS / WARN)
```

## Deux modes, choisis automatiquement

| Votre vidéo | Mode | Ce qui se passe |
|---|---|---|
| **Quelqu'un parle** (podcast, interview, face caméra, vlog) | Podcast-clip | Sélection de la meilleure histoire, coupes des silences, B-roll sur les mots, sous-titres mot à mot |
| **Pas de parole** (rushes, stock, paysages) | Montage | Meilleurs moments (netteté, mouvement), rythme ~1 s, accroche en premier, musique ou son d'ambiance, texte optionnel (`--text`) |

## Installation (une seule fois)

Il faut Python 3.10+ et ffmpeg avec libass. Ensuite :

```bash
./install.sh
```

Le script crée `.venv`, installe les dépendances, télécharge le modèle de transcription et prépare les dossiers `inbox/ outbox/ broll/ music/`.

Avec Docker (non testé ici, Docker n'était pas disponible dans l'environnement de développement) :

```bash
docker build -t autoedit .
```

## Utilisation

**Une vidéo :**

```bash
. .venv/bin/activate && python -m autoedit ma_video.mp4
```

**Pilote automatique** (déposez des vidéos dans `inbox/`, les Shorts apparaissent dans `outbox/`) :

```bash
. .venv/bin/activate && python -m autoedit --watch inbox --out outbox
```

**Plusieurs Shorts d'un long podcast, avec votre marque :**

```bash
python -m autoedit episode.mp4 --count 3 --brand "WILD|FRAME"
```

Le `|` indique où la marque change de couleur : `WILD` en blanc, `FRAME` en vert.

## Pour un résultat complet : les sources de B-roll

Le style repose à 65–77 % sur du B-roll. Le système en trouve automatiquement, dans cet ordre :

1. **Votre dossier `broll/`** (`--broll`). Nommez les fichiers par sujet, par exemple `requin_blanc_ocean.mp4` ou `lion savane.jpg`, ou ajoutez un `.txt` du même nom avec des mots-clés.
2. **Pexels**, gratuit : créez une clé sur pexels.com/api, puis lancez `export PEXELS_API_KEY=...`. Chaque mot-clé est alors illustré automatiquement, et les crédits sont écrits dans `*_credits.txt`.
3. **Pixabay**, gratuit : `export PIXABAY_API_KEY=...`.
4. **Plans de coupe trouvés dans votre propre vidéo** : les passages sans visage.

Sans aucune source, le Short reste monté (punch-ins, sous-titres, rythme), mais le rapport signalera `b-roll share` en ⚠️.

**Musique :** mettez des pistes libres de droits dans `music/`. Le système en choisit une, la règle à environ −19 dB sous la voix et la baisse automatiquement quand la personne parle.

**Optionnel, Claude :** avec `export ANTHROPIC_API_KEY=...`, Claude choisit l'histoire la plus forte, écrit le titre et formule les recherches B-roll en anglais (« octopus squeezing through gap »). Sans clé, une sélection heuristique est utilisée : accroche, chute, densité de mots visuels, exclusion des intros et outros.

## Ce que vous recevez (dans `outbox/<nom>/`)

| Fichier | Contenu |
|---|---|
| `<nom>_short1.mp4` | Le Short final : 1080×1920, 30 fps, H.264, AAC 320 k, −14 LUFS |
| `<nom>_short1_cover.jpg` | Image de couverture avec sous-titre |
| `<nom>_short1.srt` | Sous-titres (pour les traductions et l'accessibilité) |
| `<nom>_short1_report.md` / `_qc.json` | Contrôle qualité : durée, coupes/min, part de B-roll, position des sous-titres, loudness, true peak |
| `<nom>_short1_edl.json` | Le plan de montage complet, plan par plan, pour retoucher à la main si besoin |
| `<nom>_short1_credits.txt` | Crédits des B-roll téléchargés |

## Réglages

Copiez `autoedit.config.example.json` vers `autoedit.config.json` pour régler :
- la marque ;
- les durées (`min_dur`, `max_dur`, `target_dur`) ;
- la langue ;
- le modèle Whisper (`small` par défaut, `medium` pour plus de précision) ;
- les dossiers B-roll et musique ;
- l'intensité de la LUT et de la netteté ;
- le niveau de la musique.

Les options de la ligne de commande sont prioritaires sur le fichier. `python -m autoedit --help` liste tout.

## Vérifié dans ce dépôt

- **Tests unitaires :** `python3 -m unittest discover -s tests` passe (7 tests). Ils couvrent la sélection d'histoire, les invariants du montage, et l'analyse des réponses Pexels et Claude (simulées).
- **Test de bout en bout :** `python3 tests/make_fixtures.py` génère un « podcast brut » de 107 s (photo NASA du domaine public, voix de synthèse avec « um » et silences, intro et outro inutiles). Sur 4 CPU, le pipeline produit le Short en ~2,5 min.
  - **Sélection :** il a choisi seul l'histoire de 17,2 s à 67,4 s (« Did you know a cat once flew to space? »), sans l'intro ni l'outro.
  - **Contrôle qualité :** 56 coupes/min, sous-titres à 50,2 % de hauteur, −14,3 LUFS, true peak −1,9 dBTP.
  - **Seul avertissement :** la part de B-roll, à 29 %, parce que la bibliothèque de test ne contient que 10 fichiers.

  Aperçu : [`demo/autoedit_example_short.mp4`](demo/autoedit_example_short.mp4).
- **Mode montage :** QC PASS sur 30 s de rushes sans parole.
- **Mode surveillé :** une vidéo déposée dans `inbox/` est traitée puis déplacée dans `inbox/_done/`.

## Limites

- **Pertinence du B-roll :** la correspondance se fait par mots-clés. Elle est bonne avec Pexels ou une bibliothèque bien nommée, et littérale plutôt que créative.
- **Cadrage :** le visage est détecté par OpenCV (Haar). Avec plusieurs personnes à l'écran, le cadre suit le plus grand visage, pas forcément celui qui parle. Si aucun visage n'est trouvé, le cadrage est centré.
- **Langues :** la transcription gère la plupart des langues. Les listes de mots-clés et d'accroches sont surtout en anglais et en français. Pour d'autres langues, Claude (optionnel) fait mieux.
- **Rien n'est inventé :** pas de voix off, pas de musique générée. Le son vient de votre vidéo, de `music/` et d'effets synthétisés (whoosh, impact).
- **Droits :** utilisez des vidéos que vous possédez ou que vous avez le droit de monter.
