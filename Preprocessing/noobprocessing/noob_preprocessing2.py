# ============================================================
# Einfache NLP-Vorverarbeitung für deutsche Texte
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

TEXT_DATEI = Path("Polgartexte.txt")
LEXIKON_ZIP = Path("dwdswb-headwords.zip")

text = TEXT_DATEI.read_text(encoding="utf-8")

with zipfile.ZipFile(LEXIKON_ZIP) as zip_datei:
    json_name = zip_datei.namelist()[0]
    with zip_datei.open(json_name) as datei:
        dwds_daten = json.load(datei)

# Wir speichern alle Wörter aus dem Lexikon in einer Menge (set).
# Das ist praktisch, weil man damit sehr schnell prüfen kann,
# ob ein Wort vorhanden ist.
lexikon = {str(wort).lower() for wort in dwds_daten.keys()}


# ============================================================
# 2) spaCy-Modell laden
# ============================================================
# Vorher installieren:
# python -m spacy download de_core_news_md

nlp = spacy.load("de_core_news_md")


# ============================================================
# 3) Wichtige Wortlisten
# ============================================================

# Diese Wörter sollen erhalten bleiben, weil sie für die Bedeutung
# eines Satzes sehr wichtig sein können.
NEGATIONEN = {
    "nicht", "nie", "niemals", "nichts", "nirgends", "nirgendwo",
    "kein", "keine", "keinen", "keinem", "keiner", "keines",
    "weder", "ohne"
}

# Stopwörter von spaCy, aber ohne Negationen
STOPWOERTER = set(nlp.Defaults.stop_words) - NEGATIONEN

# Typische Fugenlaute in deutschen Komposita
FUGENLAUTE = ["", "s", "es", "n", "en", "er", "e"]


# ============================================================
# 4) Text bereinigen
# ============================================================

def text_normalisieren(text: str) -> str:
    """
    Macht den Text sauberer und einheitlicher.
    """
    text = unicodedata.normalize("NFC", text)

    # Weichen Trennstrich entfernen
    text = text.replace("\u00ad", "")

    # Sonderfall aus OCR / alten Texten
    text = text.replace("¬\n", "")

    # Zeilenumbruch in getrennten Wörtern reparieren:
    # ge-\nhen -> gehen
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Mehrere Leerzeichen / Umbrüche zu einem Leerzeichen machen
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# 5) Schreibvarianten prüfen
# ============================================================

def schreibvarianten(wort: str) -> List[str]:
    """
    Erzeugt einfache Varianten eines Wortes.
    Beispiel:
    - Straße -> Strasse
    - groß -> gross
    - müde -> mude
    """
    varianten = {wort}

    if "ß" in wort:
        varianten.add(wort.replace("ß", "ss"))

    if "ss" in wort:
        varianten.add(wort.replace("ss", "ß"))

    varianten.add(
        wort.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    )

    return list(varianten)


def ist_im_lexikon(wort: str, lexikon: set[str]) -> bool:
    """
    Prüft, ob ein Wort oder eine einfache Variante davon
    im Lexikon vorkommt.
    """
    for variante in schreibvarianten(wort):
        if variante in lexikon:
            return True
    return False


# ============================================================
# 6) Komposita zerlegen
# ============================================================

def kompositum_zerlegen(
    wort: str,
    lexikon: set[str],
    mindestlaenge: int = 3
) -> Optional[List[str]]:
    """
    Versucht, ein deutsches Kompositum in bekannte Teile zu zerlegen.

    Beispiel:
    großstadtjugend -> ["groß", "stadt", "jugend"]

    Wenn kein sinnvoller Split gefunden wird, kommt None zurück.
    """
    wort = wort.lower()
    laenge = len(wort)

    # Zu kurze Wörter nicht zerlegen
    if laenge < 2 * mindestlaenge:
        return None

    # dp[i] speichert eine gefundene Zerlegung für wort[:i]
    dp: List[Optional[List[str]]] = [None] * (laenge + 1)
    dp[0] = []

    for start in range(laenge):
        if dp[start] is None:
            continue

        for ende in range(start + mindestlaenge, laenge + 1):
            teil = wort[start:ende]

            for fugenlaut in FUGENLAUTE:
                if not teil.startswith(fugenlaut):
                    continue

                kern = teil[len(fugenlaut):]

                if len(kern) < mindestlaenge:
                    continue

                if ist_im_lexikon(kern, lexikon):
                    neue_teile = dp[start] + [kern]

                    if dp[ende] is None:
                        dp[ende] = neue_teile
                    else:
                        alter_wert = dp[ende]

                        # Wir bevorzugen:
                        # 1. weniger Teile
                        # 2. längere Teile
                        alter_score = (len(alter_wert), -sum(len(x) for x in alter_wert))
                        neuer_score = (len(neue_teile), -sum(len(x) for x in neue_teile))

                        if neuer_score < alter_score:
                            dp[ende] = neue_teile

    ergebnis = dp[laenge]

    if ergebnis is None or len(ergebnis) < 2:
        return None

    return ergebnis


