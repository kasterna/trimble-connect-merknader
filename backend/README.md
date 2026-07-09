# Merknader-backend

`ifcopenshell`-logikken som utfører selve IFC-endringen: legger til/fjerner en vimpel (grå stang + rødt flagg), fargelegger element(er) direkte, og skriver `NCC-Produksjon`-pset-et — adaptert fra `D:\SOS-Kolbotn\app\ifc_ops.py` (se `CLAUDE.md` i prosjektroten for mapping-tabellen).

## Nivå 1: `kjor_ko.py` (bruk denne)

Extensionen laster ned en kø-fil (`.json`) i stedet for å kalle noe automatisk — se prosjektets `CLAUDE.md` for hvorfor. Denne CLI-en kjører køen mot en lokal IFC-fil, uten server:

```bash
pip install -r requirements.txt
python kjor_ko.py <sti-til-ifc-fil> <sti-til-ko.json>
```

Skriver resultatet atomisk tilbake til samme IFC-fil (temp-fil + rename). **Bruk en kopi av fila, ikke originalen fra Trimble Connect.** Etterpå: last opp den redigerte fila som ny versjon i Trimble Connect sitt eget grensesnitt, manuelt.

Eksempel på en kø-fil (samme format som extensionen laster ned):
```json
[
  { "type": "vimpel", "guid": "2fj8RrypX5JBqbfcwCdi9v", "merknad": "Sjekk fundament før støp", "revisjonen_gjelder": "Fundamentplassering", "utfort_av": "Kåre Sternang", "prosjekt": "SOS Kolbotn" },
  { "type": "fjern-vimpel", "guid": "29stQzX3z7sRMTx7Rx8N5i" },
  { "type": "farge", "guid": "0rDnSheVT9Xer10COTOTtp", "farge": "#2E7D32", "merknad": "Sjekk armering før støp", "revisjonen_gjelder": "Armeringsmengde", "utfort_av": "Kåre Sternang", "prosjekt": "SOS Kolbotn" }
]
```

De 5 standardfargene extensionen tilbyr: Rød `#CC0000`, Grønn `#2E7D32`, Gul `#FDD835`, Blå `#1565C0`, Oransje `#EF6C00` — men `kjor_ko.py`/`app.py` tar imot enhver gyldig hex-verdi i `farge`-feltet.

Verifisert manuelt mot ekte SOS-Kolbotn-modeller (`D:\SOS-Kolbotn\ifc\arbeidsunderlag\*.ifc`): vimpel-geometri + pset skrives riktig på både vimpel og kildeelement, gjentatt "legg til" er idempotent (erstatter, dobler ikke opp), "fjern" fjerner riktig proxy, fargelegging skriver riktig `IfcStyledItem` + pset på kildeelementet, og feil i enkeltposter (f.eks. ugyldig GUID) rapporteres per post uten å stoppe resten av køen.

## `app.py` (ikke i bruk fra extensionen akkurat nå)

En Flask-tjeneste med samme logikk bak `POST /api/vimpel` / `POST /api/fjern-vimpel` / `POST /api/farge` / `GET /api/status`, som opererer på én lokalt konfigurert fil (`IFC_FIL`-miljøvariabel eller `ifc_fil` i requesten). Bygget for en tidligere ambisjon om at extensionen skulle kalle en backend automatisk over HTTP — ikke koblet til noe i frontend nå, men fungerer fortsatt og er utgangspunktet hvis dere senere går videre til full automatikk (se `CLAUDE.md`, "Why Nivå 1").

```bash
set IFC_FIL=C:\sti\til\en\kopi.ifc   # PowerShell: $env:IFC_FIL = "..."
python app.py
```
