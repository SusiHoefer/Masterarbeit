import requests, json
from bs4 import BeautifulSoup
import re


wort = input("Bitte gib ein Wort ein:")
url = "https://www.dwds.de/api/wb/snippet/"
url2 = f"https://www.dwds.de/wb/{wort}"
url3 =f"https://www.dwds.de/api/frequency/?q={wort}"
response = requests.get(url, params={"q": wort})
responsehtml = requests.get(url2)
responsefreq = requests.get(url3)
soup = BeautifulSoup(responsehtml.text,"html.parser")
#Suche div mit den classes aus dem gescrapten
suppe = soup.find("div", class_=["bedeutungsuebersicht", "dwdswb-lesarten"])
#wenn im div was drinsteht schreibts die bedeutung hin, wenn nicht eben nix gefunden
suppe = suppe.get_text() if suppe else "Keine Bedeutungsübersicht gefunden."


if response.status_code == 200:
    #Standard-dwds-API-Abfrage
    data1 = response.json()
    wortapi= (json.dumps(data1, indent=2, ensure_ascii=False)) 
    #Wortfrequenz-API-Abfrage
    data2 = responsefreq.json()
    freqapi = (json.dumps(data2,indent=2, ensure_ascii=False))
    #Bedeutungswebscraping formatiert
    formatted = re.sub(r'(\d+\.)', r'\n\1', suppe)


    print(wortapi)
    print(freqapi)
    print(formatted.strip())
    
    

    
else:
    print("Fehler:", response.status_code)
    print(response.text)


