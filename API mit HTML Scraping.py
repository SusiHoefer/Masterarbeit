import requests, json
from bs4 import BeautifulSoup


wort = input("Bitte gib ein Wort ein:")
url = "https://www.dwds.de/api/wb/snippet/"
url2 = f"https://www.dwds.de/wb/{wort}"

response = requests.get(url, params={"q": wort})
responsehtml = requests.get(url2)
soup = BeautifulSoup(responsehtml.text,"html.parser")
suppe = soup.find("div", class_="bedeutungsuebersicht")
suppe = suppe.get_text() if suppe else "Keine Bedeutungsübersicht gefunden."


if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False),suppe)
    
else:
    print("Fehler:", response.status_code)
    print(response.text)