# ============================================================
# 7) Lemma vorbereiten
# ============================================================

def lemma_bereinigen(lemma: str) -> str:
    """
    Bereinigt ein Lemma für spätere Nachschlage-Schritte.
    """
    lemma = lemma.lower().strip()

    # Sonderzeichen am Anfang oder Ende entfernen
    lemma = re.sub(r"^[^\wäöüß]+|[^\wäöüß]+$", "", lemma)

    return lemma

def partizip_oder_adjektiv_zu_verb(wort: str, lexikon: set[str]) -> Optional[str]:
    """
    Führt einfache Partizip-1-Formen auf die Verbgrundform zurück.

    Beispiele:
    - duftend   -> duften
    - duftende  -> duften
    - laufender -> laufen
    - fließendes -> fließen

    Idee:
    Partizip-1-Formen enden oft auf -end.
    Als Adjektiv bekommen sie zusätzlich Endungen wie:
    -e, -en, -em, -er, -es
    """
    wort = wort.lower().strip()

    # Nur bei längeren Wörtern sinnvoll
    if len(wort) < 5:
        return None

    # Zuerst mögliche Adjektiv-Endungen entfernen.
    # So wird z. B. aus "duftende" wieder "duftend".
    moegliche_partizip_formen = [wort]
    adjektiv_endungen = ["em", "en", "er", "es", "e"]

    for endung in adjektiv_endungen:
        if wort.endswith(endung) and len(wort) > len(endung) + 3:
            basis = wort[:-len(endung)]
            moegliche_partizip_formen.append(basis)

    # Doppelte Einträge vermeiden, Reihenfolge aber behalten
    gesehen = set()
    bereinigte_formen = []
    for form in moegliche_partizip_formen:
        if form not in gesehen:
            gesehen.add(form)
            bereinigte_formen.append(form)

    for form in bereinigte_formen:
        if not form.endswith("end"):
            continue

        stamm = form[:-3]

        moegliche_verben = [
            stamm + "en",   # duftend -> duften, laufend -> laufen
            stamm + "ern",  # lodernd -> lodern
            stamm + "eln",  # klingelnd -> klingeln
        ]

        for verb in moegliche_verben:
            if ist_im_lexikon(verb, lexikon):
                return verb

    return None



def suche_kandidaten_bauen(
    token_text: str,
    lemma: str,
    pos: str,
    lexikon: set[str]
) -> Tuple[str, Optional[List[str]], List[str]]:
    """
    Baut Suchkandidaten für ein Token.

    Rückgabe:
    1. Hauptlemma
    2. Teile eines Kompositums oder None
    3. Liste möglicher Suchformen
    """
    token_text = token_text.lower()
    lemma = lemma_bereinigen(lemma)

    kandidaten = []
    kompositum_teile = None

    # Zuerst Lemma
    if lemma:
        kandidaten.append(lemma)

    # Dann Originalform in Kleinbuchstaben
    if token_text != lemma:
        kandidaten.append(token_text)

    # Extra-Regel für Formen wie:
    # fließend -> fließen
    # laufend -> laufen
    # duftend -> duften
    verb_grundform = partizip_oder_adjektiv_zu_verb(token_text, lexikon)
    if verb_grundform and verb_grundform not in kandidaten:
        kandidaten.append(verb_grundform)

    # Komposita vor allem bei Nomen, Eigennamen und Adjektiven prüfen
    if pos in {"NOUN", "PROPN", "ADJ"} and len(lemma) >= 6:
        teile = kompositum_zerlegen(lemma, lexikon)

        if teile:
            kompositum_teile = teile
            for teil in teile:
                if teil not in kandidaten:
                    kandidaten.append(teil)

    # Schreibvarianten ergänzen
    alle_kandidaten = []
    gesehen = set()

    for kandidat in kandidaten:
        for variante in schreibvarianten(kandidat):
            if variante not in gesehen:
                gesehen.add(variante)
                alle_kandidaten.append(variante)

    hauptlemma = lemma if lemma else token_text
    return hauptlemma, kompositum_teile, alle_kandidaten


# ============================================================
# 8) Hauptfunktion für die Vorverarbeitung
# ============================================================

