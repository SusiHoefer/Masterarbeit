
# ============================================================
# NLP-Vorverarbeitung für deutsche Texte
# - besserer Lemmatizer mit spaCy
# - Komposita werden erkannt und zerlegt
# - Negationen bleiben erhalten
# - Ausgabe ist anfängerfreundlich
# ============================================================

import re
import json
import zipfile
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import spacy


# ============================================================
# 1) Dateien laden
# ============================================================

txt_path = Path("Polgartexte.txt")
zip_path = Path("dwdswb-headwords.zip")

raw_text = txt_path.read_text(encoding="utf-8")

with zipfile.ZipFile(zip_path) as zf:
    json_name = zf.namelist()[0]
    with zf.open(json_name) as f:
        dwds = json.load(f)

# Das DWDS-Lexikon als Menge anlegen:
# Mengen (set) sind praktisch, weil Nachschlagen sehr schnell ist.
dwds_lexicon = {str(k).lower() for k in dwds.keys()}


# ============================================================
# 2) spaCy-Modell laden
# ============================================================
# Wichtig:
# Vorher einmal installieren:
# python -m spacy download de_core_news_md
#
# Falls du nur wenig RAM hast:
# de_core_news_sm verwenden

nlp = spacy.load("de_core_news_md")


# ============================================================
# 3) Wichtige Wortlisten
# ============================================================

# Negationen sollen NICHT verschwinden.
# Diese Wörter wollen wir später unbedingt behalten.
NEGATIONS = {
    "nicht", "nie", "niemals", "nichts", "nirgends", "nirgendwo",
    "kein", "keine", "keinen", "keinem", "keiner", "keines",
    "weder", "ohne"
}

# Stopwörter:
# Wir starten mit spaCy-Stopwörtern, entfernen aber Negationen daraus.
# So bleiben Negationen in der Analyse erhalten.
STOPWORDS = set(nlp.Defaults.stop_words) - NEGATIONS


# ============================================================
# 4) Text normalisieren
# ============================================================

def normalize_text(text: str) -> str:
    """
    Macht den Text sauberer.

    Schritte:
    1. Unicode vereinheitlichen
    2. weiche Trennstriche entfernen
    3. Zeilentrennung in Wörtern reparieren
    4. Leerzeichen vereinheitlichen
    """
    text = unicodedata.normalize("NFC", text)

    # Sonderfälle aus OCR / alten Texten
    text = text.replace("\u00ad", "")   # weicher Trennstrich
    text = text.replace("¬\n", "")

    # Beispiel: "ge-\nhen" -> "gehen"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Alle Leerraumarten auf ein Leerzeichen reduzieren
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# 5) Hilfsfunktionen für deutsche Varianten
# ============================================================

def orthographic_variants(word: str) -> List[str]:
    """
    Erzeugt einfache Schreibvarianten:
    - ß <-> ss
    - ä/ö/ü <-> a/o/u

    Das hilft bei historischen oder uneinheitlichen Schreibungen.
    """
    variants = {word}

    if "ß" in word:
        variants.add(word.replace("ß", "ss"))
    if "ss" in word:
        variants.add(word.replace("ss", "ß"))

    variants.add(word.replace("ä", "a").replace("ö", "o").replace("ü", "u"))

    return list(variants)


def in_lexicon(word: str, lexicon: set[str]) -> bool:
    """
    Prüft, ob ein Wort oder eine einfache Schreibvariante
    im Lexikon vorkommt.
    """
    for form in orthographic_variants(word):
        if form in lexicon:
            return True
    return False


# ============================================================
# 6) Komposita zerlegen
# ============================================================
# Ziel:
# - Deutsche Komposita wie "Großstadtjugend" erkennen
# - in Teile zerlegen, z. B. ["groß", "stadt", "jugend"]
# - das Originalwort trotzdem behalten
#
# Diese Funktion ist absichtlich transparent und verständlich.
# Sie ist heuristisch, aber deutlich besser als gar kein Splitting.

FUGENLAUTE = ["", "s", "es", "n", "en", "er", "e"]


