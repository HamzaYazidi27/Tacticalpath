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

## B-roll réel en VIDÉO, qui montre exactement ce qui est dit

Par défaut, le B-roll est **uniquement en vidéo** ; les photos n'arrivent que sur demande (`"allow_photos": true`). Pour chaque mot ou expression (« glass of water », « baby powder »…), le système essaie ces sources dans l'ordre (modifiable avec `--sources`) :

| Ordre | Source | Contenu | Licence |
|---|---|---|---|
| 1 | `library` : votre dossier `broll/` | Vos clips | Les vôtres |
| 2 | `urls` : vos liens (`--broll-urls liens.txt`) | **Vidéos YouTube, TikTok, Instagram…** que vous possédez ou avez le droit d'utiliser | Votre responsabilité |
| 3 | `youtube_cc` | **Vidéos YouTube sous licence Creative Commons** (licence revérifiée vidéo par vidéo) | CC BY |
| 4 | `pexels`, `pixabay` (clé gratuite) | Vidéos stock réelles | Licence Pexels / Pixabay |
| 5 | `mixkit` (sans clé) | Vidéos stock réelles en HD | Mixkit Free License |
| 6 | `wikimedia` | Vidéos de Wikimedia Commons | CC0, domaine public, CC BY |
| option | `openverse` (photos), `archive` | Photos réelles / films anciens | CC0, PDM, CC BY |

**Pourquoi pas « n'importe quelle vidéo YouTube ou TikTok » :** un extrait court n'est pas protégé. Content ID détecte des extraits de 1 à 2 secondes, et c'est la cause des strikes et des démonétisations sur les chaînes qui le font. TikTok n'a pas de licence de réutilisation : utilisez vos liens, avec l'accord du créateur.

### Fluidité « Tacticalpath »
- **Un seul plan continu par B-roll :** le système détecte les coupes à l'intérieur du clip source (compilations, montages) et ne garde que le plan qui montre le mot. Jamais de coupe parasite au milieu d'un B-roll.
- **Mouvement naturel conservé :** quand le plan est statique, il reçoit une poussée lente calculée sur une image sur-échantillonnée 2×, donc au sous-pixel, sans tremblement.
- **Recadrage 9:16 intelligent :** CLIP teste plusieurs fenêtres horizontales et garde celle où le sujet est visible (le ballon, le verre), pas simplement le centre.
- **Calage au mot :** l'image arrive 2 images avant le mot. Si le mot est encore prononcé, les B-roll s'enchaînent directement. Un B-roll n'est jamais décalé sur un autre mot.
- **Plutôt rien que faux :**
  - pour une expression, le titre du clip doit la contenir, ou la correspondance visuelle doit être quasi certaine ;
  - un mot inclus dans une expression n'est pas cherché seul ;
  - sans bonne vidéo, le speaker reste à l'écran.
- **Filtres de contenu :** les titres explicites et les images plus « suggestives » que le mot cherché sont exclus (calibré sur de vraies images stock), ainsi que les visages d'inconnus pour des mots sans rapport.

**Comment le système garantit que l'image montre le mot (vision CLIP, locale et gratuite) :**
1. Pour une vidéo YouTube, les sous-titres du clip indiquent à quelle seconde le mot y est prononcé.
2. CLIP regarde les images autour de ce moment et ne garde que celles qui **montrent** vraiment le mot. Il les compare à « une personne qui parle », « du texte à l'écran », « un écran noir »…
3. Seules les ~4 secondes qui correspondent sont téléchargées en haute qualité, puis calées au mot près dans le montage.

Votre bibliothèque locale est indexée de la même façon : la recherche se fait par le **contenu de l'image**, plus seulement par le nom du fichier.

**Ce qui est exclu volontairement :**
- **Les vidéos YouTube ou TikTok sans licence de réutilisation** (« Standard YouTube License », TikTok en général). Les reprendre automatiquement expose à des strikes copyright, à la démonétisation et à la suppression de la chaîne. Si un créateur vous donne son accord, ajoutez ses liens dans `--broll-urls`.
- **Les licences NC** (non commercial, incompatible avec une chaîne monétisée), **ND** (pas de modification) et **SA** (elle obligerait à mettre tout votre Short sous la même licence).
- **Les photos centrées sur le visage d'un inconnu**, quand le mot ne parle pas de personnes (droit à l'image).

Tous les crédits sont écrits dans `*_credits.txt` : copiez-les dans la description de la vidéo, la licence CC BY l'exige.

**Installation de la vision** (incluse dans `install.sh`) : `pip install -r requirements-vision.txt` (~800 Mo, une fois). Sans elle, seules `library`, `urls`, `pexels` et `pixabay` sont utilisées, avec une correspondance par nom de fichier.

**Musique :** mettez des pistes libres de droits dans `music/`. Le système en choisit une, la règle à environ −19 dB sous la voix et la baisse automatiquement quand la personne parle.

**Optionnel, Claude :** avec `export ANTHROPIC_API_KEY=...`, Claude choisit l'histoire la plus forte, écrit le titre et formule des recherches B-roll plus précises.

## Ce que vous recevez (dans `outbox/<nom>/`)

| Fichier | Contenu |
|---|---|
| `<nom>_short1.mp4` | Le Short final : 1080×1920, 30 fps, H.264, AAC 320 k, −14 LUFS |
| `<nom>_short1_cover.jpg` | Image de couverture avec sous-titre |
| `<nom>_short1.srt` | Sous-titres (pour les traductions et l'accessibilité) |
| `<nom>_short1_report.md` / `_qc.json` | Contrôle qualité : durée, coupes/min, part de B-roll, position des sous-titres, loudness, true peak |
| `<nom>_short1_edl.json` | Le plan de montage complet, plan par plan, pour retoucher à la main si besoin |
| `<nom>_short1_credits.txt` | Crédits et licences de chaque B-roll, prêts à coller dans la description |

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

### Test réel sur une vidéo fournie (14,6 s, « Why Fahrenheit makes more sense than Celsius »)

Source Openverse, vision CLIP active, aucune intervention.
- **QC PASS :** 59 % de B-roll, 50 coupes/min, −14,0 LUFS.
- **Plans choisis :** verre d'eau sur « glass of water », mer sur « sea level », affichage de température sur « temperature outside », balles sur « balls », homme en sueur de dos sur « sweaty outside », short sur « shorts », talc Johnson's sur « baby powder », derrière de babouin sur « monkey butt ».
- **Plateformes non testables ici :** YouTube et Wikimedia bloquent l'IP partagée du serveur cloud (anti-bot / 429) ; les deux fonctionnent depuis une connexion normale.

## Limites

- **Pertinence du B-roll :** la correspondance se fait par mots-clés. Elle est bonne avec Pexels ou une bibliothèque bien nommée, et littérale plutôt que créative.
- **Cadrage :** le visage est détecté par OpenCV (Haar). Avec plusieurs personnes à l'écran, le cadre suit le plus grand visage, pas forcément celui qui parle. Si aucun visage n'est trouvé, le cadrage est centré.
- **Langues :** la transcription gère la plupart des langues. Les listes de mots-clés et d'accroches sont surtout en anglais et en français. Pour d'autres langues, Claude (optionnel) fait mieux.
- **Rien n'est inventé :** pas de voix off, pas de musique générée. Le son vient de votre vidéo, de `music/` et d'effets synthétisés (whoosh, impact).
- **Droits :** utilisez des vidéos que vous possédez ou que vous avez le droit de monter.
