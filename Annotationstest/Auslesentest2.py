import xml.etree.ElementTree as ET
import json
import pandas as pd
import matplotlib.pyplot as plt

ns = {"tei": "http://www.tei-c.org/ns/1.0"}

tree = ET.parse("Annotationstestlauf_Germanet2.xml")
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
            "attribute_subtype": seg.get("subtype", "").split("_"),
            "attribute_function": seg.get("function", "").split("_")
        }
        result.append(entry)

    div_index += 1  

with open("Output_Json_Annotationstest.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

df = pd.DataFrame(result)
df_exploded = df.explode("attribute_type") #macht aus list eine dataframe-row, mit list kann man sonst nicht weiterarbeiten


for div_id, group in df_exploded.groupby("div"):
        counts_attribute_types = group["attribute_type"].value_counts()
        counts_attribute_function = group["attribute_function"].value_counts()
        counts_attribute_types.plot(kind="pie", autopct="%1.0f%%")
        plt.title(f"Diagramm für Text Nummer {div_id}")
        text = ""
        text2 = ""

        for label, anzahl in counts_attribute_types.items():  #zählt alle attribute des typs "type"
             text += f"{label}: {anzahl}\n"
        plt.figtext(0.2,0.01,text,ha="center") # <--- X = text position
        plt.subplots_adjust(bottom=0.3,left=0.7) #styling
        for label2, anzahl2 in counts_attribute_function.items(): #zählt attr. des typs "function" 
             text2 += f"{label2}: {anzahl2}\n"
        plt.figtext(0.5,0.01,text2,ha="center") #textanzeige für attributfunctions
        plt.subplots_adjust(bottom=0.3,left=0.3) #styling
        plt.show()
 
  