def split_compound_dp(word: str, lexicon: set[str], min_part_len: int = 3) -> Optional[List[str]]:
    """
    Versucht, ein deutsches Kompositum mit dynamischer Programmierung
    in bekannte Lexikonteile zu zerlegen.

    Beispiel:
    "großstadtjugend" -> ["groß", "stadt", "jugend"]

    Rückgabe:
    - Liste von Teilen, wenn ein guter Split gefunden wird
    - None, wenn kein sinnvoller Split gefunden wird

    Idee:
    Wir laufen von links nach rechts durch das Wort und prüfen,
    ob wir vorne einen bekannten Teil finden.
    Danach versuchen wir rekursiv / schrittweise, den Rest zu zerlegen.
    """

    word = word.lower()
    n = len(word)

    # Sehr kurze Wörter brauchen wir nicht zu splitten.
    if n < 2 * min_part_len:
        return None

    # dp[i] speichert einen guten Split für das Teilwort word[:i]
    # oder None, falls bis dahin kein Split gefunden wurde.
    dp: List[Optional[List[str]]] = [None] * (n + 1)
    dp[0] = []

    for i in range(n):
        if dp[i] is None:
            continue

        # Von Position i aus versuchen wir ein nächstes Teil zu finden.
        for j in range(i + min_part_len, n + 1):
            candidate = word[i:j]

            # Wir erlauben auch Fugenlaute am Anfang des Reststücks:
            # z. B. "arbeitszimmer" = arbeit + s + zimmer
            for fugenlaut in FUGENLAUTE:
                if candidate.startswith(fugenlaut):
                    core = candidate[len(fugenlaut):]
                else:
                    continue

                if len(core) < min_part_len:
                    continue

                if in_lexicon(core, lexicon):
                    new_parts = dp[i] + [core]

                    # Wir speichern nur dann,
                    # wenn wir an dieser Position noch keinen Split haben
                    # oder der neue Split "besser" ist.
                    #
                    # "Besser" heißt hier:
                    # - lieber weniger Teile
                    # - und lieber längere Teile
                    if dp[j] is None:
                        dp[j] = new_parts
                    else:
                        old_score = (len(dp[j]), -sum(len(x) for x in dp[j]))
                        new_score = (len(new_parts), -sum(len(x) for x in new_parts))
                        if new_score < old_score:
                            dp[j] = new_parts

    result = dp[n]

    # Ein Split mit nur 1 Teil ist kein echtes Kompositum.
    if result is None or len(result) < 2:
        return None

    return result


# ============================================================
# 7) Lemma für GermaNet vorbereiten
# ============================================================

def normalize_lemma_for_lookup(lemma: str) -> str:
    """
    Macht ein Lemma etwas robuster für Lexikonabfragen.
    """
    lemma = lemma.lower().strip()

    # Häufiger Fall: Pronomen-Dash oder OCR-Reste
    lemma = re.sub(r"^[^\wäöüß]+|[^\wäöüß]+$", "", lemma)

    return lemma


def build_lookup_candidates(
    token_text: str,
    lemma: str,
    pos: str,
    lexicon: set[str]
) -> Tuple[str, Optional[List[str]], List[str]]:
    """
    Baut Kandidaten für spätere GermaNet-Lookups.

    Rückgabe:
    1. best_lemma:
       das Hauptlemma, mit dem du zuerst suchen würdest
    2. compound_parts:
       falls das Wort ein Kompositum ist, die Teile
    3. lookup_candidates:
       eine priorisierte Liste möglicher Suchformen

    Wichtige Idee:
    - Das Kompositum bleibt als Ganzes sichtbar
    - Die Einzelteile kommen zusätzlich dazu
    """

    token_text = token_text.lower()
    lemma = normalize_lemma_for_lookup(lemma)

    lookup_candidates = []
    compound_parts = None

    # Erst das ganze Lemma probieren
    if lemma:
        lookup_candidates.append(lemma)

    # Zusätzlich die Oberflächenform
    if token_text != lemma:
        lookup_candidates.append(token_text)

    # Bei langen Nomen und Adjektiv/Nomen-ähnlichen Wörtern
    # lohnt sich Komposita-Splitting besonders.
    #
    # POS aus spaCy hilft dabei:
    # NOUN, PROPN, ADJ sind für deutsche Komposita häufig interessant.
    if pos in {"NOUN", "PROPN", "ADJ"} and len(lemma) >= 6:
        split = split_compound_dp(lemma, lexicon)

        if split:
            compound_parts = split

            # Ganze Form weiterhin behalten
            # und zusätzlich die Teile hinzufügen.
            for part in split:
                if part not in lookup_candidates:
                    lookup_candidates.append(part)

    # Varianten ergänzen
    expanded = []
    seen = set()

    for cand in lookup_candidates:
        for var in orthographic_variants(cand):
            if var not in seen:
                seen.add(var)
                expanded.append(var)

    best_lemma = lemma if lemma else token_text
    return best_lemma, compound_parts, expanded


# ============================================================
# 8) Hauptfunktion: Text analysieren
# ============================================================

