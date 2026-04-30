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

lexikon = {str(wort).lower() for wort in dwds_daten.keys()}


# ============================================================
# 2) spaCy-Modell laden
# ============================================================

nlp = spacy.load("de_core_news_md")


# ============================================================
# 3) Wichtige Wortlisten
# ============================================================

NEGATIONEN = {
    "nicht", "nie", "niemals", "nichts", "nirgends", "nirgendwo",
    "kein", "keine", "keinen", "keinem", "keiner", "keines",
    "weder", "ohne"
}

STOPWOERTER = set(nlp.Defaults.stop_words) - NEGATIONEN

FUGENLAUTE = ["", "s", "es", "n", "en", "er", "e"]


# ============================================================
# 4) Text bereinigen
# ============================================================

def text_normalisieren(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00ad", "")
    text = text.replace("¬\n", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================
# 5) Schreibvarianten prüfen
# ============================================================

def schreibvarianten(wort: str) -> List[str]:
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
    wort = wort.lower()
    laenge = len(wort)

    if laenge < 2 * mindestlaenge:
        return None

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
    lemma = lemma.lower().strip()
    lemma = re.sub(r"^[^\wäöüß]+|[^\wäöüß]+$", "", lemma)
    return lemma


# ============================================================
# 8) Partizip-I-Formen auf Verbgrundform prüfen
# ============================================================

def partizip_oder_adjektiv_zu_verb(wort: str, lexikon: set[str]) -> Optional[str]:
    wort = wort.lower().strip()

    if len(wort) < 5:
        return None

    moegliche_formen = [wort]
    adjektiv_endungen = ["em", "en", "er", "es", "e"]

    for endung in adjektiv_endungen:
        if wort.endswith(endung) and len(wort) > len(endung) + 3:
            moegliche_formen.append(wort[:-len(endung)])

    gesehen = set()
    bereinigte_formen = []

    for form in moegliche_formen:
        if form not in gesehen:
            gesehen.add(form)
            bereinigte_formen.append(form)

    for form in bereinigte_formen:
        if not form.endswith("end"):
            continue

        stamm = form[:-3]
        moegliche_verben = [
            stamm + "en",
            stamm + "ern",
            stamm + "eln",
        ]

        for verb in moegliche_verben:
            if ist_im_lexikon(verb, lexikon):
                return verb

    return None


# ============================================================
# 9) Suchkandidaten bauen
# ============================================================

def suche_kandidaten_bauen(
    token_text: str,
    lemma: str,
    pos: str,
    lexikon: set[str]
) -> Tuple[str, Optional[List[str]], List[str]]:
    token_text = token_text.lower()
    lemma = lemma_bereinigen(lemma)

    kandidaten = []
    kompositum_teile = None

    if lemma:
        kandidaten.append(lemma)

    if token_text != lemma:
        kandidaten.append(token_text)

    verb_grundform = partizip_oder_adjektiv_zu_verb(token_text, lexikon)
    if verb_grundform and verb_grundform not in kandidaten:
        kandidaten.append(verb_grundform)

    if pos in {"NOUN", "PROPN", "ADJ"} and len(lemma) >= 6:
        teile = kompositum_zerlegen(lemma, lexikon)

        if teile:
            kompositum_teile = teile
            for teil in teile:
                if teil not in kandidaten:
                    kandidaten.append(teil)

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
# 10) Hauptfunktion für die Vorverarbeitung
# ============================================================

def text_vorverarbeiten(text: str, lexikon: set[str]) -> List[Dict]:
    sauberer_text = text_normalisieren(text)
    doc = nlp(sauberer_text)

    ergebnisse = []

    for token in doc:
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
# 11) Auswertungen
# ============================================================

def token_abdeckung(rows: List[Dict]) -> Tuple[int, int, float]:
    gesamt = len(rows)
    treffer = sum(1 for row in rows if row["in_lexicon"])
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


def token_abdeckung_ohne_stopwoerter(rows: List[Dict]) -> Tuple[int, int, float]:
    inhaltswoerter = [row for row in rows if not row["is_stopword"]]
    gesamt = len(inhaltswoerter)
    treffer = sum(1 for row in inhaltswoerter if row["in_lexicon"])
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


def typ_abdeckung(rows: List[Dict]) -> Tuple[int, int, float]:
    typen = {}

    for row in rows:
        typen[row["lemma"]] = row["in_lexicon"]

    gesamt = len(typen)
    treffer = sum(1 for gefunden in typen.values() if gefunden)
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


def typ_abdeckung_ohne_stopwoerter(rows: List[Dict]) -> Tuple[int, int, float]:
    typen = {}

    for row in rows:
        if not row["is_stopword"]:
            typen[row["lemma"]] = row["in_lexicon"]

    gesamt = len(typen)
    treffer = sum(1 for gefunden in typen.values() if gefunden)
    prozent = (treffer / gesamt * 100) if gesamt else 0.0
    return treffer, gesamt, prozent


# ============================================================
# 12) Ausgabe-Hilfen
# ============================================================

def erste_tokens_anzeigen(rows: List[Dict], anzahl: int = 30) -> None:
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
    komposita = [row for row in rows if row["compound_parts"]]

    print("\nERKANNTE KOMPOSITA:")
    print("-" * 80)

    for row in komposita[:anzahl]:
        print(
            f"{row['surface']} -> lemma={row['lemma']} -> teile={row['compound_parts']}"
        )

    print(f"\nInsgesamt erkannte Komposita: {len(komposita)}")


def json_speichern(rows: List[Dict], dateiname: str = "preprocessed_tokens2.json") -> None:
    with open(dateiname, "w", encoding="utf-8") as datei:
        json.dump(rows, datei, ensure_ascii=False, indent=2)

    print(f"\nJSON gespeichert unter: {dateiname}")


# ============================================================
# 13) Hauptprogramm
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
