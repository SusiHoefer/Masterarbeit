import xml.etree.ElementTree as ET
import json
import pandas as pd
import matplotlib.pyplot as plt

ns = {"tei": "http://www.tei-c.org/ns/1.0"}

tree = ET.parse("Annotationstestlauf_Germanet.xml")
root = tree.getroot()

result = []

divs = root.findall(".//tei:div", ns)

div_index = 0

for div in divs:
    # äußere Sammel-divs überspringen
    if div.findall("tei:div", ns):
        continue

    segs = div.findall(".//tei:seg", ns)

    # leere divs überspringen
    if not segs:
        continue

    for seg in segs:
        entry = {
            "div": div_index,
            "tag": seg.text,
            "attribute_type": seg.get("type", "").split("_"),
            "attribute_subtype": seg.get("subtype", "").split("_")
        }
        result.append(entry)

    div_index += 1
df = pd.DataFrame(result)    

with open("Output_Json_Annotationstest.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

df = pd.DataFrame(result)
df_exploded = df.explode("attribute_type")

for div_id, group in df_exploded.groupby("div"):
    counts = group["attribute_type"].value_counts()
    counts.plot(kind="pie", autopct="%1.0f%%")
    plt.title(f"Diagramm für Text Nummer {div_id}")
    plt.show()
