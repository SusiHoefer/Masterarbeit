import xml.etree.ElementTree as ET
import json
import pandas as pd
import matplotlib.pyplot as plt

ns = {"tei": "http://www.tei-c.org/ns/1.0"}
# Load XML data from a file
tree = ET.parse('Annotationstestlauf_Germanet.xml')
root = tree.getroot()
result=[]

for child in root.findall(".//tei:seg",ns):
    
    entry = {
        "tag":child.text,
        "attribute_type":child.get("type", "").split("_"),
        "attribute_subtype":child.get("subtype", "").split("_")
    }
    result.append(entry)
    

with open("Output_Json_Annotationstest.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

df = pd.DataFrame((result))
df_exploded = df.explode("attribute_type")
counts = df_exploded["attribute_type"].value_counts()
counts.plot(
    kind='pie', y='test', autopct='%1.0f%%')
plt.show()