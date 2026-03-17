import re
import json
import zipfile
import unicodedata
from pathlib import Path

txt_path = Path("/mnt/data/Polgartexte.txt")
zip_path = Path("/mnt/data/dwdswb-headwords.zip")

raw_text = txt_path.read_text(encoding="utf-8")

with zipfile.ZipFile(zip_path) as zf:
    json_name = zf.namelist()[0]
    with zf.open(json_name) as f:
        dwds = json.load(f)

STRONG_VERBS = {
    "bin": "sein", "bist": "sein", "ist": "sein", "sind": "sein", "seid": "sein",
    "war": "sein", "warst": "sein", "waren": "sein", "wart": "sein",
    "gewesen": "sein", "wäre": "sein", "wären": "sein",

    "hab": "haben", "habe": "haben", "hast": "haben", "hat": "haben",
    "haben": "haben", "habt": "haben", "hatte": "haben",
    "hatten": "haben", "hattet": "haben", "gehabt": "haben",

    "werde": "werden", "wirst": "werden", "wird": "werden", "werden": "werden",
    "werdet": "werden", "wurde": "werden", "wurden": "werden",
    "wurdest": "werden", "wurdet": "werden", "worden": "werden",
    "geworden": "werden",

    "gab": "geben", "gaben": "geben", "gäbe": "geben", "gäben": "geben",
    "gegeben": "geben", "gibt": "geben", "gebt": "geben",

    "kam": "kommen", "kamen": "kommen", "käme": "kommen", "kämen": "kommen",
    "kommt": "kommen", "gekommen": "kommen",

    "nahm": "nehmen", "nahmen": "nehmen", "nähme": "nehmen", "nähmen": "nehmen",
    "genommen": "nehmen", "nimmt": "nehmen",

    "ging": "gehen", "gingen": "gehen", "gingst": "gehen", "gingt": "gehen",
    "gegangen": "gehen", "geht": "gehen",

    "stand": "stehen", "standen": "stehen", "stünde": "stehen", "ständen": "stehen",
    "gestanden": "stehen", "steht": "stehen",

    "saß": "sitzen", "saßen": "sitzen", "säße": "sitzen", "säßen": "sitzen",
    "gesessen": "sitzen", "sitzt": "sitzen",

    "lag": "liegen", "lagen": "liegen", "läge": "liegen", "lägen": "liegen",
    "gelegen": "liegen", "liegt": "liegen",

    "lief": "laufen", "liefen": "laufen", "liefe": "laufen", "liefet": "laufen",
    "gelaufen": "laufen", "läuft": "laufen",

    "fand": "finden", "fanden": "finden", "fände": "finden", "fänden": "finden",
    "gefunden": "finden", "findet": "finden",

    "sah": "sehen", "sahen": "sehen", "sähe": "sehen", "sähen": "sehen",
    "gesehen": "sehen", "sieht": "sehen",

    "sprach": "sprechen", "sprachen": "sprechen", "spräche": "sprechen",
    "sprächen": "sprechen", "gesprochen": "sprechen", "spricht": "sprechen",

    "schrieb": "schreiben", "schrieben": "schreiben", "schriebe": "schreiben",
    "geschrieben": "schreiben", "schreibt": "schreiben",

    "las": "lesen", "lasen": "lesen", "läse": "lesen", "läsen": "lesen",
    "gelesen": "lesen", "liest": "lesen",

    "aß": "essen", "aßen": "essen", "äße": "essen", "äßen": "essen",
    "gegessen": "essen", "isst": "essen",

    "trank": "trinken", "tranken": "trinken", "trünke": "trinken",
    "getrunken": "trinken", "trinkt": "trinken",

    "half": "helfen", "halfen": "helfen", "hülfe": "helfen",
    "geholfen": "helfen", "hilft": "helfen",

    "rief": "rufen", "riefen": "rufen", "riefe": "rufen",
    "gerufen": "rufen", "ruft": "rufen",

    "schlief": "schlafen", "schliefen": "schlafen", "schliefe": "schlafen",
    "geschlafen": "schlafen", "schläft": "schlafen",

    "wuchs": "wachsen", "wuchsen": "wachsen", "wüchse": "wachsen",
    "gewachsen": "wachsen", "wächst": "wachsen",

    "fiel": "fallen", "fielen": "fallen", "fiele": "fallen",
    "gefallen": "fallen", "fällt": "fallen",

    "hielt": "halten", "hielten": "halten", "hielte": "halten",
    "gehalten": "halten", "hält": "halten",

    "stieß": "stoßen", "stießen": "stoßen", "stieße": "stoßen",
    "gestoßen": "stoßen", "stößt": "stoßen",

    "riet": "raten", "rieten": "raten", "riete": "raten",
    "geraten": "raten", "rät": "raten",

    "trug": "tragen", "trugen": "tragen", "trüge": "tragen",
    "getragen": "tragen", "trägt": "tragen",

    "warf": "werfen", "warfen": "werfen", "würfe": "werfen",
    "geworfen": "werfen", "wirft": "werfen",
}

