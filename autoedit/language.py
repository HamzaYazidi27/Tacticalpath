"""Sentences, hook scoring, visual-keyword extraction (no ML required)."""
from __future__ import annotations

import re
from collections import Counter

STOP = set("""
a about above after again against all almost also am an and any are aren't as at be because been before being below between
both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each even ever every few for from
further get gets getting got gonna had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him
himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself just kind know let's like literally look lot
made make many maybe me mean might more most much must mustn't my myself no nor not now of off on once one only or other ought our
ours ourselves out over own pretty probably really right said same say says see she she'd she'll she's should shouldn't so some
something somebody someone still such sure take than that that's the their theirs them themselves then there there's these they
they'd they'll they're they've thing things think this those though through to too totally under until up upon us very want was
wasn't way we we'd we'll we're we've well went were weren't what what's when when's where where's which while who who's whom why
why's will with won't would wouldn't yeah yes yet you you'd you'll you're you've your yours yourself yourselves actually basically
okay ok oh um uh erm hmm guy guys stuff time times going come came goes went thought told tell feel felt gonna wanna whatever
le la les un une des du de et en au aux ce cet cette ces il elle ils elles on nous vous je tu me te se mon ma mes ton ta tes son sa
ses notre nos votre vos leur leurs qui que quoi dont où est sont était être avoir a ai as avons avez ont pas ne plus pour par avec
sans sur sous dans mais ou donc or ni car si alors comme tout tous toute toutes très bien fait faire dit dire va vais vont c'est
j'ai il y ça cela ceci là voilà euh ben bah genre truc trucs chose choses vraiment juste peut être aussi même encore déjà
el la los las un una unos unas de del y en que es son por para con sin pero como muy más este esta esto eso ese esa lo le les se
""".split())

FILLERS = {"um", "uh", "erm", "hmm", "uhm", "euh", "eh", "ah", "mm", "mhm"}

HOOK_WORDS = set("""never always most rarest rare deadliest deadly dangerous worst best biggest largest smallest fastest strongest
smartest craziest crazy insane terrifying scary creepy weird strange secret nobody extinct survived impossible why how what imagine
discovered found killed attack attacked survived escaped million billion thousand hundred jamais toujours plus pire meilleur
dangereux mortel rare secret personne pourquoi comment incroyable découvert attaque survécu échappé million milliard""".split())

# words that make good literal B-roll (animals, nature, objects, places, actions) — boosts keyword ranking
VISUAL = set("""
animal animals shark sharks whale whales orca orcas dolphin dolphins octopus octopuses squid crab crabs fish fishes turtle turtles
seal seals penguin penguins bird birds eagle eagles owl owls crow crows parrot snake snakes python pythons cobra viper crocodile
crocodiles croc alligator alligators lizard lizards frog frogs spider spiders ant ants bee bees insect insects butterfly beetle
lion lions tiger tigers leopard jaguar panther cheetah bear bears wolf wolves fox foxes deer moose elk elephant elephants rhino
hippo hippos giraffe zebra gorilla gorillas monkey monkeys chimp chimpanzee ape horse horses cow cows pig pigs dog dogs puppy cat
cats kitten rabbit mouse rat bat bats camel kangaroo koala panda pandas buffalo bison goat sheep chicken duck
ocean sea beach coast wave waves river lake water rain storm lightning thunder snow ice glacier desert sand forest jungle rainforest
tree trees wood leaf leaves flower flowers grass mountain mountains volcano cave island sky cloud clouds sun moon stars star space
planet earth night fire smoke city street road bridge car cars truck boat ship plane airplane helicopter rocket train bike
house home kitchen food coffee tea pizza bread fruit meat money gold diamond phone computer camera gun knife jar lid light lights
drain pipe floor door window tank aquarium zoo farm lab laboratory hospital doctor scientist diver divers boat army soldier
blood bone bones skull teeth tooth eye eyes brain heart hand hands arm arms leg legs skin hair baby child children family
requin requins baleine dauphin poulpe pieuvre crabe poisson tortue phoque pingouin oiseau aigle serpent crocodile lézard
araignée fourmi abeille insecte lion tigre ours loup renard cerf éléphant girafe gorille singe cheval chien chat lapin
océan mer plage vague rivière lac eau pluie orage neige glace désert forêt jungle arbre fleur montagne volcan grotte île
ciel nuage soleil lune étoile espace planète nuit feu ville rue pont voiture bateau avion fusée maison nourriture café argent
""".split())


