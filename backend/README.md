# Merknader-backend (Fase 2a)

Flask-tjeneste som utfører selve IFC-endringen med `ifcopenshell`: legger til/fjerner en vimpel (grå stang + rødt flagg) og skriver `NCC-Produksjon`-pset-et, adaptert fra `D:\SOS-Kolbotn\app\ifc_ops.py` (se `CLAUDE.md` i prosjektroten for mapping-tabellen).

## Hva som IKKE er bygget ennå

Denne tjenesten opererer på **én lokalt konfigurert IFC-fil** — den henter ikke filen fra og laster ikke opp til et Trimble Connect-prosjekt. Det krever Trimble Connect sitt REST API (egen OAuth-app-registrering) og et valgt hostingmiljø for tjenesten (må være HTTPS for å kunne kalles fra en GitHub Pages-hostet extension inni ekte Trimble Connect — `localhost` fungerer kun når begge deler kjøres lokalt på samme maskin). Ingen av delene er besluttet ennå.

## Lokal test

```bash
pip install -r requirements.txt
set IFC_FIL=C:\sti\til\en\kopi.ifc   # PowerShell: $env:IFC_FIL = "..."
python app.py
```

Server kjører på `http://localhost:5003`.

```
GET  /api/status        – viser hvilken fil som er konfigurert
POST /api/vimpel         { "guid": "...", "merknad": "...", "utfort_av": "...", "disiplin": "", "prosjekt": "", "revisjonsnummer": "", "flagg_farge": "#CC0000" }
POST /api/fjern-vimpel   { "guid": "..." }
```

`ifc_fil` kan også sendes med i hver request-body for å overstyre `IFC_FIL`.

**Bruk en kopi av IFC-filen, ikke originalen** — endringen skrives atomisk tilbake til samme fil (temp-fil + rename), akkurat som dagens SOS-Produksjon-app.

Verifisert manuelt mot ekte SOS-Kolbotn-modeller (`D:\SOS-Kolbotn\ifc\arbeidsunderlag\*.ifc`): vimpel-geometri + pset skrives riktig på både vimpel og kildeelement, gjentatt "legg til" er idempotent (erstatter, dobler ikke opp), og "fjern" fjerner riktig proxy.
