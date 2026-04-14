import requests, json
from bs4 import BeautifulSoup
import re


wort = input("Bitte gib ein Wort ein:")
url = "https://www.dwds.de/api/wb/snippet/"
url2 = f"https://www.dwds.de/wb/{wort}"

response = requests.get(url, params={"q": wort})
responsehtml = requests.get(url2)
soup = BeautifulSoup(responsehtml.text,"html.parser")
suppe = soup.find("div", class_=["bedeutungsuebersicht", "dwdswb-lesarten"])
suppe = suppe.get_text() if suppe else "Keine Bedeutungsübersicht gefunden."


if response.status_code == 200:
    data = response.json()
    api= (json.dumps(data, indent=2, ensure_ascii=False)) #

    formatted = re.sub(r'(\d+\.)', r'\n\1', suppe)
    print(api)
    print(formatted.strip())
    

    
else:
    print("Fehler:", response.status_code)
    print(response.text)


