import xml.etree.ElementTree as ET
import json
ns = {"tei": "http://www.tei-c.org/ns/1.0"}
# Load XML data from a file
tree = ET.parse('Annotationstestlauf_Germanet.xml')
root = tree.getroot()
result=[]

for child in root.findall(".//tei:seg",ns):
    entry = {
        "tag": "child",
        "attributes": child.attrib,
        "text": "".join(child.itertext()).strip()
    }
    result.append(entry)
with open("Output_Json_Annotationstest.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)