def bare(w: str) -> str:
    return re.sub(r"[^\w'’-]", "", w).lower().replace("’", "'")


def sentences(words: list[dict], pause: float = 0.9) -> list[dict]:
    """Group words into sentences on terminal punctuation or long pauses."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        nxt = words[i + 1]["start"] if i + 1 < len(words) else None
        end_punct = bool(re.search(r"[.!?…]$", w["word"].strip()))
        if end_punct or nxt is None or (nxt - w["end"]) > pause:
            out.append({"i0": cur[0], "i1": cur[-1], "start": words[cur[0]]["start"], "end": words[cur[-1]]["end"],
                        "text": " ".join(words[k]["word"] for k in cur)})
            cur = []
    return out


def keywords(words: list[dict], i0: int, i1: int, top: int = 40) -> list[dict]:
    """Showable keywords in words[i0..i1], best words first, EVERY occurrence kept (repeated nouns are
    prime B-roll anchors later in the story). Returns [{idx, word, query, score}]."""
    counts = Counter(bare(words[k]["word"]) for k in range(i0, i1 + 1))
    best = {}
    occ = {}
    for k in range(i0, i1 + 1):
        b = bare(words[k]["word"])
        if len(b) < 3 or b in STOP or b in FILLERS or b.isdigit():
            continue
        if b.endswith("ly") and b not in VISUAL:
            continue
        occ.setdefault(b, []).append(k)
        if b not in best:
            score = 1.0 + 0.4 * (counts[b] - 1) + (2.5 if b in VISUAL or b.rstrip("s") in VISUAL else 0.0)
            score += 0.3 if len(b) >= 6 else 0.0
            q = b[:-1] if b.endswith("s") and len(b) > 4 and b[:-1] in VISUAL else b
            best[b] = (round(score, 2), q)
    ranked = sorted(best, key=lambda w: -best[w][0])[:top]
    out = [{"idx": k, "word": w, "query": best[w][1], "score": best[w][0]} for w in ranked for k in occ[w]]
    return out


HOOK_PHRASES = ("did you know", "imagine", "here's the", "the craziest", "true story", "nobody knows", "the reason",
                "the truth", "what happened", "saviez-vous", "imaginez", "le plus", "personne ne", "la vérité")
META = ("welcome back", "welcome to", "thanks for", "thank you for", "today we", "before we start", "let's talk about",
        "talk about something else", "anyway", "moving on", "see you", "that's the show", "subscribe", "sponsor",
        "link in", "okay, so", "bienvenue", "merci de", "abonnez", "on se retrouve", "passons à")


def is_meta(text: str) -> bool:
    t = text.lower().strip()
    return any(m in t for m in META) or len(t.split()) <= 2


def hook_score(text: str) -> float:
    t = text.lower()
    toks = [bare(x) for x in t.split()]
    s = 0.0
    s += 1.5 * sum(1 for x in toks if x in HOOK_WORDS)
    s += 2.0 * sum(1 for p in HOOK_PHRASES if p in t)
    s += 1.5 if re.search(r"\d", t) else 0.0
    s += 1.0 if "?" in t else 0.0
    s += 0.5 if 4 <= len(toks) <= 16 else -0.5
    s -= 1.5 if toks and toks[0] in {"so", "and", "but", "um", "uh", "yeah", "like", "then", "donc", "et", "mais", "euh"} else 0.0
    s -= 4.0 if is_meta(text) else 0.0
    return s