def text_vorverarbeiten(text: str, lexikon: set[str]) -> List[Dict]:
    """
    Verarbeitet den Text mit spaCy und liefert eine Liste von Tokens.
    """
    sauberer_text = text_normalisieren(text)
    doc = nlp(sauberer_text)

    ergebnisse = []

    for token in doc:
        # Unwichtige Tokens überspringen
        if token.is_space or token.is_punct or token.like_num:
            continue

        original = token.text
        klein = token.text.lower()

        lemma = token.lemma_.lower().strip()
        if not lemma:
            lemma = klein

        pos = token.pos_

        ist_negation = klein in NEGATIONEN or lemma in NEGATIONEN
        ist_stopwort = (klein in STOPWOERTER or lemma in STOPWOERTER) and not ist_negation

        hauptlemma, kompositum_teile, suchkandidaten = suche_kandidaten_bauen(
            token_text=klein,
            lemma=lemma,
            pos=pos,
            lexikon=lexikon
        )

        im_lexikon = any(ist_im_lexikon(kandidat, lexikon) for kandidat in suchkandidaten)

        token_info = {
            "surface": original,
            "lower": klein,
            "lemma": hauptlemma,
            "pos": pos,
            "is_negation": ist_negation,
            "is_stopword": ist_stopwort,
            "compound_parts": kompositum_teile,
            "lookup_candidates": suchkandidaten,
            "in_lexicon": im_lexikon
        }

        ergebnisse.append(token_info)

    return ergebnisse


# ============================================================
# 9) Auswertungen
# ============================================================

def token_abdeckung(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Wie viele Tokens wurden im Lexikon gefunden?
    """
    gesamt = len(rows)
    treffer = sum(1 for row in rows if row["in_lexicon"])
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


def token_abdeckung_ohne_stopwoerter(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Token-Abdeckung ohne Stopwörter.
    Negationen bleiben erhalten.
    """
    inhaltswoerter = [row for row in rows if not row["is_stopword"]]
    gesamt = len(inhaltswoerter)
    treffer = sum(1 for row in inhaltswoerter if row["in_lexicon"])
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


def typ_abdeckung(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Wie viele verschiedene Lemmas wurden gefunden?
    """
    typen = {}

    for row in rows:
        typen[row["lemma"]] = row["in_lexicon"]

    gesamt = len(typen)
    treffer = sum(1 for gefunden in typen.values() if gefunden)
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


def typ_abdeckung_ohne_stopwoerter(rows: List[Dict]) -> Tuple[int, int, float]:
    """
    Type-Abdeckung ohne Stopwörter.
    """
    typen = {}

    for row in rows:
        if not row["is_stopword"]:
            typen[row["lemma"]] = row["in_lexicon"]

    gesamt = len(typen)
    treffer = sum(1 for gefunden in typen.values() if gefunden)
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


# ============================================================
# 10) Ausgabe-Hilfen
# ============================================================

def erste_tokens_anzeigen(rows: List[Dict], anzahl: int = 30) -> None:
    """
    Zeigt die ersten Tokens übersichtlich an.
    """
    print("\nERSTE TOKENS:")
    print("-" * 80)

    for row in rows[:anzahl]:
        print(
            f"surface={row['surface']:<20} "
            f"lemma={row['lemma']:<20} "
            f"pos={row['pos']:<6} "
            f"neg={str(row['is_negation']):<5} "
            f"compound_parts={row['compound_parts']}"
        )


def komposita_anzeigen(rows: List[Dict], anzahl: int = 20) -> None:
    """
    Zeigt erkannte Komposita an.
    """
    komposita = [row for row in rows if row["compound_parts"]]

    print("\nERKANNTE KOMPOSITA:")
    print("-" * 80)

    for row in komposita[:anzahl]:
        print(
            f"{row['surface']} -> lemma={row['lemma']} -> teile={row['compound_parts']}"
        )

    print(f"\nInsgesamt erkannte Komposita: {len(komposita)}")


def json_speichern(rows: List[Dict], dateiname: str = "preprocessed_tokens2.json") -> None:
    """
    Speichert die Ergebnisse als JSON-Datei.
    """
    with open(dateiname, "w", encoding="utf-8") as datei:
        json.dump(rows, datei, ensure_ascii=False, indent=2)

    print(f"\nJSON gespeichert unter: {dateiname}")


# ============================================================
# 11) Hauptprogramm
# ============================================================

rows = text_vorverarbeiten(text, lexikon)

print("TOKEN-Abdeckung mit Stopwörtern:")
treffer, gesamt, prozent = token_abdeckung(rows)
print(f"{treffer} / {gesamt} = {prozent:.2f}%")

print("\nTOKEN-Abdeckung ohne Stopwörter:")
treffer, gesamt, prozent = token_abdeckung_ohne_stopwoerter(rows)
print(f"{treffer} / {gesamt} = {prozent:.2f}%")

print("\nTYPE-Abdeckung mit Stopwörtern:")
treffer, gesamt, prozent = typ_abdeckung(rows)
print(f"{treffer} / {gesamt} = {prozent:.2f}%")

print("\nTYPE-Abdeckung ohne Stopwörter:")
treffer, gesamt, prozent = typ_abdeckung_ohne_stopwoerter(rows)
print(f"{treffer} / {gesamt} = {prozent:.2f}%")

erste_tokens_anzeigen(rows, anzahl=30)
komposita_anzeigen(rows, anzahl=20)

json_speichern(rows)