STOPWORDS = {
    "aber", "als", "am", "an", "auch", "auf", "aus", "bei", "bin", "bis", "bist",
    "da", "dadurch", "daher", "darum", "das", "daß", "dass", "dein", "deine",
    "dem", "den", "der", "des", "dessen", "deshalb", "die", "dies", "diese",
    "diesem", "diesen", "dieser", "dieses", "doch", "dort", "du", "durch", "ein",
    "eine", "einem", "einen", "einer", "eines", "er", "es", "euer", "eure", "für",
    "hatte", "hatten", "hattest", "hattet", "hier", "hinter", "ich", "ihr", "ihre",
    "im", "in", "ist", "ja", "jede", "jedem", "jeden", "jeder", "jedes", "jener",
    "jenes", "jetzt", "kann", "kannst", "können", "könnt", "machen", "mein",
    "meine", "mit", "muß", "mußt", "musst", "müssen", "müßt", "nach", "nachdem",
    "nein", "nicht", "nun", "oder", "seid", "sein", "seine", "sich", "sie", "sind",
    "soll", "sollen", "sollst", "sollt", "sonst", "soweit", "sowie", "und", "unser",
    "unsere", "unter", "vom", "von", "vor", "wann", "warum", "was", "weiter",
    "weitere", "wenn", "wer", "werde", "werden", "werdet", "weshalb", "wie",
    "wieder", "wieso", "wir", "wird", "wirst", "wo", "woher", "wohin", "zu",
    "zum", "zur", "zwar", "zwischen", "über", "ohne", "noch", "nur", "schon",
    "sehr", "so", "man", "manche", "manchem", "manchen", "mancher", "manches",
    "euch", "uns", "mir", "mich", "dir", "dich", "ihm", "ihn", "ihnen", "dazu",
    "darauf", "darin", "darüber", "darunter", "dagegen", "dafür", "dabei", "beim",
    "beispielsweise", "etwa", "kein", "keine", "keinem", "keinen", "keiner",
    "keines", "all", "alle", "allem", "allen", "aller", "alles"
}

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("¬\n", "").replace("\u00ad", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text

def tokenize(text: str):
    text = text.lower()
    return re.findall(r"[a-zäöüß]+", text)

def variants(word: str):
    forms = [word]

    if "ß" in word:
        forms.append(word.replace("ß", "ss"))
    if "ss" in word:
        forms.append(word.replace("ss", "ß"))

    umlaut_map = {"ä": "a", "ö": "o", "ü": "u"}
    deum = "".join(umlaut_map.get(ch, ch) for ch in word)
    if deum != word:
        forms.append(deum)

    return list(dict.fromkeys(forms))

def lemmatize_token(token: str, lexicon: set[str]) -> str:
    if token in STRONG_VERBS:
        return STRONG_VERBS[token]

    for form in variants(token):
        if form in lexicon:
            return form

    candidates = set(variants(token))

    for w in list(candidates):
        if w.startswith("ge") and len(w) > 5:
            candidates.add(w[2:])

        for suf in ("end", "ende", "enden", "endem", "ender", "endes",
                    "ig", "ige", "igen", "igem", "iger", "iges"):
            if w.endswith(suf) and len(w) > len(suf) + 2:
                candidates.add(w[:-len(suf)])

    suffixes = [
        "chen", "lein", "ern", "er", "en", "em", "es", "e", "n", "s",
        "st", "te", "ten", "test", "tet", "t",
        "ung", "ungen", "heit", "heiten", "keit", "keiten",
        "isch", "liche", "lich", "liches", "lichen", "lichem", "licher"
    ]

    for w in list(candidates):
        for suf in suffixes:
            if w.endswith(suf) and len(w) > len(suf) + 2:
                base = w[:-len(suf)]
                candidates.add(base)
                candidates.add(base + "en")

                umlaut_back = base.replace("ä", "a").replace("ö", "o").replace("ü", "u")
                candidates.add(umlaut_back)
                candidates.add(umlaut_back + "e")
                candidates.add(umlaut_back + "en")

    for w in list(candidates):
        if w.endswith("e") and len(w) > 3:
            candidates.add(w[:-1])
        if w.endswith("en") and len(w) > 4:
            candidates.add(w[:-2])
        if w.endswith("er") and len(w) > 4:
            candidates.add(w[:-2])
        if w.endswith("n") and len(w) > 3:
            candidates.add(w[:-1])

    for cand in sorted(candidates, key=lambda x: (0 if x in lexicon else 1, len(x), x)):
        if cand in lexicon:
            return cand

    return token

normalized_text = normalize_text(raw_text)
dwds_lexicon = {str(k).lower() for k in dwds.keys()}

tokens = tokenize(normalized_text)
lemmas = [lemmatize_token(tok, dwds_lexicon) for tok in tokens]

all_total = len(lemmas)
all_match = sum(1 for lemma in lemmas if lemma in dwds_lexicon)

content_lemmas = [lemma for lemma in lemmas if lemma not in STOPWORDS]
content_total = len(content_lemmas)
content_match = sum(1 for lemma in content_lemmas if lemma in dwds_lexicon)

type_lemmas = set(lemmas)
type_content = {lemma for lemma in type_lemmas if lemma not in STOPWORDS}

print("TOKEN-Abdeckung mit Stopwörtern:")
print(f"{all_match} / {all_total} = {all_match / all_total * 100:.2f}%")

print("TOKEN-Abdeckung ohne Stopwörter:")
print(f"{content_match} / {content_total} = {content_match / content_total * 100:.2f}%")

print("TYPE-Abdeckung mit Stopwörtern:")
type_match = sum(1 for lemma in type_lemmas if lemma in dwds_lexicon)
print(f"{type_match} / {len(type_lemmas)} = {type_match / len(type_lemmas) * 100:.2f}%")

print("TYPE-Abdeckung ohne Stopwörter:")
type_content_match = sum(1 for lemma in type_content if lemma in dwds_lexicon)
print(f"{type_content_match} / {len(type_content)} = {type_content_match / len(type_content) * 100:.2f}%")
