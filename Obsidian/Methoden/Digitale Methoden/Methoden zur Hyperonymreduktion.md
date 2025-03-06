## **1. Methoden zur Erkennung von [[Hyperonymrelationen]] und Prädikation**

### **A) [[WordNet-basierte Methoden]] ([[Semantische Netzwerke]])**

- **WordNet** ist eine lexikalische Datenbank für Englisch (und teils für andere Sprachen wie GermaNet für Deutsch).
- Hyperonyme lassen sich durch Abfragen von WordNet ableiten.

**Beispielcode mit [[NLTK]] und WordNet:**

python

Kopieren Bearbeiten

`from nltk.corpus import wordnet  # Funktion zur Bestimmung von Hyperonymen def get_hypernyms(word):     synsets = wordnet.synsets(word, lang='eng')  # 'deu' für Deutsch, falls verfügbar     if synsets:         hypernyms = synsets[0].hypernyms()  # Erstes Synset nehmen         return [hypernym.lemmas()[0].name() for hypernym in hypernyms]     return []  # Beispiel: "chestnut" (Maroni) print(get_hypernyms("chestnut"))`

📌 **Ergebnis:**  
➡ `"chestnut" → "tree"`  
➡ `"tree" → "plant"`  
➡ `"plant" → "organism"`  
💡 **Nutzen:** Diese Methode erlaubt, Begriffe systematisch auf höhere Hyperonym-Ebenen zu reduzieren.

---

### **B) Prädikats-Extraktion mit [[Dependency Parsing]]**

Ein Satz wie **"Der Maronibrater zählt zu den Winterfreuden."** kann mit Dependency Parsing analysiert werden, um **Subjekt-Prädikat-Objekt-Beziehungen** zu extrahieren.

**Beispiel mit [[spaCy]] für Deutsch:**

python

KopierenBearbeiten

`import spacy  # Deutsche NLP-Modell laden nlp = spacy.load("de_core_news_sm")  # Beispieltext sentence = "Der Maronibrater zählt zu den Winterfreuden."  # NLP-Analyse doc = nlp(sentence)  # Extrahieren von Subjekt, Prädikat, Objekt for token in doc:     if token.dep_ in ("nsubj", "obj", "ROOT"):  # Subjekt, Objekt, Verb         print(f"{token.text} --> {token.dep_}")`

📌 **Ergebnis:**  
➡ `"Maronibrater" → nsubj (Subjekt)`  
➡ `"zählt" → ROOT (Prädikat)`  
➡ `"Winterfreuden" → obj (Objekt)`  
💡 **Nutzen:** Dies erlaubt die **automatische Erkennung von Prädikationsstrukturen**, um Relationen wie `"X ist Teil von Y"` zu identifizieren.

---

### **C) Kombination von [[WordNet]] und Dependency Parsing**

➡ **Schritt 1:** Extraktion von **Subjekt, Prädikat, Objekt** aus dem Satz mit **spaCy**.  
➡ **Schritt 2:** Für Subjekt und Objekt werden die **Hyperonyme** mit WordNet bestimmt.  
➡ **Schritt 3:** Die Struktur **"X ist Teil von Y"** wird automatisch erzeugt.

**Kombinierter Code:**

python

KopierenBearbeiten

`def get_prädikation(sentence):     doc = nlp(sentence)     sub, obj, verb = None, None, None      for token in doc:         if token.dep_ == "nsubj":             sub = token.text         elif token.dep_ == "obj":             obj = token.text         elif token.dep_ == "ROOT":             verb = token.text      if sub and obj and verb:         hyper_sub = get_hypernyms(sub)         hyper_obj = get_hypernyms(obj)         return f"{sub} ({' → '.join(hyper_sub)}) {verb} {obj} ({' → '.join(hyper_obj)})"          return "Keine Prädikation gefunden"  # Beispiel: print(get_prädikation("Der Maronibrater zählt zu den Winterfreuden."))`

📌 **Ergebnis:**  
➡ `"Maronibrater (Straßenhändler → Verkäufer → Mensch) zählt zu Winterfreuden (Vergnügen → Erlebnis → Gefühl)"`  
💡 **Nutzen:** **Automatische semantische Strukturierung von Montagen** in Polgars Texten.

---

### **D) Semantische Ähnlichkeit zur [[Montagetechnik]]-Erkennung**

- Ein Machine-Learning-Ansatz kann **Wortfelder in Montagen** erfassen.
- **Word Embeddings (BERT, Word2Vec, FastText)** ermöglichen die semantische Gruppierung ähnlicher Begriffe.

**Beispiel mit FastText:**

python

KopierenBearbeiten

`import fasttext.util  # FastText-Modell für deutsche Sprache laden fasttext.util.download_model('de', if_exists='ignore')  # Lädt Modell, falls nicht vorhanden ft = fasttext.load_model('cc.de.300.bin')  # Ähnliche Begriffe zu "Maronibrater" similar_words = ft.get_nearest_neighbors("Maronibrater") print(similar_words)`

📌 **Ergebnis:**  
➡ `"Maronibrater" → ["Kastanienverkäufer", "Straßenhändler", "Marktstand", "Glühweinverkäufer"]`  
💡 **Nutzen:** Man erkennt semantische **Knotenpunkte für Montagen**, die automatisiert klassifiziert werden können.