def preprocess_text(text: str, lexicon: set[str]) -> List[Dict]:
    """
    Führt die gesamte Vorverarbeitung durch.

    Für jedes Token liefern wir ein Wörterbuch mit:
    - originaler Form
    - Lemma
    - Wortart
    - Negations-Info
    - Stopwort-Info
    - Kompositum-Teile
    - Kandidaten für GermaNet
    """

    clean_text = normalize_text(text)
    doc = nlp(clean_text)

    rows = []

    for token in doc:
        # Satzzeichen, Leerzeichen und Zahlen überspringen
        if token.is_space or token.is_punct or token.like_num:
            continue

        surface = token.text
        lower = token.text.lower()

        # spaCy-Lemma benutzen:
        # Das ist der große Unterschied zu deinem alten Code.
        lemma = token.lemma_.lower().strip()

        # Falls spaCy mal etwas Leeres oder Unsinn liefert,
        # nehmen wir die Kleinschreibung der Oberfläche.
        if not lemma:
            lemma = lower

        pos = token.pos_

        is_negation = lower in NEGATIONS or lemma in NEGATIONS

        # Negationen sollen niemals als Stopwort herausfallen.
        is_stop = (lower in STOPWORDS or lemma in STOPWORDS) and not is_negation

        best_lemma, compound_parts, lookup_candidates = build_lookup_candidates(
            token_text=lower,
            lemma=lemma,
            pos=pos,
            lexicon=lexicon
        )

        # "Gefunden" heißt hier:
        # mind. eine der Kandidatenformen kommt im Lexikon vor.
        found_in_lexicon = any(in_lexicon(c, lexicon) for c in lookup_candidates)

        row = {
            "surface": surface,                     # Original im Text
            "lower": lower,                        # Kleinschreibung
            "lemma": best_lemma,                   # Hauptlemma
            "pos": pos,                            # Wortart aus spaCy
            "is_negation": is_negation,            # Negation ja/nein
            "is_stopword": is_stop,                # Stopwort ja/nein
            "compound_parts": compound_parts,      # z. B. ["groß", "stadt", "jugend"]
            "lookup_candidates": lookup_candidates, # für GermaNet
            "in_lexicon": found_in_lexicon         # kam etwas im Lexikon vor?
        }

        rows.append(row)

    return rows


# ============================================================
# 9) Hilfsfunktionen für Auswertungen
# ============================================================

def token_coverage(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Abdeckung auf TOKEN-Ebene:
    jedes Wortvorkommen zählt einzeln
    """
    total = len(rows)
    matches = sum(1 for r in rows if r["in_lexicon"])
    percent = (matches / total * 100) if total else 0.0
    return matches, total, percent


def token_coverage_without_stopwords(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Token-Abdeckung ohne Stopwörter.
    Negationen bleiben trotzdem erhalten.
    """
    content_rows = [r for r in rows if not r["is_stopword"]]
    total = len(content_rows)
    matches = sum(1 for r in content_rows if r["in_lexicon"])
    percent = (matches / total * 100) if total else 0.0
    return matches, total, percent


def type_coverage(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Abdeckung auf TYPE-Ebene:
    nur verschiedene Lemmas zählen
    """
    types = {}
    for r in rows:
        types[r["lemma"]] = r["in_lexicon"]

    total = len(types)
    matches = sum(1 for found in types.values() if found)
    percent = (matches / total * 100) if total else 0.0
    return matches, total, percent


def type_coverage_without_stopwords(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Type-Abdeckung ohne Stopwörter.
    Negationen bleiben erhalten.
    """
    types = {}
    for r in rows:
        if not r["is_stopword"]:
            types[r["lemma"]] = r["in_lexicon"]

    total = len(types)
    matches = sum(1 for found in types.values() if found)
    percent = (matches / total * 100) if total else 0.0
    return matches, total, percent


def print_examples(rows: List[Dict], n: int = 30) -> None:
    """
    Zeigt die ersten n Tokens schön lesbar an.
    """
    print("\nERSTE TOKENS NACH DEM PREPROCESSING:")
    print("-" * 80)

    for r in rows[:n]:
        print(
            f"surface={r['surface']:<20} "
            f"lemma={r['lemma']:<20} "
            f"pos={r['pos']:<6} "
            f"neg={str(r['is_negation']):<5} "
            f"compound_parts={r['compound_parts']}"
        )


def print_compound_examples(rows: List[Dict], n: int = 20) -> None:
    """
    Zeigt erkannte Komposita.
    """
    compounds = [r for r in rows if r["compound_parts"]]

    print("\nERKANNTE KOMPOSITA:")
    print("-" * 80)

    for r in compounds[:n]:
        print(
            f"{r['surface']} -> lemma={r['lemma']} -> teile={r['compound_parts']}"
        )

    print(f"\nInsgesamt erkannte Komposita: {len(compounds)}")


def export_rows_to_json(rows: List[Dict], output_path: str = "preprocessed_tokens.json") -> None:
    """
    Speichert die Vorverarbeitung als JSON-Datei.
    Das ist praktisch für spätere GermaNet-Schritte.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\nJSON gespeichert unter: {output_path}")


# ============================================================
# 10) Ausführen
# ============================================================

rows = preprocess_text(raw_text, dwds_lexicon)

print("TOKEN-Abdeckung mit Stopwörtern:")
m, t, p = token_coverage(rows)
print(f"{m} / {t} = {p:.2f}%")

print("\nTOKEN-Abdeckung ohne Stopwörter (Negationen bleiben erhalten):")
m, t, p = token_coverage_without_stopwords(rows)
print(f"{m} / {t} = {p:.2f}%")

print("\nTYPE-Abdeckung mit Stopwörtern:")
m, t, p = type_coverage(rows)
print(f"{m} / {t} = {p:.2f}%")

print("\nTYPE-Abdeckung ohne Stopwörter (Negationen bleiben erhalten):")
m, t, p = type_coverage_without_stopwords(rows)
print(f"{m} / {t} = {p:.2f}%")

print_examples(rows, n=30)
print_compound_examples(rows, n=20)

export_rows_to_json(rows)